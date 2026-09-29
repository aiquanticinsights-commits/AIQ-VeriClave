"""Repair-closure ablation (Gate B mechanism test): check-names-only closure
(arm A, status quo) vs fault-hinted closure with ranked suspects (arm B).

Six SEEDED repair tasks (deterministic bugs, known fixes): the model
generates a full corrected module free-form; Verilator lint + per-task gates
judge it. Both arms share prompts, model, temperature, BoN=1, and budgets —
the ONLY difference is closure-prompt content. A higher rescue count for B
is evidence the localization layer earns its keep (frozen §7 cost-control
discipline applied to intelligence, not just BoN width).

R6 is a golden control (already-correct module): closing it measures
specificity; BREAKING it measures harm. Neither arm may break R6.
"""
from __future__ import annotations

import json
import os
import sys
import time

from bakeoff import default_lint, extract_fence, lms_load, lms_unload, query
from localize import format_suspects, localize
from router import BASELINE_GENERATOR, Candidate, majority_vote

BASELINE_API_ID = "meta-llama-3.1-8b-instruct"
BASELINE_NAME = "llama-3.1-8b"
GEN_TEMPERATURE = 0.7
MIN_ROUNDS, MAX_ROUNDS = 2, 3
HERE = os.path.dirname(os.path.abspath(__file__))

REPAIR_TASKS = (
    {"id": "R1-undeclared", "bug": "undeclared signal `b`",
     "buggy": ("module r1(input wire [3:0] a, output wire [3:0] y);\n"
               "assign y = a & b;\nendmodule"),
     "must_contain": ["[3:0] b"], "must_absent": []},
    {"id": "R2-width", "bug": "9-bit literal on 8-bit signal",
     "buggy": ("module r2(input wire [7:0] a, output wire [7:0] q);\n"
               "assign q = 9'b100000001;\nendmodule"),
     "must_contain": ["8'b00000001"], "must_absent": ["9'b100000001"]},
    {"id": "R3-semicolon", "bug": "missing semicolon",
     "buggy": ("module r3(input wire [3:0] a, output wire [3:0] y);\n"
               "assign y = a\nendmodule"),
     "must_contain": ["assign y = a;"], "must_absent": []},
    {"id": "R4-reset-value", "bug": "4-bit literal on 3-bit reset value",
     "buggy": ("module r4(input wire clk, output reg [2:0] status);\n"
               "always @(posedge clk) status <= 4'b1000;\nendmodule"),
     "must_contain": ["3'b000"], "must_absent": ["4'b1000"]},
    {"id": "R5-double", "bug": "undeclared signal AND width truncation",
     "buggy": ("module r5(input wire [3:0] a, output wire [3:0] y);\n"
               "assign y = a + c + 4'b11111;\nendmodule"),
     "must_contain": ["4'b1111"], "must_absent": ["4'b11111"]},
    {"id": "R6-golden", "bug": "none (already correct — do no harm)",
     "buggy": ("module r6(input wire [3:0] a, output wire [3:0] y);\n"
               "assign y = a;\nendmodule"),
     "must_contain": ["assign y = a;"], "must_absent": []},
)

PROMPT = ("This Verilog module has a bug ({bug}). Reply with the CORRECTED "
          "full module in a fenced verilog block:\n```verilog\n{buggy}\n```")


def verify(task: dict, text: str, lint_fn=None) -> tuple[dict, str]:
    """Full-module candidate -> (verdicts, lint log). Module extraction is
    fence-first, whole-text fallback (same rule as the bake-off)."""
    from bakeoff import extract_fence as _ef
    lint = lint_fn or default_lint
    snippet = _ef(text)
    if "module" not in snippet:
        return {"syntax": False, "fix": False}, ""
    ok, log = lint(snippet, wall=True)
    gates = all(s in snippet for s in task["must_contain"]) \
        and not any(s in snippet for s in task["must_absent"])
    # Width bugs that are hard %Errors fail ok; warning-grade truncations
    # fail on the explicit marker (same doctrine as the lint gate).
    clean = ok and "%Warning-WIDTH" not in log
    return {"syntax": clean, "fix": clean and gates}, log


def closure_prompt(task: dict, failed: str, arm: str, log: str = "") -> str:
    base = (PROMPT.format(bug=task["bug"], buggy=task["buggy"]) +
            f"\n\nYour previous answer FAILED ({failed}). "
            "Fix exactly that failure; reply with the full module again.")
    if arm == "B" and log.strip():
        sus = format_suspects(localize("", log))
        base += "\nTool output for your previous attempt:\n" + \
            "\n".join(log.splitlines()[:6])
        if sus:
            base += "\n" + sus
    return base


