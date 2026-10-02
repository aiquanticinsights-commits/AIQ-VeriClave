"""R2 pipeline (P3 system-level intervention, additive to the frozen repair
loop).

Stages:
  1. fault localization    — deterministic tools first (Verilator lint WIDTH
                            diagnostic + rank_suspects on the real log). This
                            is the strongest signal available and costs no
                            model call.
  2. exact numeric constraint — deterministic: parse the oversized literal
                            (bits, value), parse the target signal width
                            from the frame, compute the exact required value
                            (value mod 2**width). No model involved — the
                            arithmetic IS the constraint, so the model is
                            never asked to do arithmetic it cannot check.
  3. multiple candidate repairs — k LLM samples, each given the localization
                            evidence AND the computed constraint. k>1 so
                            ranking has something to rank.
  4. deterministic value/syntax checks — the frozen repair.verify() grader
                            (value_gate + splice + lint wall). Zero false
                            acceptances is inherited from the frozen gate,
                            not re-implemented here.
  5. rank candidates       — deterministic: verifier-passing first, then
                            semantic closeness to the frame's original
                            expression shape, then fewest edits. Abstain if
                            nothing passes.
  6. simulation / FRM      — optional, gated on availability: if a sim/FRM
                            entry point is supplied, the winner must also
                            pass it before being emitted. Absence of a sim
                            back-end is recorded as not-run, never as pass.

Zero model calls are made in stages 1-2: on this task family the
deterministic path is strictly better than asking an 8B model to localize.
"""
from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from bakeoff import default_lint  # noqa: E402
from localize import format_suspects, localize  # noqa: E402
from repair import literal_values, value_gate, verify  # noqa: E402

GEN_TEMPERATURE = 0.7
N_CANDIDATES = 5
MAX_TOKENS = 128

# Signal-width declaration in the module header. Verilog allows a computed
# MSB (the frozen P2 frames use "[4-1:0]"), so the MSB is captured as an
# optional digit-minus-digit expression and evaluated, not pattern-matched as
# a bare integer.
WIDTH_RE = re.compile(
    r"(?:input|output)\s+wire\s*\[\s*(\d+)(?:\s*-\s*(\d+))?\s*:\s*(\d+)\s*\]")

PROMPT_REPAIR = (
    "Fault localization evidence:\n{evidence}\n\n"
    "Verified numeric constraint (already computed for you — do not "
    "recompute, do not change the value):\n"
    "  target signal width: {width} bits\n"
    "  current literal: {bad}\n"
    "  required value: {expect} (decimal) = {expect_bits} in {width}'b\n\n"
    "Write ONLY the corrected assign line. Keep the FULL original value "
    "(truncation keeps the LOW bits) and keep the original expression "
    "shape. Output exactly one line, nothing else:\n"
    "assign q = {width}'b{expect_bits};   <- shape example only, use the "
    "signal name from the frame")


def parse_target_width(task: dict) -> int | None:
    """Width of the assigned signal, taken from the task frame (deterministic).

    The frame is scanned for port declarations and the LAST one is used: in
    these frames the assigned signal is the output port, and taking the first
    match would pick the input instead.
    """
    best = None
    for src in (task.get("frame") or "", task.get("buggy") or ""):
        for m in WIDTH_RE.finditer(src):
            msb = int(m.group(1))
            if m.group(2) is not None:
                msb -= int(m.group(2))
            lsb = int(m.group(3))
            if msb >= lsb:
                best = msb - lsb + 1
    return best


def numeric_constraint(task: dict) -> dict:
    """Exact numeric constraint, computed deterministically from the buggy
    literal and the target width. `expect` must agree with the frozen task
    field — a mismatch is a benchmark bug and is surfaced, not patched."""
    # Read the literal from the ASSIGN line only. Scanning the whole module
    # would pick up the port-declaration widths ("[4-1:0]" -> 4) first and
    # silently compute the wrong constraint.
    line = _assign_line(task.get("buggy", "")) or task.get("buggy", "")
    lits = literal_values(line)
    if not lits:
        return {"ok": False, "why": "no literal on the assign line"}
    bits, value = lits[0]
    width = parse_target_width(task)
    if width is None:
        return {"ok": False, "why": "no target width in frame"}
    expect = value % (1 << width)
    agrees = (task.get("expect_value") == expect)
    return {"ok": True, "width": width, "literal_bits": bits,
            "literal_value": value, "expect": expect,
            "expect_bits": format(expect, f"0{width}b"),
            "agrees_with_frozen_task": agrees,
            "truncates": bits is not None and bits > width}


