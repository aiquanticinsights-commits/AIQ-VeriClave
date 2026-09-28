"""P0-B model bake-off — same benchmark for every candidate, deterministic scoring.

Frozen architecture (D43/D49): Model A/B/C/D run the SAME verification
micro-tasks; selection is on measured correctness + verification quality +
resources + latency + tokens + cost — never general benchmarks alone, never
an LLM judge. Every scorer below is a rule (regex / exact-match / Verilator
lint); a task passes only if a deterministic tool says so.

Tasks map to verification kinds (2 tasks per kind over the 6-task set):
  sva-ack, sva-irq      -> sva-validity   (SVA draft must lint clean)
  localize-bus, classify-reset -> localization (exact-option match)
  req-ids               -> coverage       (REQ-ID structure present)
  width-fix             -> mutant-kill    (introduced WIDTH warning removed)

Usage (Windows python, stdlib only; Verilator reached via WSL):
  python bakeoff.py                       # runs slate, writes P0B_BASELINE.json
  python bakeoff.py --list                # show tasks without running models

Model load/unload is automated via `lms` between candidates so each model is
measured alone. A candidate that cannot load (e.g. RAM guardrail) is recorded
as skipped with its reason — never silently dropped (C4).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request

ENDPOINT = "http://localhost:1234/v1/chat/completions"
LMS = os.path.expandvars(r"%USERPROFILE%\.lmstudio\bin\lms.exe")

# Bake-off slate: LMStudio API id -> router registry name.
SLATE = (
    ("deepseek-coder-6.7b-instruct", "deepseek-coder-6.7b"),
    ("meta-llama-3.1-8b-instruct", "llama-3.1-8b"),
    ("openai/gpt-oss-20b", "gpt-oss-20b"),
)

TASK_TIMEOUT_S = 600
LOAD_TIMEOUT_S = 600


# --------------------------------------------------------------------------
# Response extraction / graders (pure functions — unit-tested, no infra)
# --------------------------------------------------------------------------

def extract_fence(text: str) -> str:
    """First ``` fenced block (optional language tag), else whole response."""
    m = re.search(r"```(?:\w+)?\s*\n(.*?)```", text, re.DOTALL)
    return (m.group(1) if m else text).strip()


def grade_mc(text: str, expected: str) -> bool:
    """First standalone A–D letter must equal the expected option."""
    m = re.search(r"\b([A-D])\b", text)
    return m is not None and m.group(1) == expected


def grade_req_ids(text: str, minimum: int = 3) -> bool:
    """At least `minimum` distinct REQ-NNN identifiers present."""
    return len(set(re.findall(r"REQ-\d{3}", text))) >= minimum


def default_lint(verilog: str, wall: bool = False) -> tuple[bool, str]:
    """Write snippet to a temp file and Verilator --lint-only it via WSL.

    Returns (no_error, log). With wall=True the caller inspects the log for
    specific warnings (e.g. WIDTH); errors always fail.
    """
    tmp = tempfile.NamedTemporaryFile("w", suffix=".sv", delete=False,
                                      encoding="utf-8")
    try:
        tmp.write(verilog)
        tmp.close()
        wsl_path = "/mnt/" + tmp.name[0].lower() + tmp.name[2:].replace("\\", "/")
        cmd = ["wsl", "verilator", "--lint-only"]
        if wall:
            cmd.append("-Wall")
        cmd.append(wsl_path)
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        log = (p.stdout or "") + (p.stderr or "")
        return ("%Error" not in log, log)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def grade_sva(text: str, ports: str, lint=default_lint) -> bool:
    """SVA snippet must lint clean inside a wrapper exposing `ports`."""
    snippet = extract_fence(text)
    if "assert" not in snippet.lower() and "property" not in snippet.lower():
        return False
    wrapper = f"module tb_sva({ports});\n{snippet}\nendmodule\n"
    ok, _ = lint(wrapper)
    return ok


def grade_width_fix(text: str, lint=default_lint) -> bool:
    """Fixed module must lint with NO width warning and correct constant."""
    snippet = extract_fence(text)
    if "4'b11111" in snippet:  # the injected bug literal must be gone
        return False
    if "4'b1111" not in snippet:
        return False
    ok, log = lint(snippet, wall=True)
    return ok and "%Warning-WIDTH" not in log


# --------------------------------------------------------------------------
# Tasks (frozen P0-B v1 set; benchmark_version recorded in results)
# --------------------------------------------------------------------------

SVA_PORTS_ACK = "input wire clk, input wire s_wb_stb, input wire s_wb_ack"
SVA_PORTS_IRQ = "input wire clk, input wire irq, input wire irq_en"

TASKS = (
    {"id": "T1-sva-ack", "kind": "sva-validity", "max_tokens": 256,
     "prompt": ("Write ONE SystemVerilog concurrent assertion (a single "
                "property + assert statement, no testbench, no module) for a "
                "Wishbone slave: s_wb_ack must be asserted within 2 cycles "
                "after s_wb_stb is asserted. Use signals clk, s_wb_stb, "
                "s_wb_ack. Reply with a fenced systemverilog block."),
     "grade": lambda t: grade_sva(t, SVA_PORTS_ACK)},
    {"id": "T2-sva-irq", "kind": "sva-validity", "max_tokens": 256,
     "prompt": ("Write ONE SystemVerilog concurrent assertion for a DMA "
                "engine with `assign irq = irq_flag & irq_en;`: whenever irq "
                "is 1, irq_en must be 1. Use signals clk, irq, irq_en. Reply "
                "with a fenced systemverilog block."),
     "grade": lambda t: grade_sva(t, SVA_PORTS_IRQ)},
    {"id": "T3-localize-bus", "kind": "localization", "max_tokens": 64,
     "prompt": ("Wishbone DMA failure: s_wb_ack never asserts although "
                "s_wb_stb toggles; clock and reset are correct. Rank the most "
                "likely culprit. Reply with exactly one letter.\n"
                "A. timeout counter\nB. slave ack generation logic\n"
                "C. clock-domain crossing\nD. reset sequencing"),
     "grade": lambda t: grade_mc(t, "B")},
    {"id": "T4-classify-reset", "kind": "localization", "max_tokens": 64,
     "prompt": ("Failure: after reset deasserts, dma_state stays S_READ "
                "forever although m_wb_ack pulses. Most likely root cause? "
                "Reply with exactly one letter.\nA. reset sequencing\n"
                "B. timeout counter\nC. state-machine ack handling\n"
                "D. clock-domain crossing"),
     "grade": lambda t: grade_mc(t, "C")},
    {"id": "T5-req-ids", "kind": "coverage", "max_tokens": 256,
     "prompt": ("Decompose into atomic requirements with IDs (format "
                "REQ-001, REQ-002, ...): 'Vehicle must enter safe state "
                "within 10 cycles after watchdog timeout.' Reply with one "
                "requirement per line, each starting with its REQ-ID."),
     "grade": grade_req_ids},
    {"id": "T6-width-fix", "kind": "mutant-kill", "max_tokens": 256,
     "prompt": ("This Verilog has a width bug (5-bit literal on a 4-bit "
                "signal). Reply with the CORRECTED module in a fenced "
                "verilog block, changing only the literal:\n"
                "```verilog\nmodule m(input wire [3:0] a, output wire [3:0] y);"
                "\nassign y = 4'b11111;\nendmodule\n```"),
     "grade": grade_width_fix},
)


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

