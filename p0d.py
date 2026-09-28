"""P0-D verification loop — BoN + Judge + bounded closure on wb_dma (frozen D36).

P0-C (baseline selection) froze `selected-open-llm` onto llama-3.1-8b
(P0B_BASELINE.json). P0-D exercises the full loop with that baseline:

  generate (BoN candidates, temperature 0.7 for diversity)
    -> deterministic verifiers (Verilator lint / Yosys / rule checks)
    -> Judge (majority + CorrectBench discard-unproven)
    -> targeted closure regen (<=3 rounds, then escalate_to_human)
    -> evidence ledger (hash-chained, audit completeness computed)
    -> P0D_REPORT.json (Gates A-E measurements; human fields stay PENDING)

Honest scope (v1): loop mechanics + measurement on wb_dma. C1-C5 >=95% gates
are NOT claimed here — v1 reports measured rates; scale-up closes the gates.
Model-generated artifacts are semantically graded by tools, never byte-compared.

Usage (Windows python, stdlib only; Verilator/Yosys via WSL; LLM via LMStudio):
  python p0d.py            # full suite BoN=3 + ablation subset at n=1,5
  python p0d.py --quick    # 3-task smoke (ablation only), no full suite
"""
from __future__ import annotations

import json
import os
import sys
import time

from bakeoff import (ENDPOINT, TASKS as BAKEOFF_TASKS, default_lint,
                     extract_fence, grade_mc, grade_req_ids, grade_sva,
                     grade_width_fix, lms_load, lms_unload, query)
from compute import record_envelope
from evidence import EvidenceLedger
from router import judge_filter, majority_vote, Candidate

BASELINE_API_ID = "meta-llama-3.1-8b-instruct"
BASELINE_NAME = "llama-3.1-8b"
GEN_TEMPERATURE = 0.7
MIN_ROUNDS, MAX_ROUNDS = 2, 3

ABLATION_WIDTHS = (1, 3, 5)
ABLATION_SUBSET = ("T1-sva-ack", "T3-localize-bus", "T6-width-fix")

EXTRA_TASKS = (
    {"id": "T7-sva-cyc", "kind": "sva-validity", "max_tokens": 256,
     "prompt": ("Write ONE SystemVerilog concurrent assertion for a Wishbone "
                "DMA master: whenever m_wb_stb is 1, m_wb_cyc must be 1. Use "
                "signals clk, m_wb_stb, m_wb_cyc. Reply with a fenced "
                "systemverilog block."),
     "ports": "input wire clk, input wire m_wb_stb, input wire m_wb_cyc"},
    {"id": "T8-localize-irq", "kind": "localization", "max_tokens": 64,
     "prompt": ("Failure: DMA completes transfers (status shows done) but "
                "irq stays 0 although the driver enabled interrupts. Most "
                "likely root cause? Reply with exactly one letter.\n"
                "A. reset sequencing\nB. irq enable / irq_en control path\n"
                "C. clock-domain crossing\nD. timeout counter"),
     "expected": "B"},
    {"id": "T9-status-fix", "kind": "mutant-kill", "max_tokens": 256,
     "prompt": ("This Verilog has a width bug (4-bit literal on a 3-bit "
                "signal). Reply with the CORRECTED module in a fenced "
                "verilog block, changing only the literal:\n"
                "```verilog\nmodule s(input wire clk, output reg [2:0] status);"
                "\nalways @(posedge clk) status <= 4'b1000;\nendmodule\n```"),
     "bad": "4'b1000", "good": "3'b000"},
)

SUITE = BAKEOFF_TASKS + EXTRA_TASKS
HERE = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------------------------------
# Deterministic verifiers (wrap bake-off graders into verdict dicts)
# --------------------------------------------------------------------------

