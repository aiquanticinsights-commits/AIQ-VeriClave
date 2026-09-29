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
import re
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
     "verify_mode": "line",
     "frame": ("module r2(input wire [7:0] a, output wire [7:0] q);\n"
               "{line}\nendmodule"),
     "buggy": ("module r2(input wire [7:0] a, output wire [7:0] q);\n"
               "assign q = 9'b100000001;\nendmodule"),
     "must_contain": [], "must_absent": [],
     "bad": "9'b100000001", "expect_value": 1},
    {"id": "R3-semicolon", "bug": "missing semicolon",
     "buggy": ("module r3(input wire [3:0] a, output wire [3:0] y);\n"
               "assign y = a\nendmodule"),
     "must_contain": ["assign y = a;"], "must_absent": []},
    {"id": "R4-reset-value", "bug": "4-bit literal on 3-bit reset value",
     "buggy": ("module r4(input wire clk, output reg [2:0] status);\n"
               "always @(posedge clk) status <= 4'b1000;\nendmodule"),
     "must_contain": ["3'b000"], "must_absent": ["4'b1000"]},
    {"id": "R5-double", "bug": "undeclared signal AND width truncation "
     "(two faults — fix both, keep the module interface unchanged)",
     "verify_mode": "declline",
     "frame": ("module r5(input wire [3:0] a, output wire [3:0] y);\n"
               "{decl}\n{line}\nendmodule"),
     "buggy": ("module r5(input wire [3:0] a, output wire [3:0] y);\n"
               "assign y = a + c + 4'b11111;\nendmodule"),
     "must_contain": [], "must_absent": [],
     "bad": "4'b11111", "expect_value": 15,
     "decl_must": ["wire", "[3:0]", "c"],
     "decl_must_absent": ["input", "output"]},
    {"id": "R6-golden", "bug": "none (already correct — do no harm)",
     "buggy": ("module r6(input wire [3:0] a, output wire [3:0] y);\n"
               "assign y = a;\nendmodule"),
     "must_contain": ["assign y = a;"], "must_absent": []},
)

PROMPT = ("This Verilog module has a bug ({bug}). Reply with the CORRECTED "
          "full module in a fenced verilog block:\n```verilog\n{buggy}\n```")
PROMPT_LINE = ("This Verilog assign statement has a width bug ({bug}). "
               "Reply with ONLY the corrected assign line and nothing else. "
               "Keep the FULL original value: truncation keeps the LOW bits "
               "(e.g. 5'b10000 holds 0x10, whose low 4 bits are 4'b0000). "
               "Do not restructure anything:\n{buggy}")
PROMPT_DECLLINE = ("This Verilog module has two bugs ({bug}). Reply with "
                   "EXACTLY two lines and nothing else:\n"
                   "DECL: <declaration line for the missing signal — internal "
                   "wire only with the SAME width as the other operands "
                   "([3:0] here), never add ports>\n"
                   "ASSIGN: <corrected assign line — keep the original "
                   "expression shape, changing only the wrong literal>\n{buggy}")


def task_prompt(task: dict) -> str:
    mode = task.get("verify_mode", "free")
    if mode == "line":
        return PROMPT_LINE.format(bug=task["bug"], buggy=task["buggy"])
    if mode == "declline":
        return PROMPT_DECLLINE.format(bug=task["bug"], buggy=task["buggy"])
    return PROMPT.format(bug=task["bug"], buggy=task["buggy"])


DECL_RE = re.compile(r"^\s*(?:input\s+|output\s+)?wire\b[^;]*;\s*$")
LIT_RE = re.compile(r"(\d+)'([bBdDhH])([0-9a-fA-F_xzZ?]+)|(?<![\w'])(\d+)(?![\w'])")


def literal_values(line: str) -> list[tuple[int | None, int]]:
    """Integer literals in a line -> [(bits or None, value)]. x/z/? digits
    disqualify the literal (unknown value). Unsized decimals are 32-bit."""
    out = []
    for m in LIT_RE.finditer(line):
        if m.group(1):
            bits, base, digits = int(m.group(1)), m.group(2).lower(), m.group(3)
            if re.search(r"[xz?]", digits, re.IGNORECASE):
                continue
            out.append((bits, int(digits, {"b": 2, "d": 10, "h": 16}[base])))
        else:
            out.append((None, int(m.group(4))))
    return out


def value_gate(line: str, expected: int, bad: str) -> bool:
    """The line computes the required value with no oversized literal and
    without the original bug literal. Value truth, not text identity."""
    if bad in line:
        return False
    lits = literal_values(line)
    if not lits:
        return False
    if not any(v == expected for _, v in lits):
        return False
    return all(bits is None or v < (1 << bits) for bits, v in lits)


def extract_decl(text: str, signal: str = "c") -> str | None:
    """First internal wire declaration mentioning `signal` (interface adds
    — lines starting with input/output — are rejected by the caller gate).
    Leading `LABEL:` prefixes (DECL:) are stripped before matching."""
    for raw in text.splitlines():
        core = re.sub(r"^[A-Za-z_]+:\s*", "", raw)
        line = core.strip().strip("`'\"~").strip()
        if DECL_RE.match(line) and signal in line:
            return line[:line.index(";") + 1]
    return None


def verify(task: dict, text: str, lint_fn=None) -> tuple[dict, str]:
    """Candidate -> (verdicts, lint log), by the task's verify_mode:
    free      — full module, lint + substring gates (R1/R3/R4/R6).
    line      — extract ONE assign line, splice into the task frame, lint
                the spliced module + literal gates (R2).
    declline  — extract DECL + ASSIGN lines, splice both, lint + gates;
                interface preservation enforced (no input/output adds) (R5).
    """
    from bakeoff import extract_fence as _ef
    from skeletons import extract_assign_line as _eal
    lint = lint_fn or default_lint
    mode = task.get("verify_mode", "free")
    if mode == "line":
        line = _eal(text)
        if line is None or not value_gate(line, task["expect_value"],
                                          task["bad"]):
            return {"syntax": False, "fix": False}, ""
        code = task["frame"].format(line=line)
    elif mode == "declline":
        decl = extract_decl(text)
        line = _eal(text)
        if decl is None or line is None:
            return {"syntax": False, "fix": False}, ""
        if any(s in decl for s in task["decl_must_absent"]):
            return {"syntax": False, "fix": False}, ""
        if not all(s in decl for s in task["decl_must"]):
            return {"syntax": False, "fix": False}, ""
        if not value_gate(line, task["expect_value"], task["bad"]):
            return {"syntax": False, "fix": False}, ""
        code = task["frame"].format(decl=decl, line=line)
    else:
        code = _ef(text)
        if "module" not in code:
            return {"syntax": False, "fix": False}, ""
    ok, log = lint(code, wall=True)
    gates = all(s in code for s in task["must_contain"]) \
        and not any(s in code for s in task["must_absent"])
    clean = ok and "%Warning-WIDTH" not in log
    return {"syntax": clean, "fix": clean and gates}, log


def closure_prompt(task: dict, failed: str, arm: str, log: str = "") -> str:
    base = (task_prompt(task) +
            f"\n\nYour previous answer FAILED ({failed}). "
            "Fix exactly that failure; reply in the same format.")
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
            prompt = task_prompt(task)
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