def query(model_id: str, prompt: str, max_tokens: int) -> tuple[str, dict, float]:
    """One chat completion. Returns (text, usage, latency_s)."""
    body = json.dumps({"model": model_id,
                       "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": max_tokens, "temperature": 0}).encode()
    req = urllib.request.Request(ENDPOINT, data=body,
                                 headers={"Content-Type": "application/json"})
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=TASK_TIMEOUT_S) as r:
        data = json.load(r)
    latency = time.perf_counter() - start
    msg = data["choices"][0]["message"]["content"] or ""
    return msg, data.get("usage", {}), latency


def lms_load(model_id: str) -> tuple[bool, str]:
    p = subprocess.run([LMS, "load", model_id], capture_output=True,
                       text=True, timeout=LOAD_TIMEOUT_S)
    log = (p.stdout or "") + (p.stderr or "")
    low = log.lower()
    ok = "successfully" in low or "already loaded" in low
    return ok, log.strip().splitlines()[-1] if log.strip() else ""


def lms_unload(model_id: str) -> None:
    subprocess.run([LMS, "unload", model_id], capture_output=True,
                   text=True, timeout=120)


def run_candidate(api_id: str) -> dict:
    """Load one model, run all tasks, unload. Never raises: failures recorded."""
    loaded, note = lms_load(api_id)
    if not loaded:
        return {"loaded": False, "skip_reason": note, "tasks": []}
    rows = []
    try:
        for t in TASKS:
            try:
                text, usage, latency = query(api_id, t["prompt"], t["max_tokens"])
                passed = bool(t["grade"](text))
                rows.append({"task": t["id"], "kind": t["kind"], "pass": passed,
                             "latency_s": round(latency, 1),
                             "prompt_tokens": usage.get("prompt_tokens", -1),
                             "completion_tokens": usage.get("completion_tokens", -1),
                             "output_chars": len(text)})
            except Exception as exc:  # noqa: BLE001 — record, never abort slate
                rows.append({"task": t["id"], "kind": t["kind"], "pass": False,
                             "latency_s": -1.0, "prompt_tokens": -1,
                             "completion_tokens": -1, "output_chars": 0,
                             "error": str(exc)[:200]})
    finally:
        lms_unload(api_id)
    return {"loaded": True, "skip_reason": "", "tasks": rows}


