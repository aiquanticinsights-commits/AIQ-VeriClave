"""P3-C amendment Q1 runner: Qwen + the existing pipeline, unchanged.

Reuses scripts/t4_pipeline.py, scripts/r2_pipeline.py, the frozen 20-case
set, verifiers, judges, temperatures, token budgets, k=5, single-pass
closure, and sim-not-run semantics WITHOUT modification. The ONLY changes
vs scripts/p3_pipeline_run.py are the model id and per-call HTTP timeouts
sized for 14B CPU generation (harness, recorded in P3_C_QWEN_AMENDMENT.json).
Original llama outputs are never opened for writing.

Timeouts are recorded as errors, never scored.
Usage: p3c_qwen_run.py
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
import t4_pipeline  # noqa: E402

MODEL_ID = "qwen2.5-coder-14b-instruct"
GOLD = "C"
N_T4 = 20
TIMEOUT_LONG = 7200    # 512-token prose stages
TIMEOUT_R2 = 3600      # 128-token repair candidates
TIMEOUT_LETTER = 1800  # 8-token bare-letter candidates
PARTIAL_PATH = os.path.join(HERE, "P3_C_QWEN_PARTIAL.json")
OUT = os.path.join(HERE, "P3_C_PIPELINE_QWEN.json")
SPEC_TAG = "p3-c-qwen-pipeline-frozen"


def save(partial):
    with open(PARTIAL_PATH, "w", encoding="utf-8") as f:
        json.dump(partial, f, indent=2)


def qwen_query(prompt: str, max_tokens: int, temperature: float):
    """Same endpoint/body as bakeoff.query; only the timeout varies by
    stage budget (Q1 harness amendment)."""
    if max_tokens >= 512:
        timeout = TIMEOUT_LONG
    elif max_tokens >= 128:
        timeout = TIMEOUT_R2
    else:
        timeout = TIMEOUT_LETTER
    body = json.dumps({"model": MODEL_ID,
                       "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": max_tokens,
                       "temperature": temperature}).encode()
    req = urllib.request.Request(ENDPOINT, data=body,
                                 headers={"Content-Type": "application/json"})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except Exception as exc:  # noqa: BLE001 — recorded, run goes on
        raise RuntimeError(f"timeout@{timeout}s: {str(exc)[:120]}")
    latency = time.perf_counter() - start
    msg = data["choices"][0]["message"]["content"] or ""
    return msg, data.get("usage", {}), latency


def main() -> int:
    try:
        with open(PARTIAL_PATH, encoding="utf-8") as f:
            partial = json.load(f)
    except (OSError, ValueError):
        partial = {}
    if partial.get("spec_tag") != SPEC_TAG:
        if partial:
            stale = os.path.join(HERE, "P3_C_QWEN_PARTIAL_STALE.json")
            try:
                with open(stale, "w", encoding="utf-8") as f:
                    json.dump(partial, f, indent=2)
                print(f"partial predates {SPEC_TAG}; archived", flush=True)
            except OSError:
                pass
        partial = {"spec_tag": SPEC_TAG}
        with open(PARTIAL_PATH, "w", encoding="utf-8") as f:
            json.dump(partial, f, indent=2)

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
        # ---- T4 track (existing pipeline, Qwen model) ----
        t4_rows = partial.setdefault("t4", {})
        for i in range(N_T4):
            key = str(i)
            if key in t4_rows:
                print(f"  t4[{i}]: recorded", flush=True)
                continue
            try:
                r = t4_pipeline.run_once(qwen_query, gold=GOLD)
            except Exception as exc:  # noqa: BLE001 — ledgered, run continues
                r = {"error": str(exc)[:200], "stage_selection":
                     {"correct": False, "abstained": True}}
            t4_rows[key] = r
            save(partial)
            sel = r.get("stage_selection", {})
            print(f"  t4[{i}]: ans={sel.get('answer')} "
                  f"correct={sel.get('correct')} "
                  f"abstained={sel.get('abstained')} {r.get('error', '')}",
                  flush=True)

        t4_sel = [r.get("stage_selection", {}) for r in t4_rows.values()]
        t4_hits = sum(1 for s in t4_sel if s.get("correct"))
        t4_abst = sum(1 for s in t4_sel if s.get("abstained"))
        t4_fa = sum(1 for s in t4_sel
                    if s.get("correct") and not s.get("scoring_agrees", True))
        t4_disagree = sum(1 for s in t4_sel
                          if s.get("scoring_agrees") is False)
        t4_err = sum(1 for r in t4_rows.values() if "error" in r)
        t4 = {
            "n": N_T4, "hits": t4_hits,
            "accuracy": round(t4_hits / N_T4, 4) if not t4_err else None,
            "errors": t4_err,
            "abstentions": t4_abst,
            "false_acceptances": t4_fa,
            "scoring_disagreements": t4_disagree,
            "tokens": sum(r.get("tokens", 0) for r in t4_rows.values()),
            "latency_s": round(sum(r.get("latency_s", 0.0)
                                   for r in t4_rows.values()), 1),
            "samples": t4_rows,
        }
        partial["t4_summary"] = t4
        save(partial)

        # ---- R2 track (existing pipeline, Qwen model) ----
        r2_rows = partial.setdefault("r2", {})
        cases = r2_cases()
        for case in cases:
            cid = case["id"]
            if cid in r2_rows:
                print(f"  {cid}: recorded", flush=True)
                continue
            try:
                r = r2_pipeline.run_once(qwen_query, case)
            except Exception as exc:  # noqa: BLE001
                r = {"stage_rank": {"abstained": True, "answer": None},
                     "error": str(exc)[:200]}
            closed = not r["stage_rank"].get("abstained") and \
                bool(r["stage_rank"].get("answer"))
            n_pass = r["stage_rank"].get("n_passing", 0)
            r2_rows[cid] = {
                "closed": closed, "first_pass": closed,
                "n_passing": n_pass,
                "abstained": r["stage_rank"].get("abstained"),
                "sim": r["stage_rank"].get("sim"),
                "answer": r["stage_rank"].get("answer"),
                "constraint": r.get("stage_constraint"),
                "latency_s": r.get("latency_s"),
                "tokens": r.get("tokens", 0),
            }
            if "error" in r:
                r2_rows[cid]["error"] = r["error"]
            save(partial)
            print(f"  {cid}: closed={closed} n_pass={n_pass} "
                  f"sim={r2_rows[cid]['sim']} "
                  f"{r2_rows[cid].get('error', '')}", flush=True)

        closed_n = sum(1 for v in r2_rows.values() if v["closed"])
        r2_fa = 0
        r2_fa_cases = []
        for case in cases:
            row = r2_rows[case["id"]]
            ans = row.get("answer")
            if not ans:
                continue
            line = r2_pipeline._assign_line(ans) or ans
            if not _vg(line, case["expect_value"], case["bad"]):
                r2_fa += 1
                r2_fa_cases.append(case["id"])
        r2_err = sum(1 for v in r2_rows.values() if "error" in v)
        r2 = {
            "n": len(cases), "closed": closed_n,
            "first_pass": sum(1 for v in r2_rows.values()
                              if v.get("first_pass")),
            "false_acceptances": r2_fa,
            "false_acceptance_cases": r2_fa_cases,
            "errors": r2_err,
            "abstentions": sum(1 for v in r2_rows.values()
                               if v.get("abstained")),
            "sim_not_run": sum(1 for v in r2_rows.values()
                               if v.get("sim") == "not-run"),
            "tokens": sum(v.get("tokens", 0) for v in r2_rows.values()),
            "latency_s": round(sum(v.get("latency_s", 0.0)
                                   for v in r2_rows.values()), 1),
            "rows": r2_rows,
        }
        partial["r2_summary"] = r2
        save(partial)

        doc = {"track": "P3-C Qwen-plus-pipeline (amendment Q1)",
               "spec_tag": SPEC_TAG, "model": "qwen2.5-coder-14b",
               "model_id": MODEL_ID, "date": time.strftime("%Y-%m-%d"),
               "elapsed_s": round(time.perf_counter() - t0, 1),
               "timeouts": {"long_prose_512": TIMEOUT_LONG,
                            "r2_repair_128": TIMEOUT_R2,
                            "bare_letter_8": TIMEOUT_LETTER},
               "t4": t4, "r2": r2, "signoff": "PENDING"}
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
        print(f"t4={t4['hits']}/{t4['n']} (abst {t4['abstentions']} "
              f"err {t4['errors']}) "
              f"r2_closed={r2['closed']}/{r2['n']} (err {r2['errors']}) "
              f"-> {OUT}", flush=True)
        return 0
    finally:
        lms_unload(MODEL_ID)


if __name__ == "__main__":
    raise SystemExit(main())
