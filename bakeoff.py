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
import shutil
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

# --------------------------------------------------------------------------
# P0-B v2 task bank: 10 tasks x 4 kinds (40 total), all wb_dma-grounded.
# Honest scope: SVA = syntactic validity (lint-clean, immediate overlap
# forms only — the only SVA shape this Verilator lints, measured);
# localization = MCQ accuracy; coverage = REQ-ID structure; mutant-kill =
# width-fix gates. These are GENERATOR capability rates at scale (priors),
# not C1/C2 proof claims — those need the full loop at scale (P1).
# --------------------------------------------------------------------------

_SVA_PAIRS = [
    ("irq", "irq_en", "clk, irq, irq_en"),
    ("m_wb_stb", "m_wb_cyc", "clk, m_wb_stb, m_wb_cyc"),
    ("m_wb_we", "m_wb_cyc", "clk, m_wb_we, m_wb_cyc"),
    ("m_wb_we", "m_wb_stb", "clk, m_wb_we, m_wb_stb"),
    ("s_wb_we", "s_wb_stb", "clk, s_wb_we, s_wb_stb"),
    ("s_wb_stb", "s_wb_cyc", "clk, s_wb_stb, s_wb_cyc"),
    ("irq", "s_wb_stb", "clk, irq, s_wb_stb"),
    ("m_wb_stb", "s_wb_stb", "clk, m_wb_stb, s_wb_stb"),
    ("s_wb_ack", "s_wb_cyc", "clk, s_wb_ack, s_wb_cyc"),
    ("irq", "m_wb_cyc", "clk, irq, m_wb_cyc"),
]


def _sva_task(i: int, ante: str, cons: str, sigs: str) -> dict:
    ports = "input wire " + ", input wire ".join(s.strip() for s in
                                                 ["clk"] + sigs.split(",")[1:])
    return {"id": f"V2-sva-{i:02d}", "kind": "sva-validity", "max_tokens": 256,
            "prompt": (
                "Write ONE SystemVerilog concurrent assertion (a single "
                "property + assert statement, no testbench, no module) of the "
                f"overlap-implication form: whenever {ante} holds, {cons} "
                f"must hold the same cycle. Use signals {sigs}. Plain "
                "boolean expressions only (no cycle delays — the checker "
                "accepts immediate forms). Reply with a fenced systemverilog "
                "block."),
            "ports": ports,
            "grade": lambda t, p=ports: grade_sva(t, p)}


_MCQ = [
    ("s_wb_ack never asserts although s_wb_stb toggles; clock and reset are "
     "correct.",
     ["timeout counter", "slave ack generation logic",
      "clock-domain crossing", "reset sequencing"], "B"),
    ("After reset deasserts, dma_state stays S_READ forever although "
     "m_wb_ack pulses.",
     ["reset sequencing", "timeout counter", "state-machine ack handling",
      "clock-domain crossing"], "C"),
    ("DMA completes (status shows done) but irq stays 0 although the driver "
     "enabled interrupts.",
     ["reset sequencing", "irq enable / irq_flag path",
      "clock-domain crossing", "timeout counter"], "B"),
    ("Read data is always 0 although writes to the same register ack.",
     ["timeout counter", "read mux / s_wb_dat_r path",
      "clock-domain crossing", "reset sequencing"], "B"),
    ("Transfer never starts although ctrl start bit is 1 and word_count > 0.",
     ["start gating / busy status stuck", "timeout counter",
      "clock-domain crossing", "reset sequencing"], "A"),
    ("A second transfer corrupts addresses although the first completed.",
     ["timeout counter", "reset sequencing", "shadow address registers",
      "clock-domain crossing"], "C"),
    ("Status done bit never sets although the engine runs to completion.",
     ["timeout counter", "status update logic", "clock-domain crossing",
      "reset sequencing"], "B"),
    ("m_wb_adr frozen during a burst although words complete.",
     ["timeout counter", "reset sequencing", "clock-domain crossing",
      "shadow increment / ctrl bits"], "D"),
    ("Byte writes clobber the other three bytes of the register.",
     ["sel masking logic", "timeout counter", "clock-domain crossing",
      "reset sequencing"], "A"),
    ("Spurious irq with no transfer ever programmed.",
     ["timeout counter", "reset sequencing", "clock-domain crossing",
      "irq_flag reset / enable path"], "D"),
]


def _mcq_task(i: int, symptom: str, options: list[str], expected: str) -> dict:
    lines = "\n".join(f"{chr(65 + j)}. {o}" for j, o in enumerate(options))
    return {"id": f"V2-loc-{i:02d}", "kind": "localization", "max_tokens": 64,
            "prompt": (f"Wishbone DMA failure: {symptom} Rank the most likely "
                       f"culprit. Reply with exactly one letter.\n{lines}"),
            "expected": expected,
            "grade": lambda t, e=expected: grade_mc(t, e)}