def run_task(task: dict, arm: str, query_fn=query,
             lint_fn=None) -> dict:
    """One repair task under one closure arm. Elitist, bounded, cost-counted.
    Arm is recorded per round (same arm throughout one run)."""
    rounds, winner, history = 0, None, []
    incumbent = None
    lat_sum, tok_sum = 0.0, 0
    while rounds < MAX_ROUNDS:
        rounds += 1
        if rounds == 1:
            prompt = PROMPT.format(bug=task["bug"], buggy=task["buggy"])
        else:
            iv = incumbent.verdicts if incumbent is not None else {}
            bad = sorted(k for k, v in iv.items() if not v)
            flog = "failed checks: " + (", ".join(bad) if bad else "none")
            detail = ""
            last = incumbent.output if incumbent is not None else ""
            if arm == "B" and last and "module" in last:
                _, detail = verify(task, last, lint_fn)
            prompt = closure_prompt(task, flog, arm, detail)
        try:
            out, use, lat = query_fn(BASELINE_API_ID, prompt, 256)
        except Exception:  # noqa: BLE001 — ledgered, run continues
            out, use, lat = "", {}, 0.0
        lat_sum += max(0.0, lat)
        tok_sum += sum(v for v in
                       (use.get("prompt_tokens", 0),
                        use.get("completion_tokens", 0))
                       if isinstance(v, int) and v > 0)
        verdicts, _ = verify(task, out, lint_fn)
        cand = Candidate(task["id"], BASELINE_NAME, out, verdicts)
        pool = ([incumbent] if incumbent is not None else []) + [cand]
        judged = [c for c in pool if all(c.verdicts.values())]
        winner = majority_vote(judged)
        if winner is not None and (incumbent is None
                                   or winner.approvals > incumbent.approvals):
            incumbent = winner
        history.append({"round": rounds,
                        "approvals": winner.approvals if winner else 0})
        closed = winner is not None and winner.approvals >= 2
        if rounds >= MIN_ROUNDS and closed:
            break
    closed = winner is not None and winner.approvals >= 2
    return {"task": task["id"], "arm": arm, "closed": closed,
            "rounds": rounds,
            "approvals": winner.approvals if winner else 0,
            "escalated_to_human": not closed,
            "latency_s": round(lat_sum, 1), "tokens": tok_sum,
            "history": history}


def main() -> int:
    only = []
    for i, a in enumerate(sys.argv):
        if a.startswith("--tasks="):
            only = a.split("=", 1)[1].split(",")
        elif a == "--tasks" and i + 1 < len(sys.argv):
            only = sys.argv[i + 1].split(",")
    tasks = [t for t in REPAIR_TASKS if not only or t["id"] in only]
    if not tasks:
        print("FATAL: --tasks matched nothing", flush=True)
        return 1
    partial_path = os.path.join(HERE, "REPAIR_PARTIAL.json")
    try:
        with open(partial_path, encoding="utf-8") as f:
            done = json.load(f)
    except (OSError, ValueError):
        done = {}
    run_id = done.get("run_id", "rep-" + time.strftime("%Y%m%d-%H%M%S"))
    print(f"loading {BASELINE_API_ID} ...", flush=True)
    ok, note = lms_load(BASELINE_API_ID)
    if not ok:
        print(f"FATAL: cannot load baseline: {note}")
        return 1
    live = lambda m, p, n: query(m, p, n, GEN_TEMPERATURE)
    try:
        for task in tasks:
            for arm in ("A", "B"):
                key = f"{task['id']}/{arm}"
                if key in done.get("rows", {}):
                    print(f"  {key}: recorded, skipping", flush=True)
                    continue
                r = run_task(task, arm, query_fn=live)
                done.setdefault("rows", {})[key] = r
                done["run_id"] = run_id
                with open(partial_path, "w", encoding="utf-8") as f:
                    json.dump(done, f, indent=2)
                print(f"  {key}: closed={r['closed']} rounds={r['rounds']}",
                      flush=True)
    finally:
        lms_unload(BASELINE_API_ID)
    rows = done["rows"]
    by_arm = {}
    for arm in ("A", "B"):
        rs = [r for k, r in rows.items() if k.endswith(f"/{arm}")]
        by_arm[arm] = {"closed": sum(1 for r in rs if r["closed"]),
                       "tasks": len(rs)}
    doc = {"date": time.strftime("%Y-%m-%d"), "run_id": run_id,
           "benchmark": "repair-closure ablation v1",
           "arms": {"A": "check-names-only closure (status quo)",
                    "B": "fault-hinted closure (lint excerpt + suspects)"},
           "by_arm": by_arm, "rows": rows, "signoff": "PENDING"}
    out = os.path.join(HERE, "REPAIR_CLOSURE.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    print(f"A={by_arm['A']} B={by_arm['B']} -> {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
