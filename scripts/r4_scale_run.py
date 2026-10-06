"""R-4 scale runner: the validated Qwen R2-pipeline recipe over the
expanded R2 pool, one cycle per invocation.

Pool (frozen rule): all 20 P2 cases + exactly those R-2b cases whose
pipeline-computed constraint agrees with the case's frozen expect (the
prompt's 'verified constraint' must be true). Disagreeing cases are
recorded as excluded with reasons — never run, never scored.

New files only: R4_PARTIAL.json (git-ignored checkpoint),
R4_CYCLE_<N>.json (per-cycle evidence), R4_TRAJECTORIES.json (cumulative
assessor input). Pipeline modules, cases, verifiers, temperatures, token
budgets, k=5 all reused untouched.
Usage: r4_scale_run.py [N]
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

from bakeoff import (ENDPOINT, LMS, lms_load, lms_unload,  # noqa: E402
                     require_server)
from p2_bench import r2_cases  # noqa: E402
from repair import value_gate as _vg  # noqa: E402
import r2_pipeline  # noqa: E402
from r2_pipeline import numeric_constraint  # noqa: E402

MODEL_ID = "qwen2.5-coder-14b-instruct"
TIMEOUT_R2 = 3600
SPEC_TAG = "p3-r4-scale-frozen"
PARTIAL_PATH = os.path.join(HERE, "R4_PARTIAL.json")
TRAJ_PATH = os.path.join(HERE, "R4_TRAJECTORIES.json")


def save(partial):
    with open(PARTIAL_PATH, "w", encoding="utf-8") as f:
        json.dump(partial, f, indent=2)


def pool_cases():
    """(pool, excluded): pool entries are (origin, case). A case joins the
    pool iff the pipeline's own constraint computation agrees with its
    frozen expect_value (pure check, no model, no lint)."""
    pool = [("P2", c) for c in r2_cases()]
    with open(os.path.join(HERE, "P3_R2B_REAL.json"),
              encoding="utf-8") as f:
        r2b = json.load(f)["cases"]
    excluded = []
    for c in r2b:
        con = numeric_constraint(c)
        if con.get("ok") and con.get("expect") == c["expect_value"]:
            pool.append(("R2B", c))
        else:
            excluded.append({"id": c["id"],
                             "reason": con.get("why", "constraint mismatch"),
                             "con_expect": con.get("expect"),
                             "case_expect": c["expect_value"]})
    return pool, excluded


def build_row(origin, case, r, cycle):
    closed = not r["stage_rank"].get("abstained") and \
        bool(r["stage_rank"].get("answer"))
    return {
        "cycle": cycle, "origin": origin, "case": case["id"],
        "closed": closed, "first_pass": closed,
        "n_passing": r["stage_rank"].get("n_passing", 0),
        "n_candidates": r2_pipeline.N_CANDIDATES,
        "abstained": r["stage_rank"].get("abstained"),
        "sim": r["stage_rank"].get("sim"),
        "answer": r["stage_rank"].get("answer"),
        "constraint": r.get("stage_constraint"),
        "latency_s": r.get("latency_s"),
        "tokens": r.get("tokens", 0),
    }


def qwen_query(prompt: str, max_tokens: int, temperature: float):
    body = json.dumps({"model": MODEL_ID,
                       "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": max_tokens,
                       "temperature": temperature}).encode()
    req = urllib.request.Request(ENDPOINT, data=body,
                                 headers={"Content-Type": "application/json"})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_R2) as r:
            data = json.load(r)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"timeout@{TIMEOUT_R2}s: {str(exc)[:120]}")
    latency = time.perf_counter() - start
    msg = data["choices"][0]["message"]["content"] or ""
    return msg, data.get("usage", {}), latency


def main(argv) -> int:
    cycle = int(argv[1]) if len(argv) > 1 else 1
    pool, excluded = pool_cases()
    try:
        with open(PARTIAL_PATH, encoding="utf-8") as f:
            partial = json.load(f)
    except (OSError, ValueError):
        partial = {}
    if partial.get("spec_tag") != SPEC_TAG or \
            partial.get("cycle") != cycle:
        partial = {"spec_tag": SPEC_TAG, "cycle": cycle, "rows": {}}
    rows = partial["rows"]

    print(f"loading {MODEL_ID} ...", flush=True)
    ok, note = lms_load(MODEL_ID)
    if not ok:
        import subprocess as _sp
        ps = ""
        try:
            ps = _sp.run([LMS, "ps"], capture_output=True, text=True,
                         timeout=60).stdout or ""
        except Exception:  # noqa: BLE001
            pass
        if MODEL_ID not in ps:
            print(f"FATAL: cannot load model: {note}", flush=True)
            return 1
        print("model already resident, proceeding", flush=True)
    if not require_server():
        lms_unload(MODEL_ID)
        return 1
    try:
        t0 = time.perf_counter()
        for origin, case in pool:
            cid = f"{origin}:{case['id']}"
            if cid in rows:
                print(f"  {cid}: recorded", flush=True)
                continue
            try:
                r = r2_pipeline.run_once(qwen_query, case)
            except Exception as exc:  # noqa: BLE001
                r = {"stage_rank": {"abstained": True, "answer": None,
                                    "n_passing": 0, "sim": "not-run"},
                     "error": str(exc)[:200]}
            row = build_row(origin, case, r, cycle)
            if "error" in r:
                row["error"] = r["error"]
            rows[cid] = row
            save(partial)
            print(f"  {cid}: closed={row['closed']} "
                  f"n_pass={row['n_passing']} {row.get('error', '')}",
                  flush=True)
        # False acceptances re-derived (not inherited).
        fa, fa_cases = 0, []
        need = {c["id"]: c for _, c in pool}
        for cid, row in rows.items():
            ans = row.get("answer")
            if not ans:
                continue
            case = need[row["case"]]
            line = r2_pipeline._assign_line(ans) or ans
            if not _vg(line, case["expect_value"], case["bad"]):
                fa += 1
                fa_cases.append(cid)
        doc = {"track": "P3-R-4 scale", "spec_tag": SPEC_TAG,
               "cycle": cycle, "model_id": MODEL_ID,
               "date": time.strftime("%Y-%m-%d"),
               "elapsed_s": round(time.perf_counter() - t0, 1),
               "pool": [f"{o}:{c['id']}" for o, c in pool],
               "excluded": excluded,
               "closed": sum(1 for v in rows.values() if v["closed"]),
               "n": len(rows), "false_acceptances": fa,
               "false_acceptance_cases": fa_cases,
               "rows": rows}
        out = os.path.join(HERE, f"R4_CYCLE_{cycle}.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
        try:
            with open(TRAJ_PATH, encoding="utf-8") as f:
                traj = json.load(f)
        except (OSError, ValueError):
            traj = {"cycles": {}, "rows": []}
        traj["cycles"][str(cycle)] = {
            "closed": doc["closed"], "n": doc["n"],
            "false_acceptances": fa, "date": doc["date"]}
        seen = {(v.get("cycle"), v.get("case")) for v in traj["rows"]}
        traj["rows"].extend(v for v in rows.values()
                            if (v.get("cycle"), v.get("case")) not in seen)
        with open(TRAJ_PATH, "w", encoding="utf-8") as f:
            json.dump(traj, f, indent=2)
        print(f"cycle={cycle} closed={doc['closed']}/{doc['n']} fa={fa} "
              f"-> {out}", flush=True)
        return 0
    finally:
        lms_unload(MODEL_ID)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
