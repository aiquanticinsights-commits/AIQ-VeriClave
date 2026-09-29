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
from formal_adapter import prove_wb_prop
from router import BASELINE_GENERATOR, PRICE, judge_filter, majority_vote, Candidate
from skeletons import SKELETONS, WIDTH_FRAMES, assemble, constrained_prompt

BASELINE_API_ID = "meta-llama-3.1-8b-instruct"
BASELINE_NAME = "llama-3.1-8b"
GEN_TEMPERATURE = 0.7
MIN_ROUNDS, MAX_ROUNDS = 2, 3

# T1-class delay requirements are unlintable (no ## support anywhere in the
# lint toolchain — measured) and go to sby instead. judge_on reroutes the
# Judge to the formal verdict for exactly these tasks.
# T4 (r2): the v1 scenario under-determined the answer (CDC defensible).
# The r2 scenario adds the waveform observation a real bug report would
# carry, which rules CDC out — scenario clarification, not answer leaking.
TASK_OVERLAYS = {
    "T1-sva-ack": {"formal": True, "judge_on": ("formal",)},
    "T4-classify-reset": {
        "prompt": ("Failure: after reset deasserts, dma_state stays S_READ "
                   "forever although m_wb_ack pulses. Waveforms at the slave "
                   "pads show m_wb_ack arriving cleanly every cycle, and the "
                   "design is single-clock (no clock-domain crossings "
                   "exist). Most likely root cause? Reply with exactly one "
                   "letter.\n"
                   "A. reset sequencing\nB. timeout counter\n"
                   "C. state-machine ack handling\nD. clock-domain crossing"),
    },
}

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

SUITE = [dict(t, **TASK_OVERLAYS.get(t["id"], {}))
         for t in (BAKEOFF_TASKS + EXTRA_TASKS)]
HERE = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------------------------------
# Deterministic verifiers (wrap bake-off graders into verdict dicts)
# --------------------------------------------------------------------------

def verify_output(task: dict, text: str, lint_fn=None,
                  preassembled: bool = False,
                  formal_fn=None) -> dict:
    """One output -> machine verdicts. Never repairs into truth.

    `preassembled` (skeleton path): text is ALREADY a complete module from
    `skeletons.assemble` — lint it as-is. Re-wrapping it in another module
    block is a harness bug that fails correct artifacts (measured P0-D
    skeleton v2: nested-module %Error on T2/T7).

    `formal_fn` (T1-class only): property text that no linter can check
    (## delays unsupported everywhere — measured) goes to sby instead.
    None (tool unavailable/bounded-unknown) fails CLOSED: escalates, never
    passes.

    `lint_fn` is injectable so unit tests stay hermetic (no Verilator).
    """
    lint = lint_fn or default_lint
    tid = task["id"]
    if task.get("formal") and preassembled:
        res = formal_fn(text) if formal_fn is not None else None
        return {"formal": res is True}
    if preassembled and tid in SKELETONS:
        ok, _ = lint(text)
        return {"syntax": ok, "proof_shape": ok}
    if preassembled and tid in WIDTH_FRAMES:
        spec = WIDTH_FRAMES[tid]
        ok, log = lint(text, wall=True)
        kill = (ok and "%Warning-WIDTH" not in log
                and spec["bad"] not in text and spec["good"] in text)
        return {"syntax": ok, "kill": kill}
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


def closure_prompt(task: dict, failed_log: str, detail: str = "") -> str:
    """Targeted regen prompt: root-cause hint from the deterministic failure,
    plus raw tool diagnostics when available (fault-hinted closure)."""
    prompt = (task["prompt"] + "\n\nYour previous answer FAILED deterministic "
              f"verification ({failed_log}). Fix exactly that failure and reply "
              "in the same format.")
    if detail:
        prompt += ("\nTool output for your previous attempt (fix these):\n"
                   + detail)
    return prompt


def failure_log(verdicts: dict) -> str:
    bad = sorted(k for k, v in verdicts.items() if not v)
    return "failed checks: " + (", ".join(bad) if bad else "none")


def diagnose(task: dict, text: str, lint_fn=None) -> str:
    """Fault localization for the closure prompt: first lint diagnostics of
    the candidate artifact. Only complete modules are linted directly (no
    re-wrapping — that path caused the nested-module fiasco); anything else
    yields '' and the prompt falls back to check names. Never raises."""
    if "module" not in text:
        return ""
    lint = lint_fn or default_lint
    try:
        ok, log = lint(text, wall=True)
    except Exception:
        return ""
    if ok:
        return ""
    lines = [l.strip()[:160] for l in log.splitlines()
             if l.strip().startswith(("%Error", "%Warning"))]
    return "\n".join(lines[:4])


def call_cost(tokens_in: int, tokens_out: int) -> float:
    """USD for one baseline call (Gate C accounting; local nominal pricing)."""
    pi, po, _ = PRICE[BASELINE_GENERATOR]
    return tokens_in / 1e6 * pi + tokens_out / 1e6 * po


def is_skeleton_task(task_id: str) -> bool:
    return task_id in SKELETONS or task_id in WIDTH_FRAMES