_REQ_SENTENCES = [
    "Vehicle must enter safe state within 10 cycles after watchdog timeout.",
    "DMA must assert slave ack within 2 cycles of a valid strobe.",
    "Interrupt must fire exactly when a transfer completes with enable set.",
    "A second transfer must not start before software clears the done bit.",
    "Byte selects must mask unwritten bytes on partial writes.",
    "Reset must clear all control, status, and flag registers.",
    "Master strobe must never assert without master cycle.",
    "Write strobe must never assert without master cycle.",
    "Status busy must read 1 while any transfer is in flight.",
    "Read data must reflect the last written value of the addressed register.",
]


def _req_task(i: int, sentence: str) -> dict:
    return {"id": f"V2-cov-{i:02d}", "kind": "coverage", "max_tokens": 256,
            "prompt": ("Decompose into atomic requirements with IDs (format "
                       f"REQ-001, REQ-002, ...): '{sentence}' Reply with one "
                       "requirement per line, each starting with its REQ-ID."),
            "grade": grade_req_ids}


_WIDTH_SPECS = [
    ("w0", "y", "[3:0]", "4'b11111", "4'b1111"),
    ("w1", "q", "[7:0]", "9'b100000001", "8'b00000001"),
    ("w2", "d", "[15:0]", "17'h10000", "16'h0000"),
    ("w3", "s", "[2:0]", "4'b1000", "3'b000"),
    ("w4", "v", "[3:0]", "4'b10101", "4'b0101"),
    ("w5", "t", "[1:0]", "3'b111", "2'b11"),
    ("w6", "u", "[7:0]", "8'h1ff", "8'hff"),
    ("w7", "p", "[3:0]", "4'b00000", "4'b0000"),
    ("w8", "n", "[15:0]", "16'h12345", "16'h2345"),
    ("w9", "k", "[2:0]", "3'b000", "3'b000"),
]


def _width_task(i: int, mod: str, sig: str, rng: str, bad: str,
                good: str) -> dict:
    return {"id": f"V2-mut-{i:02d}", "kind": "mutant-kill", "max_tokens": 256,
            "prompt": ("This Verilog has a width bug (wrong-size literal). "
                       "Reply with the CORRECTED module in a fenced verilog "
                       "block, changing only the literal:\n"
                       "```verilog\n"
                       f"module {mod}(input wire {rng} a, output wire {rng} {sig});\n"
                       f"assign {sig} = {bad};\nendmodule\n```"),
            "bad": bad, "good": good,
            "grade": lambda t, b=bad, g=good: grade_width(t, b, g)}


def v2_bank() -> tuple:
    tasks = []
    for i, (a, c, s) in enumerate(_SVA_PAIRS):
        tasks.append(_sva_task(i, a, c, s))
    for i, (sym, opts, exp) in enumerate(_MCQ):
        tasks.append(_mcq_task(i, sym, opts, exp))
    for i, sent in enumerate(_REQ_SENTENCES):
        tasks.append(_req_task(i, sent))
    for i, (mod, sig, rng, bad, good) in enumerate(_WIDTH_SPECS):
        tasks.append(_width_task(i, mod, sig, rng, bad, good))
    return tuple(tasks)


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


# Verilator's `%Error: Exiting due to N warning(s)` line is exit-status noise,
# not a diagnostic: it appears whenever warnings exist, even with zero real
# errors. It is stripped before judging; genuine `%Error-*` lines always fail.
# (Measured P0-D skeleton v1: the noise line failed correct T2/T6/T7 outputs.)
EXIT_NOISE = re.compile(r"^%Error: Exiting due to \d+ (?:warning|error)\(s\)\s*$",
                        re.MULTILINE)


def _tool_cmd(path: str, wall: bool) -> list[str]:
    """Verilator via WSL on Windows, natively elsewhere (CI-safe)."""
    if os.name == "nt":
        wsl_path = "/mnt/" + path[0].lower() + path[2:].replace("\\", "/")
        return ["wsl", "verilator", "--lint-only"] + (["-Wall"] if wall else []) + [wsl_path], path
    return (["verilator", "--lint-only"] + (["-Wall"] if wall else []) + [path],
            path)


def default_lint(verilog: str, wall: bool = False) -> tuple[bool, str]:
    """Write snippet to a temp file and Verilator --lint-only it.

    The file is named after the module it contains: a random temp name trips
    DECLFILENAME warnings that fail otherwise-correct artifacts (measured).
    Returns (no_error, log). With wall=True the caller inspects the log for
    specific warnings (e.g. WIDTH); errors always fail.
    """
    m = re.search(r"^\s*module\s+(\w+)", verilog, re.MULTILINE)
    d = tempfile.mkdtemp()
    path = os.path.join(d, (m.group(1) if m else "t") + ".sv")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(verilog)
        cmd, _ = _tool_cmd(path, wall)
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        log = EXIT_NOISE.sub("", (p.stdout or "") + (p.stderr or ""))
        return ("%Error" not in log, log)
    finally:
        try:
            os.unlink(path)
            os.rmdir(d)
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