def verify_output(task: dict, text: str, lint_fn=None) -> dict:
    """One output -> machine verdicts. Never repairs into truth.

    `lint_fn` is injectable so unit tests stay hermetic (no Verilator);
    live runs always use the real Verilator lint via WSL.
    """
    lint = lint_fn or default_lint
    tid = task["id"]
    if tid in ("T1-sva-ack", "T2-sva-irq"):
        from bakeoff import SVA_PORTS_ACK, SVA_PORTS_IRQ
        ports = SVA_PORTS_ACK if tid == "T1-sva-ack" else SVA_PORTS_IRQ
        ok = grade_sva(text, ports, lint=lint)
        return {"syntax": ok, "proof_shape": ok}
    if tid == "T7-sva-cyc":
        ok = grade_sva(text, task["ports"], lint=lint)
        return {"syntax": ok, "proof_shape": ok}
    if tid in ("T3-localize-bus", "T4-classify-reset"):
        exp = "B" if tid == "T3-localize-bus" else "C"
        ok = grade_mc(text, exp)
        return {"syntax": True, "ranked": ok}
    if tid == "T8-localize-irq":
        return {"syntax": True, "ranked": grade_mc(text, task["expected"])}
    if tid == "T5-req-ids":
        ok = grade_req_ids(text)
        return {"syntax": True, "traceable": ok}
    if tid == "T6-width-fix":
        ok = grade_width_fix(text, lint=lint)
        return {"syntax": ok, "kill": ok}
    if tid == "T9-status-fix":
        snippet = extract_fence(text)
        if task["bad"] in snippet or task["good"] not in snippet:
            return {"syntax": False, "kill": False}
        ok, log = lint(snippet, wall=True)
        passed = ok and "%Warning-WIDTH" not in log
        return {"syntax": passed, "kill": passed}
    raise ValueError(f"no verifier for {tid}")


def closure_prompt(task: dict, failed_log: str) -> str:
    """Targeted regen prompt: root-cause hint from the deterministic failure."""
    return (task["prompt"] + "\n\nYour previous answer FAILED deterministic "
            f"verification ({failed_log}). Fix exactly that failure and reply "
            "in the same format.")


def failure_log(verdicts: dict) -> str:
    bad = sorted(k for k, v in verdicts.items() if not v)
    return "failed checks: " + (", ".join(bad) if bad else "none")


def run_one(task: dict, width: int, query_fn=query) -> dict:
    """One task: BoN generation -> Judge (min 2 rounds) -> closure (max 3)."""
    rounds, winner, history = 0, None, []
    while rounds < MAX_ROUNDS:
        rounds += 1
        cands = []
        for _ in range(width):
            if rounds == 1:
                out, use, lat = query_fn(BASELINE_API_ID, task["prompt"],
                                         task["max_tokens"])
            else:
                out, use, lat = query_fn(
                    BASELINE_API_ID,
                    closure_prompt(task, failure_log(history[-1]["verdicts"])
                                   if history else "no winner"),
                    task["max_tokens"])
            cands.append(Candidate(task["id"], BASELINE_NAME, out,
                                   verify_output(task, out)))
        judged = [c for c in cands
                  if all(c.verdicts.get(r, False) for r in ("syntax",))]
        winner = majority_vote(judged)
        Round = {"round": rounds, "approvals":
                 winner.approvals if winner else 0,
                 "verdicts": winner.verdicts if winner else {}}
        history.append(Round)
        if rounds >= MIN_ROUNDS and winner is not None \
                and winner.approvals >= 2:
            break
    return {"task": task["id"], "kind": task["kind"], "width": width,
            "winner": winner.generator if winner else None,
            "approvals": winner.approvals if winner else 0,
            "rounds": rounds, "history": history,
            "escalated_to_human": winner is None}


def ledger_for(results: list[dict], run_id: str) -> EvidenceLedger:
    """Every task lands in the hash-chained ledger — wins and escalations."""
    ledger = EvidenceLedger()
    for r in results:
        last = r["history"][-1] if r["history"] else {"verdicts": {}}
        if r["winner"] is not None:
            ledger.append(__import__("evidence").EvidenceRecord(
                r["task"], f"SVA-TB/{r['task']}/{BASELINE_NAME}",
                dict(last["verdicts"]), "PASS", run_id=run_id))
        else:
            ledger.record_not_executed(
                r["task"], f"closure/{r['task']}",
                f"no winner after {r['rounds']} rounds; escalated to human",
                run_id=run_id)
    return ledger


