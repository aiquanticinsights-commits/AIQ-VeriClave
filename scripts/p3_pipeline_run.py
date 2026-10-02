"""Live P3 pipeline benchmark run (spec frozen+tagged before execution).

Reads P3_PIPELINE_BENCH.json; runs T4 pipeline N=20 and R2 pipeline over the
frozen 20-case set on llama-3.1-8b. Checkpoints per case so a long run
resumes without re-querying. Results are recorded verbatim.
Usage: p3_pipeline_run.py
"""
from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

from bakeoff import LMS, lms_load, lms_unload, query, require_server  # noqa: E402
import r2_pipeline  # noqa: E402
import t4_pipeline  # noqa: E402
from p2_bench import r2_cases  # noqa: E402

MODEL_ID = "meta-llama-3.1-8b-instruct"
GOLD = "C"
N_T4 = 20
PARTIAL_PATH = os.path.join(HERE, "P3_PIPELINE_PARTIAL.json")
OUT = os.path.join(HERE, "P3_PIPELINE_LLAMA.json")


def save(partial):
    with open(PARTIAL_PATH, "w", encoding="utf-8") as f:
        json.dump(partial, f, indent=2)


def main() -> int:
    with open(os.path.join(HERE, "P3_PIPELINE_BENCH.json"), encoding="utf-8") as f:
        spec = json.load(f)
    try:
        with open(PARTIAL_PATH, encoding="utf-8") as f:
            partial = json.load(f)
    except (OSError, ValueError):
        partial = {}
    spec_tag = "p3-pipeline-bench-v2"
    stale = os.path.join(HERE, "P3_PIPELINE_PARTIAL_STALE.json")
    if partial.get("spec_commit_tag") != spec_tag:
        # A partial from a superseded spec must never be mixed into a run.
        # Preserve it as evidence and start clean rather than silently
        # reusing or silently discarding it.
        if partial:
            try:
                with open(stale, "w", encoding="utf-8") as f:
                    json.dump(partial, f, indent=2)
                print(f"partial predates {spec_tag}; archived to "
                      f"{os.path.basename(stale)}", flush=True)
            except OSError:
                pass
        partial = {"spec_commit_tag": spec_tag}
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

    def q(prompt, n=256, temp=0.7):
        return query(MODEL_ID, prompt, n, temp)

    try:
        t0 = time.perf_counter()
        # ---- T4 track ----
        t4_rows = partial.setdefault("t4", {})
        for i in range(N_T4):
            key = str(i)
            if key in t4_rows:
                print(f"  t4[{i}]: recorded", flush=True)
                continue
            try:
                r = t4_pipeline.run_once(q, gold=GOLD)
            except Exception as exc:  # noqa: BLE001 — ledgered, run continues
                r = {"error": str(exc)[:200], "stage_selection":
                     {"correct": False, "abstained": True}}
            t4_rows[key] = r
            save(partial)
            sel = r.get("stage_selection", {})
            print(f"  t4[{i}]: ans={sel.get('answer')} "
                  f"correct={sel.get('correct')} "
                  f"abstained={sel.get('abstained')}", flush=True)

        t4_sel = [r.get("stage_selection", {}) for r in t4_rows.values()]
        t4_hits = sum(1 for s in t4_sel if s.get("correct"))
        t4_abst = sum(1 for s in t4_sel if s.get("abstained"))
        # False acceptance = selection reported correct while the frozen
        # grader disagrees. Computed, not asserted.
        t4_fa = sum(1 for s in t4_sel
                    if s.get("correct") and not s.get("scoring_agrees", True))
        t4_disagree = sum(1 for s in t4_sel
                          if s.get("scoring_agrees") is False)
        cons = [r.get("stage_machine_check", {}).get("consistency", {})
                for r in t4_rows.values()]
        jac = [c["jaccard"] for c in cons if c.get("jaccard") is not None]
        t4 = {
            "n": N_T4, "hits": t4_hits,
            "accuracy": round(t4_hits / N_T4, 4),
            "abstentions": t4_abst,
            "false_acceptances": t4_fa,
            "scoring_disagreements": t4_disagree,
            "fact_consistency_mean_jaccard": round(sum(jac) / len(jac), 4)
            if jac else None,
            "tokens": sum(r.get("tokens", 0) for r in t4_rows.values()),
            "latency_s": round(sum(r.get("latency_s", 0.0)
                                   for r in t4_rows.values()), 1),
            "samples": t4_rows,
        }
        partial["t4_summary"] = t4
        save(partial)

        # ---- R2 track ----
        r2_rows = partial.setdefault("r2", {})
        cases = r2_cases()
        for case in cases:
            cid = case["id"]
            if cid in r2_rows:
                print(f"  {cid}: recorded", flush=True)
                continue
            try:
                r = r2_pipeline.run_once(q, case)
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
            save(partial)
            print(f"  {cid}: closed={closed} n_pass={n_pass} "
                  f"sim={r2_rows[cid]['sim']}", flush=True)

        closed_n = sum(1 for v in r2_rows.values() if v["closed"])
        fp_n = sum(1 for v in r2_rows.values() if v["first_pass"])
        # False acceptance: the pipeline emitted an answer whose value the
        # deterministic gate does NOT actually confirm. Re-derived from the
        # case, not from the pipeline's own claim.
        from repair import value_gate as _vg
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
        r2 = {
            "n": len(cases), "closed": closed_n, "first_pass": fp_n,
            "false_acceptances": r2_fa, "false_acceptance_cases": r2_fa_cases,
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

        doc = {"benchmark": spec["title"], "spec_tag":
               "p3-pipeline-bench-v2", "model": "llama-3.1-8b",
               "model_id": MODEL_ID, "date": time.strftime("%Y-%m-%d"),
               "elapsed_s": round(time.perf_counter() - t0, 1),
               "t4": t4, "r2": r2, "signoff": "PENDING"}
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
        print(f"t4={t4['hits']}/{t4['n']} (abst {t4['abstentions']}) "
              f"r2_closed={r2['closed']}/{r2['n']} -> {OUT}", flush=True)
        return 0
    finally:
        lms_unload(MODEL_ID)


if __name__ == "__main__":
    raise SystemExit(main())