TASK_TIMEOUT_S = 600
LOAD_TIMEOUT_S = 600


def grade_width(text: str, bad: str, good: str, lint=default_lint) -> bool:
    """Parameterized width-fix gate for the v2 bank. Control case
    (bad == good, already-correct module) passes on clean lint alone —
    a specificity control against trigger-happy rewriters."""
    snippet = extract_fence(text)
    if bad == good:
        ok, _ = lint(snippet)
        return ok
    if bad in snippet or good not in snippet:
        return False
    ok, log = lint(snippet, wall=True)
    return ok and "%Warning-WIDTH" not in log


TASKS_V2 = v2_bank()


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

def query(model_id: str, prompt: str, max_tokens: int,
          temperature: float = 0.0) -> tuple[str, dict, float]:
    """One chat completion. Returns (text, usage, latency_s).

    temperature defaults to 0 (deterministic — bake-off comparability).
    P0-D passes GEN_TEMPERATURE explicitly for BoN candidate diversity and
    records it in the envelope (measured: without this, BoN widths are
    near-identical re-samples and width ablations are confounded).
    """
    body = json.dumps({"model": model_id,
                       "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": max_tokens,
                       "temperature": temperature}).encode()
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


def partial_path(suite: str) -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, f"BAKEOFF_PARTIAL_{suite}.json")


def load_partial(suite: str) -> dict:
    try:
        with open(partial_path(suite), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_partial(suite: str, data: dict) -> None:
    with open(partial_path(suite), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def run_candidate(api_id: str, tasks: tuple = TASKS,
                  done: dict | None = None, suite: str = "") -> dict:
    """Load one model, run all tasks, unload. Never raises: failures recorded.
    `done` maps task id -> recorded row (resume support); with `suite` set,
    every row is checkpointed to BAKEOFF_PARTIAL_<suite>.json immediately."""
    loaded, note = lms_load(api_id)
    if not loaded:
        return {"loaded": False, "skip_reason": note, "tasks": []}
    done = done or {}
    rows = []
    try:
        for t in tasks:
            if t["id"] in done:
                rows.append(done[t["id"]])
                continue
            try:
                text, usage, latency = query(api_id, t["prompt"], t["max_tokens"])
                passed = bool(t["grade"](text))
                row = {"task": t["id"], "kind": t["kind"], "pass": passed,
                       "latency_s": round(latency, 1),
                       "prompt_tokens": usage.get("prompt_tokens", -1),
                       "completion_tokens": usage.get("completion_tokens", -1),
                       "output_chars": len(text)}
            except Exception as exc:  # noqa: BLE001 — record, never abort slate
                row = {"task": t["id"], "kind": t["kind"], "pass": False,
                       "latency_s": -1.0, "prompt_tokens": -1,
                       "completion_tokens": -1, "output_chars": 0,
                       "error": str(exc)[:200]}
            rows.append(row)
            done[t["id"]] = row
            if suite:
                partial = load_partial(suite)
                partial[api_id] = done
                save_partial(suite, partial)
    finally:
        lms_unload(api_id)
    res = {"loaded": True, "skip_reason": "", "tasks": rows}
    return res


def summarize(name: str, res: dict, kinds: tuple | None = None) -> dict:
    rows = res["tasks"]
    kinds = kinds or tuple({t["kind"] for t in TASKS})
    by_kind: dict[str, dict] = {}
    for kind in kinds:
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
    v2 = "--v2" in sys.argv
    tasks = TASKS_V2 if v2 else TASKS
    kinds = ("mutant-kill", "sva-validity", "localization", "coverage")
    suite = "v2" if v2 else "v1"
    out_name = "P0B_V2_BASELINE.json" if v2 else "P0B_BASELINE.json"
    if "--list" in sys.argv:
        for t in tasks:
            print(f"{t['id']} [{t['kind']}] max_tokens={t['max_tokens']}")
        return 0
    partial = load_partial(suite) if "--resume" in sys.argv else {}
    summaries = []
    for api_id, name in SLATE:
        print(f"== {name} ({api_id}) ==", flush=True)
        res = run_candidate(api_id, tasks, partial.get(api_id, {}), suite)
        summaries.append(summarize(name, res, kinds))
        done = summaries[-1]
        print(f"   loaded={done['loaded']} pass_rate={done['pass_rate']} "
              f"avg_latency={done['avg_latency_s']}s tokens={done['total_tokens']}",
              flush=True)
    winner = select_winner(summaries)
    results = {"benchmark": f"P0-B bake-off {'v2' if v2 else 'v1'}",
               "benchmark_version": "wb_dma-v2" if v2 else "wb_dma-v1",
               "date": time.strftime("%Y-%m-%d"),
               "slate": [n for _, n in SLATE],
               "selection_rule": "max pass_rate, tie-break min avg_latency_s, then min total_tokens",
               "winner": winner, "candidates": summaries,
               "signoff": "PENDING"}
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), out_name)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"winner: {winner} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