def summarize(name: str, res: dict) -> dict:
    rows = res["tasks"]
    by_kind: dict[str, dict] = {}
    for kind in {t["kind"] for t in TASKS}:
        krows = [r for r in rows if r["kind"] == kind]
        by_kind[kind] = {"tasks": len(krows),
                         "pass_rate": round(sum(r["pass"] for r in krows)
                                            / max(1, len(krows)), 4)}
    lat = [r["latency_s"] for r in rows if r["latency_s"] >= 0]
    tok = sum((r["prompt_tokens"] if r["prompt_tokens"] > 0 else 0)
              + (r["completion_tokens"] if r["completion_tokens"] > 0 else 0)
              for r in rows)
    return {"model": name, "loaded": res["loaded"],
            "skip_reason": res["skip_reason"],
            "pass_rate": round(sum(r["pass"] for r in rows) / len(rows), 4)
            if rows else 0.0,
            "by_kind": by_kind,
            "avg_latency_s": round(sum(lat) / len(lat), 1) if lat else -1.0,
            "total_tokens": tok, "tasks": rows}


def select_winner(summaries: list[dict]) -> str:
    """Correctness first, then latency, then tokens (frozen selection rule)."""
    contenders = [s for s in summaries if s["loaded"]]
    if not contenders:
        raise RuntimeError("no candidate loaded; cannot freeze baseline")
    return min(contenders,
               key=lambda s: (-s["pass_rate"], s["avg_latency_s"],
                              s["total_tokens"]))["model"]


def main() -> int:
    if "--list" in sys.argv:
        for t in TASKS:
            print(f"{t['id']} [{t['kind']}] max_tokens={t['max_tokens']}")
        return 0
    summaries = []
    for api_id, name in SLATE:
        print(f"== {name} ({api_id}) ==", flush=True)
        summaries.append(summarize(name, run_candidate(api_id)))
        done = summaries[-1]
        print(f"   loaded={done['loaded']} pass_rate={done['pass_rate']} "
              f"avg_latency={done['avg_latency_s']}s tokens={done['total_tokens']}",
              flush=True)
    winner = select_winner(summaries)
    results = {"benchmark": "P0-B bake-off v1", "benchmark_version": "wb_dma-v1",
               "date": time.strftime("%Y-%m-%d"),
               "slate": [n for _, n in SLATE],
               "selection_rule": "max pass_rate, tie-break min avg_latency_s, then min total_tokens",
               "winner": winner, "candidates": summaries,
               "signoff": "PENDING"}
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "P0B_BASELINE.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"winner: {winner} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