def summarize(results: list[dict]) -> dict:
    rounds = [r["rounds"] for r in results]
    winners = [r for r in results if r["winner"] is not None]
    requiring = [r for r in results if r["rounds"] > 2 or r["winner"] is None]
    req_closed = [r for r in requiring if r["winner"] is not None]
    srt = sorted(rounds)
    return {
        "tasks": len(results),
        "closed": len(winners),
        "system_accuracy": round(len(winners) / len(results), 4),
        "closure_success_rate": round(len(req_closed) / len(requiring), 4)
        if requiring else 1.0,
        "first_pass_rate": round(sum(1 for r in winners if r["rounds"] <= 2)
                                 / len(results), 4),
        "avg_closure_iterations": round(sum(rounds) / len(rounds), 2),
        "median_closure_iterations": round(
            (srt[(len(srt) - 1) // 2] + srt[len(srt) // 2]) / 2, 2),
        "max_closure_iterations": max(rounds),
        "escalated_to_human": sum(1 for r in results if r["escalated_to_human"]),
    }


def partial_path() -> str:
    return os.path.join(HERE, "P0D_PARTIAL.json")


def load_partials() -> dict:
    try:
        with open(partial_path(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"results": {}, "ablation": {}, "run_id": ""}


def save_partials(data: dict) -> None:
    with open(partial_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def main() -> int:
    quick = "--quick" in sys.argv
    resume = "--resume" in sys.argv
    suite_only = "--suite-only" in sys.argv
    ablation_only = "--ablation-only" in sys.argv
    suite = list(SUITE)
    if quick:
        suite = [t for t in SUITE if t["id"] in ABLATION_SUBSET]

    partials = load_partials() if resume else {"results": {}, "ablation": {},
                                               "run_id": ""}
    run_id = partials.get("run_id") or ("p0d-" + time.strftime("%Y%m%d-%H%M%S"))
    done = partials.get("results", {})
    ablation = partials.get("ablation", {})
    if resume and done:
        print(f"resuming {run_id}: {len(done)} suite tasks, "
              f"{len(ablation)} ablation rows already recorded", flush=True)

    print(f"loading {BASELINE_API_ID} ...", flush=True)
    ok, note = lms_load(BASELINE_API_ID)
    if not ok:
        print(f"FATAL: cannot load baseline: {note}")
        return 1
    try:
        results = []
        if not ablation_only:
            for t in suite:
                if t["id"] in done:
                    print(f"  {t['id']}: already recorded, skipping",
                          flush=True)
                    results.append(done[t["id"]])
                    continue
                r = run_one(t, 3)
                results.append(r)
                done[r["task"]] = r
                save_partials({"results": done, "ablation": ablation,
                               "run_id": run_id})
                print(f"  {r['task']}: winner={r['winner']} "
                      f"rounds={r['rounds']} escalated={r['escalated_to_human']}",
                      flush=True)
        else:
            missing = [t["id"] for t in suite if t["id"] not in done]
            if missing:
                print(f"FATAL: --ablation-only needs suite partials; "
                      f"missing {missing}. Run suite first or use --resume.")
                return 1
            results = [done[t["id"]] for t in suite]
        if not quick and not suite_only:
            for tid in ABLATION_SUBSET:
                t = next(x for x in SUITE if x["id"] == tid)
                for n in (1, 5):
                    key = f"{tid}/n={n}"
                    if key in ablation:
                        print(f"  ablation {key}: already recorded, skipping",
                              flush=True)
                        continue
                    r = run_one(t, n)
                    ablation[key] = {
                        "closed": r["winner"] is not None,
                        "rounds": r["rounds"],
                        "approvals": r["approvals"],
                        "escalated_to_human": r["escalated_to_human"]}
                    save_partials({"results": done, "ablation": ablation,
                                   "run_id": run_id})
                    print(f"  ablation {tid} n={n}: closed={r['winner'] is not None} "
                          f"rounds={r['rounds']}", flush=True)
    finally:
        lms_unload(BASELINE_API_ID)

    ledger = ledger_for(results, run_id)
    report = summarize(results)
    report.update({
        "run_id": run_id, "date": time.strftime("%Y-%m-%d"),
        "benchmark": "P0-D loop v1", "benchmark_version": "wb_dma-v1",
        "model": BASELINE_NAME, "bon_production": 3, "ablation": ablation,
        "audit_completeness": round(ledger.audit_completeness(), 4),
        "chain_valid": ledger.verify_chain(),
        "engineer_review_time_per_task": None,
        "human_rejection_rate": None, "human_override_rate": None,
        "cross_env_variance": None, "signoff": "PENDING",
        "envelope": record_envelope(
            {"backend": "local-cpu"}, model=BASELINE_NAME,
            runtime="LMStudio server :1234",
            tool_versions={"verilator": "5.032", "yosys": "0.52",
                           "sby": "0.68"},
            benchmark_version="wb_dma-v1", seed=7,
            token_settings={"temperature": GEN_TEMPERATURE},
            verification_config={"bon": 3, "min_rounds": MIN_ROUNDS,
                                 "max_rounds": MAX_ROUNDS}),
    })
    out = os.path.join(HERE, "P0D_REPORT.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"audit={report['audit_completeness']} chain={report['chain_valid']} "
          f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