# Verdict keys per kind for skeleton-rejects (assemble() said NO): the
# failure is recorded without consulting any tool — an unparseable fill
# must fail even if the toolchain would lint an empty file cleanly.
REJECT_KEYS = {"sva-validity": ("syntax", "proof_shape"),
               "mutant-kill": ("syntax", "kill"),
               "localization": ("syntax", "ranked"),
               "coverage": ("syntax", "traceable")}


def base_prompt(task: dict, constrained: bool) -> str:
    if constrained:
        return constrained_prompt(task["id"], task["prompt"])
    return task["prompt"]


def run_one(task: dict, width: int, query_fn=query, lint_fn=None,
            constrained: bool = False, formal_fn=None) -> dict:
    """One task: BoN generation -> Judge (min 2 rounds) -> closure (max 3).

    ELITIST closure (prescription 1): the best candidate so far is carried
    into every later judging pool, so regen can only improve on the incumbent
    — never destroy a round-1 winner (the T2/T7 backfire class). Carrying is
    free: no extra generation calls. Ties favor the incumbent (status-quo
    bias is the point). A task is CLOSED only with approvals >= 2; anything
    weaker runs the full budget and escalates.

    Efficiency is instrumented per candidate (Gate C): total_latency_s,
    total_tokens, est_cost_usd accumulate over every generation call,
    including failed rounds — cost honesty requires counting misses too.
    """
    rounds, winner, history = 0, None, []
    total_latency, total_tokens, total_cost = 0.0, 0, 0.0
    incumbent = None
    sketched = constrained and is_skeleton_task(task["id"])
    query_errors = 0
    required = task.get("judge_on", ("syntax",))
    # Close bar: unanimous on required verdicts AND approvals >= 2 — except
    # single-verdict formal tasks, where the proof IS the whole evidence
    # (bar 1). Weak plurality on multi-key tasks escalates (elitism rule).
    need = 1 if set(required) == {"formal"} else 2
    last_text = ""
    while rounds < MAX_ROUNDS:
        rounds += 1
        cands = []
        for _ in range(width):
            prompt = base_prompt(task, constrained)
            if rounds == 1:
                call = lambda: query_fn(BASELINE_API_ID, prompt,
                                        task["max_tokens"])
            else:
                hint = diagnose(task, last_text or (
                    incumbent.output if incumbent is not None else ""),
                    lint_fn)
                call = lambda: query_fn(
                    BASELINE_API_ID,
                    closure_prompt(
                        {"id": task["id"], "kind": task["kind"],
                         "prompt": prompt, "max_tokens": task["max_tokens"]},
                        failure_log(
                            incumbent.verdicts if incumbent is not None else {}),
                        hint),
                    task["max_tokens"])
            try:
                out, use, lat = call()
            except Exception:  # noqa: BLE001 — infra fault, not a verdict:
                out, use, lat = "", {}, 0.0  # ledgered as failure, run continues
                query_errors += 1
            total_latency += max(0.0, lat)
            tin = use.get("prompt_tokens", 0) if isinstance(use, dict) else 0
            tout = use.get("completion_tokens", 0) if isinstance(use, dict) else 0
            tin = tin if tin and tin > 0 else 0
            tout = tout if tout and tout > 0 else 0
            total_tokens += tin + tout
            total_cost += call_cost(tin, tout)
            if sketched:
                built = assemble(task["id"], out)
                if built is None:
                    verdicts = dict.fromkeys(
                        REJECT_KEYS[task["kind"]], False)
                    text, method = "", "skeleton-reject"
                else:
                    text, method = built, "skeleton"
            else:
                text, method = out, "free"
            if not (sketched and method == "skeleton-reject"):
                verdicts = verify_output(
                    task, text, lint_fn=lint_fn, formal_fn=formal_fn,
                    preassembled=(sketched and is_skeleton_task(task["id"])))
            cand = Candidate(task["id"], BASELINE_NAME, text, verdicts)
            cand.method = method  # informational only; Judge sees verdicts
            cands.append(cand)
            last_text = text  # next round's fault hint localizes THIS artifact
        pool = ([incumbent] if incumbent is not None else []) + cands
        judged = [c for c in pool
                  if all(c.verdicts.get(r, False) for r in required)]
        winner = majority_vote(judged)
        if winner is not None and (incumbent is None
                                   or winner.approvals > incumbent.approvals):
            incumbent = winner
        Round = {"round": rounds, "approvals":
                 winner.approvals if winner else 0,
                 "verdicts": winner.verdicts if winner else {}}
        history.append(Round)
        closed = winner is not None and winner.approvals >= need
        if rounds >= MIN_ROUNDS and closed:
            break
    closed = winner is not None and winner.approvals >= need
    return {"task": task["id"], "kind": task["kind"], "width": width,
            "winner": winner.generator if winner else None,
            "approvals": winner.approvals if winner else 0,
            "rounds": rounds, "history": history,
            "closed": closed,
            "escalated_to_human": not closed,
            "query_errors": query_errors,
            # Winning artifact text (truncated): evidence must show WHAT was
            # proven, not just the verdict. Histories stay verdict-only.
            "artifact": (winner.output[:500] if winner is not None else ""),
            "total_latency_s": round(total_latency, 1),
            "total_tokens": total_tokens,
            "est_cost_usd": round(total_cost, 6)}