def stage_localize(task: dict, lint_fn=None) -> dict:
    """Deterministic localization: lint the buggy module and rank suspects."""
    lint = lint_fn or default_lint
    code = task["buggy"]
    ok, log = lint(code, wall=True)
    sus = format_suspects(localize("", log))
    return {"lint_ok": ok, "lint_log": log[:1200],
            "has_width_diag": "%Warning-WIDTH" in log,
            "suspects": sus}


def gen_candidates(query_fn, task: dict, constraint: dict,
                   evidence: str) -> list[dict]:
    prompt = PROMPT_REPAIR.replace(
        "{evidence}", evidence or "(lint produced no diagnostic)").replace(
        "{width}", str(constraint["width"])).replace(
        "{bad}", task["bad"]).replace(
        "{expect}", str(constraint["expect"])).replace(
        "{expect_bits}", constraint["expect_bits"])
    out = []
    for i in range(N_CANDIDATES):
        text, use, lat = query_fn(prompt, MAX_TOKENS, GEN_TEMPERATURE)
        verdicts, log = verify(task, text, lint_fn=default_lint)
        out.append({"i": i, "text": text.strip(), "verdicts": verdicts,
                    "passes": bool(all(verdicts.values())),
                    "tokens": (use.get("prompt_tokens", 0)
                               + use.get("completion_tokens", 0))
                    if isinstance(use, dict) else 0, "latency_s": lat})
    return out


_ASSIGN_RE = re.compile(r"^\s*assign\b.*;\s*$", re.MULTILINE)


def _assign_line(text: str) -> str | None:
    """The assign statement in a snippet, or None. Robust to the comment/
    boilerplate lines models add around it."""
    m = _ASSIGN_RE.search(text or "")
    return m.group(0).strip() if m else None


def _edits(line: str, original: str) -> int:
    """Cheap edit-distance proxy: count differing characters (same length
    assumption is fine as a ranking tiebreak, not a correctness claim)."""
    a, b = original.strip(), line.strip()
    if len(a) != len(b):
        return abs(len(a) - len(b)) + sum(
            1 for x, y in zip(a, b) if x != y)
    return sum(1 for x, y in zip(a, b) if x != y)


def rank(candidates: list[dict], task: dict,
         sim_fn=None) -> dict:
    """Deterministic ranking: verifier pass first (mandatory), then fewest
    edits vs the buggy line, then index. Abstains when nothing passes."""
    passing = [c for c in candidates if c["passes"]]
    if not passing:
        return {"answer": None, "abstained": True, "sim": "not-run",
                "why": "no candidate passed deterministic checks",
                "n_passing": 0}
    scored = []
    original = _assign_line(task.get("buggy", ""))
    for c in passing:
        line = _assign_line(c["text"]) or (c["text"].splitlines() or [""])[-1]
        scored.append((_edits(line, original), c["i"], c, line))
    scored.sort(key=lambda t: (t[0], t[1]))
    winner = scored[0][2]
    sim = "not-run"
    if sim_fn is not None:
        try:
            sim = "pass" if sim_fn(winner["text"]) else "fail"
        except Exception as exc:  # noqa: BLE001 — recorded, not swallowed
            sim = f"error: {str(exc)[:120]}"
    if sim_fn is not None and sim != "pass":
        return {"answer": None, "abstained": True, "sim": sim,
                "why": "winner failed simulation/FRM", "n_passing":
                len(passing)}
    return {"answer": winner["text"].strip(), "abstained": False,
            "sim": sim, "n_passing": len(passing),
            "why": "verifier-pass, fewest edits",
            "line": scored[0][3], "edits": scored[0][0]}


def run_once(query_fn, task: dict, lint_fn=None, sim_fn=None) -> dict:
    loc = stage_localize(task, lint_fn)
    con = numeric_constraint(task)
    if not con["ok"]:
        return {"stage_localize": loc, "stage_constraint": con,
                "stage_candidates": [], "stage_rank": {
                    "answer": None, "abstained": True,
                    "why": "deterministic constraint unavailable"},
                "abstain_reason": con["why"]}
    cands = gen_candidates(query_fn, task, con, loc["suspects"] + "\n"
                           + loc["lint_log"])
    rk = rank(cands, task, sim_fn=sim_fn)
    return {"stage_localize": loc, "stage_constraint": con,
            "stage_candidates": cands, "stage_rank": rk,
            "tokens": sum(c["tokens"] for c in cands),
            "latency_s": round(sum(c["latency_s"] for c in cands), 1),
            "abstain_reason": rk.get("why", "") if rk.get("abstained") else ""}


__all__ = ["run_once", "rank", "numeric_constraint", "stage_localize",
           "parse_target_width", "value_gate", "GEN_TEMPERATURE",
           "N_CANDIDATES"]