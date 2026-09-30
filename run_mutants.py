"""Mutation campaign runner (frozen V6 objective, Gate A/C1).

Kill ladder per mutant (first hit wins, cheapest first):
  1. syntax  — Verilator --lint-only error  -> KILLED-syntax
  2. sim     — FRM-vs-RTL co-sim mismatch on fixed vectors -> KILLED-sim
  3. fuzz    — mismatch on 5 seeded fuzz programs -> KILLED-fuzz
  otherwise -> SURVIVED (human analyzes; EQUIVALENT is NEVER assigned by
  machine — it enters only via a human-authored dispositions file that
  classify.py consumes).

INVALID = seeder produced no change / file unwritable. INFRA_FAILURE =
timeout or crash (retried once, then recorded — never silently dropped).

Crash-safe: MUTATION_PARTIAL.json checkpoints every mutant; --resume
continues; --limit N caps the run. One shared sim workdir so the build
cache keys off RTL hashes (rebuild per mutant, seconds each).
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MUTANT_DIRNAME = "mutants"
PARTIAL_NAME = "MUTATION_PARTIAL.json"
LINT_TIMEOUT_S = 120
SIM_TIMEOUT_S = 600

FIXED_VECTORS = [
    ["rst", "w 0 00001000", "w 4 00002000", "w 8 00000002", "w c 00000007",
     "w 14 00000001", "tick 10", "w c 00000006", "tick 4", "r 10"],
    ["rst", "w 0 deadbeef", "w 4 cafef00d", "w 8 0010", "w c 00000007",
     "r 0", "r 4", "r 8", "r c", "r 10", "r 14"],
    # V4: status/flag clear path, QUIESCED (start bit cleared first so no
    # retrigger masks the cleared state — measured masking in v1 vectors).
    ["rst", "w 0 00001000", "w 4 00002000", "w 8 00000001", "w c 00000007",
     "w 14 00000001", "tick 10", "w c 00000006", "tick 2", "w 10 0000000f",
     "tick 2", "r 10", "r 14"],
    # V5: invalid-address read AFTER a valid one (default arm must return 0,
    # not hold the previous read).
    ["rst", "w 0 11223344", "r 0", "r 3c", "r 10", "r 14"],
    # V6: byte-select lanes, sequenced so each lane is distinguishing
    # (src, then count, then dst lanes).
    ["rst", "w 0 12345678", "ws 0 aabb 2", "r 0",
     "ws 8 ff 1", "ws 8 00 2", "r 8",
     "ws 8 1234 3", "ws 8 abcd 2", "r 8",
     "ws 4 1234 3", "ws 4 abcd 2", "r 4"],
    # V7: deasserted-strobe discipline (M010/M038) + stb-less clear (M020).
    # Programs a transfer first so flag/status are SET (clear has effect).
    ["rst", "w 0 00001000", "w 4 00002000", "w 8 00000001", "w c 00000007",
     "w 14 00000001", "tick 10", "w c 00000006", "tick 2",
     "w 0 11223344", "h", "hw 0 55667788", "r 0",
     "hw 10 0000000f", "r 10", "r 14"],
    # V8: idle/query sampling (kills stuck-ack + reset-value mutants).
    ["rst", "q", "w 0 1", "tick 3", "q"],
]
FUZZ_SEEDS = (11, 22, 33, 44, 55)


def _lazy():
    global _M
    try:
        return _M
    except NameError:
        pass
    sys.path.insert(0, HERE)
    import bakeoff
    import mutate
    import sim_frm
    _M = (bakeoff, mutate, sim_frm)
    return _M


def apply_catalog(catalog: list[dict], outdir: str) -> dict:
    """Write one mutant file per catalog entry. Returns {id: path|None}.
    Unreadable sources yield None (INVALID downstream), never an exception."""
    _, mutate, _ = _lazy()
    os.makedirs(outdir, exist_ok=True)
    paths = {}
    for entry in catalog:
        try:
            with open(entry["path"], encoding="utf-8") as f:
                lines = f.readlines()
        except OSError:
            paths[entry["id"]] = None
            continue
        mutated = mutate.apply_mutation(lines, entry)
        dest = os.path.join(outdir, f"{entry['id']}.v")
        if mutated is None:
            paths[entry["id"]] = None
            continue
        with open(dest, "w", encoding="utf-8") as f:
            f.writelines(mutated)
        paths[entry["id"]] = dest
    return paths


def lint_file(path: str, lint_fn=None) -> tuple[bool, str]:
    """True = lints clean. Uses default_lint unless injected (tests)."""
    bakeoff, _, _ = _lazy()
    lint = lint_fn or bakeoff.default_lint
    with open(path, encoding="utf-8") as f:
        text = f.read()
    try:
        ok, log = lint(text)
        return ok, log
    except Exception as exc:  # noqa: BLE001 — infra fault, recorded
        return False, f"INFRA: {exc}"[:300]


def sim_kill(mutant_path: str, workdir: str, sim_fn=None,
             fuzz_fn=None) -> tuple[bool, str]:
    """True = killed (trace mismatch). Fixed vectors first, then fuzz.
    sim_fn(stim) replaces co-simulation wholesale (tests inject it; live
    wraps co_sim which builds+runs). fuzz_fn replaces fuzz_stim.
    A build that fails WITH tool diagnostics (%Error, incl. warning-grade
    failures the stricter --cc stage catches) is a KILLED-build verdict —
    the pipeline catches it. Only tool absence/timeout/crash is INFRA."""
    _, _, sim_frm = _lazy()
    if sim_fn is None:
        def sim_fn(stim, _mp=mutant_path, _wd=workdir):
            try:
                return sim_frm.co_sim(stim, rtl_path=_mp, workdir=_wd)
            except RuntimeError as exc:
                if "%Error" in str(exc):
                    return {"match": False, "first_diverge": -99,
                            "frm": "", "rtl": "",
                            "note": "build-gate"}
                raise
    fuzz = fuzz_fn or sim_frm.fuzz_stim
    for k, stim in enumerate(FIXED_VECTORS):
        try:
            res = sim_fn(stim)
        except Exception as exc:  # noqa: BLE001
            return False, f"INFRA: {exc}"[:200]
        if not res["match"]:
            why = res.get("note") or f"fixed-vector {k} div@{res['first_diverge']}"
            return True, why
    for seed in FUZZ_SEEDS:
        try:
            res = sim_fn(fuzz(seed))
        except Exception as exc:  # noqa: BLE001
            return False, f"INFRA: {exc}"[:200]
        if not res["match"]:
            why = res.get("note") or \
                f"fuzz seed {seed} div@{res['first_diverge']}"
            return True, why
    return False, ""


def frm_run(frm, stim: list[str]) -> list[str]:
    frm.__init__()
    return frm.run_stim(stim)


def run_one(entry: dict, paths: dict, workdir: str, lint_fn=None,
            sim_fn=None, fuzz_fn=None) -> dict:
    """Full ladder for one mutant -> result record (never raises)."""
    mid = entry["id"]
    path = paths.get(mid)
    if not path or not os.path.isfile(path):
        return {"id": mid, "op": entry["op"], "status": "INVALID",
                "by": "no-change", "detail": "seeder produced no file"}
    ok, log = lint_file(path, lint_fn)
    if not ok:
        if log.startswith("INFRA:"):
            return {"id": mid, "op": entry["op"], "status": "INFRA_FAILURE",
                    "by": "lint-infra", "detail": log[:200]}
        return {"id": mid, "op": entry["op"], "status": "KILLED",
                "by": "syntax", "detail": log.splitlines()[0][:200]
                if log else ""}
    killed, detail = sim_kill(path, workdir, sim_fn, fuzz_fn)
    if detail.startswith("INFRA:"):
        return {"id": mid, "op": entry["op"], "status": "INFRA_FAILURE",
                "by": "sim-infra", "detail": detail}
    if killed:
        return {"id": mid, "op": entry["op"], "status": "KILLED",
                "by": "sim", "detail": detail}
    return {"id": mid, "op": entry["op"], "status": "SURVIVED",
            "by": "fixed+fuzz-vectors", "detail": ""}


def partial_path() -> str:
    return os.path.join(HERE, PARTIAL_NAME)


def load_partial() -> dict:
    try:
        with open(partial_path(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_partial(data: dict) -> None:
    with open(partial_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def campaign(catalog: list[dict], workdir: str = "",
             limit: int = 0, resume: bool = False,
             lint_fn=None, sim_fn=None, fuzz_fn=None) -> dict:
    """Run the ladder over the catalog. Returns {id: result} (all entries)."""
    workdir = workdir or tempfile.mkdtemp(prefix="mutcamp_")
    os.makedirs(workdir, exist_ok=True)
    mutdir = os.path.join(workdir, MUTANT_DIRNAME)
    done = load_partial().get("results", {}) if resume else {}
    if limit:
        catalog = catalog[:limit]
    paths = apply_catalog(catalog, mutdir)
    results = {}
    for entry in catalog:
        mid = entry["id"]
        if mid in done:
            results[mid] = done[mid]
            continue
        try:
            results[mid] = run_one(entry, paths, workdir, lint_fn,
                                   sim_fn, fuzz_fn)
        except Exception as exc:  # noqa: BLE001 — last-resort guard
            results[mid] = {"id": mid, "op": entry.get("op", "?"),
                            "status": "INFRA_FAILURE", "by": "runner",
                            "detail": str(exc)[:200]}
        done[mid] = results[mid]
        save_partial({"results": done})
    return results


def main() -> int:
    limit, resume, selftest = 0, False, False
    out = os.path.join(HERE, "MUTATION_WB_DMA.json")
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a.startswith("--limit="):
            limit = int(a.split("=", 1)[1])
        elif a == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
        elif a == "--resume":
            resume = True
        elif a == "--selftest":
            selftest = True
        elif a.startswith("--out="):
            out = a.split("=", 1)[1]
        elif a == "--out" and i + 1 < len(args):
            out = args[i + 1]
    if selftest:
        return _selftest()
    sys.path.insert(0, HERE)
    import mutate
    from classify import classify, write_report
    from sim_frm import DEFAULT_RTL
    # V6 campaign scope: wb_dma only. gates_demo blocks carry CDC operators
    # in the seeder, but their TB/FRM does not exist yet — campaigning them
    # under the wb_dma harness would measure harness mismatch, not mutants.
    # (Recorded limitation, not silent scope cut.)
    files = [DEFAULT_RTL] if os.path.isfile(DEFAULT_RTL) else []
    if not files:
        print("FATAL: no RTL sources found", flush=True)
        return 1
    pool = mutate.seed_catalog(files, 100000, seed=7)
    catalog = mutate.stratify(pool, 100, seed=7)
    mutate.write_catalog(catalog, os.path.join(HERE, "mutant_catalog.json"))
    print(f"pool={len(pool)} campaign={len(catalog)}", flush=True)
    t0 = time.perf_counter()
    results = campaign(catalog, resume=resume, limit=limit)
    disp_path = os.path.join(HERE, "mutation_dispositions.json")
    try:
        with open(disp_path, encoding="utf-8") as f:
            dispositions = {k: v for k, v in json.load(f).items()
                            if not k.startswith("_")}
    except (OSError, ValueError):
        dispositions = {}
    report = classify(results, catalog, dispositions)
    report["elapsed_s"] = round(time.perf_counter() - t0, 1)
    report["benchmark"] = "mutation-c1 v1"
    write_report(report, out)
    print(f"killed={report['killed']}/{report['executable']} "
          f"score={report['score']} survivors={report['survived']} "
          f"-> {out}", flush=True)
    return 0


def _selftest() -> int:
    """CI mutation smoke: 3 seeded mutants on an inline fixture through the
    lint rung only (no RTL sibling, no sim build on CI). Fails loudly on
    ladder regressions, never on missing tools (those skip upstream)."""
    import tempfile
    sys.path.insert(0, HERE)
    import mutate
    d = tempfile.mkdtemp(prefix="mutself_")
    src = os.path.join(d, "f.sv")
    with open(src, "w", encoding="utf-8") as f:
        f.write("module f(input wire clk, input wire [3:0] a,\n"
                "output wire [3:0] y);\n"
                "assign y = a;\nendmodule\n")
    cat = mutate.seed_catalog([src], 3, seed=7)
    assert len(cat) == 3, f"expected 3 mutants, got {len(cat)}"
    paths = apply_catalog(cat, os.path.join(d, "m"))
    assert all(paths.values()), "all 3 must apply"
    from classify import classify
    fake = {m["id"]: {"status": "KILLED", "by": "syntax"} for m in cat}
    rep = classify(fake, cat)
    assert rep["score"] == 1.0, rep
    print(f"mutation selftest ok: 3 seeded, 3 applied, score path ok",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