def ledger_for(results: list[dict], run_id: str) -> EvidenceLedger:
    """Every task lands in the hash-chained ledger — closes and escalations."""
    ledger = EvidenceLedger()
    for r in results:
        last = r["history"][-1] if r["history"] else {"verdicts": {}}
        if not r["escalated_to_human"]:
            ledger.append(__import__("evidence").EvidenceRecord(
                r["task"], f"SVA-TB/{r['task']}/{BASELINE_NAME}",
                dict(last["verdicts"]), "PASS", run_id=run_id))
        else:
            ledger.record_not_executed(
                r["task"], f"closure/{r['task']}",
                f"no qualifying winner after {r['rounds']} rounds; "
                "escalated to human",
                run_id=run_id)
    return ledger


def summarize(results: list[dict]) -> dict:
    rounds = [r["rounds"] for r in results]
    winners = [r for r in results if not r["escalated_to_human"]]
    requiring = [r for r in results if r["rounds"] > 2 or r["escalated_to_human"]]
    req_closed = [r for r in requiring if not r["escalated_to_human"]]
    srt = sorted(rounds)
    lat = sum(r.get("total_latency_s", 0.0) for r in results)
    tok = sum(r.get("total_tokens", 0) for r in results)
    cost = sum(r.get("est_cost_usd", 0.0) for r in results)
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
        "total_latency_s": round(lat, 1),
        "total_tokens": tok,
        "total_cost_usd": round(cost, 6),
        "avg_cost_per_task_usd": round(cost / len(results), 6),
        "avg_latency_s_per_task": round(lat / len(results), 1),
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
    no_ablation = "--no-ablation" in sys.argv
    sketched = "--skeleton" in sys.argv
    only = []
    for i, a in enumerate(sys.argv):
        if a.startswith("--tasks="):
            only = a.split("=", 1)[1].split(",")
        elif a == "--tasks" and i + 1 < len(sys.argv):
            only = sys.argv[i + 1].split(",")
    suite = list(SUITE)
    if quick:
        suite = [t for t in SUITE if t["id"] in ABLATION_SUBSET]
    if only:
        wanted = set(only)
        suite = [t for t in SUITE if t["id"] in wanted]
        if not suite:
            print(f"FATAL: --tasks matched nothing in {[t['id'] for t in SUITE]}")
            return 1

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
    # Live calls carry GEN_TEMPERATURE for BoN diversity (bake-off default
    # temp 0 is for comparability; the loop needs diverse candidates).
    live_query = lambda m, p, n: query(m, p, n, GEN_TEMPERATURE)
    live_formal = lambda prop: prove_wb_prop(prop, run_id=run_id)
    try:
        results = []
        if not ablation_only:
            for t in suite:
                if t["id"] in done:
                    print(f"  {t['id']}: already recorded, skipping",
                          flush=True)
                    results.append(done[t["id"]])
                    continue
                r = run_one(t, 3, query_fn=live_query, constrained=sketched,
                            formal_fn=live_formal)
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
        if not quick and not suite_only and not no_ablation:
            for tid in ABLATION_SUBSET:
                t = next(x for x in SUITE if x["id"] == tid)
                for n in (1, 5):
                    key = f"{tid}/n={n}"
                    if key in ablation:
                        print(f"  ablation {key}: already recorded, skipping",
                              flush=True)
                        continue
                    r = run_one(t, n, query_fn=live_query,
                                constrained=sketched, formal_fn=live_formal)
                    ablation[key] = {
                        "closed": not r["escalated_to_human"],
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
    # Per-task evidence: WHAT was proven/accepted, not just the verdict.
    report["tasks_detail"] = [
        {"task": r["task"], "kind": r["kind"], "winner": r["winner"],
         "rounds": r["rounds"], "approvals": r["approvals"],
         "escalated_to_human": r["escalated_to_human"],
         "artifact": r.get("artifact", "")[:500],
         "latency_s": r.get("total_latency_s", 0.0),
         "tokens": r.get("total_tokens", 0)}
        for r in results]
    report.update({
        "run_id": run_id, "date": time.strftime("%Y-%m-%d"),
        "benchmark": "P0-D loop v2 (elitist closure)",
        "benchmark_version": "wb_dma-v1",
        "strategy": ("skeleton-v1 for T1/T2/T6/T7/T9 + free for the rest"
                     if sketched else "free-form"),
        "task_filter": [t["id"] for t in suite],
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
    rep = []
    for i, a in enumerate(sys.argv):
        if a.startswith("--report="):
            rep = [a.split("=", 1)[1]]
        elif a == "--report" and i + 1 < len(sys.argv):
            rep = [sys.argv[i + 1]]
    default_out = "P0D_SKELETON.json" if sketched else "P0D_REPORT.json"
    out = os.path.join(HERE, rep[0] if rep else default_out)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"audit={report['audit_completeness']} chain={report['chain_valid']} "
          f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
