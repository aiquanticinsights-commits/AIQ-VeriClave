"""Fault localization from tool diagnostics (BluesFL-style, lint slicing).

Given a failed candidate artifact + its Verilator log, produce a RANKED
suspect list for the closure prompt: file:line anchors first (the tool
points at them), then identifiers recurring across diagnostics. Purely
deterministic — no model, no heuristics beyond counting. The localizer
never proposes fixes; it ranks WHERE to look. The Judge still decides.

Suspect record: {"rank", "where", "signal", "reason"}.
"""
from __future__ import annotations

import re

from bakeoff import EXIT_NOISE

DIAG_RE = re.compile(r"^(%Error(?:-\w+)?|%Warning(?:-\w+)?)\s*:\s*(.*?)\s*$")
LOC_RE = re.compile(r"([^:\s()]+\.(?:sv|v|svh|vhdl?|vhd)):(\d+)")
IDENT_RE = re.compile(r"'([A-Za-z_][A-Za-z0-9_]*)'")


def parse_diagnostics(log: str) -> list[dict]:
    """Verilator log -> [{kind, code, loc, line, message}] (errors+warnings).
    The synthetic `%Error: Exiting due to N ...` exit line is status noise,
    not a diagnostic, and is excluded (same rule as the lint gate)."""
    log = EXIT_NOISE.sub("", log)
    out = []
    for raw in log.splitlines():
        m = DIAG_RE.match(raw.strip())
        if not m:
            continue
        msg = m.group(2)
        loc = LOC_RE.search(msg)
        out.append({"kind": "error" if m.group(1).startswith("%Error")
                    else "warning",
                    "code": m.group(1), "loc": loc.group(0) if loc else "",
                    "line": int(loc.group(2)) if loc else 0,
                    "message": msg[:200]})
    return out


def localize(artifact: str, log: str, top_n: int = 3) -> list[dict]:
    """Rank suspects. Errors outrank warnings; located diagnostics outrank
    unlocated ones; ties break by identifier frequency then line number
    (all deterministic). Empty log -> [] (caller falls back to check names)."""
    diags = [d for d in parse_diagnostics(log) if d["kind"] == "error"]
    if not diags:
        diags = parse_diagnostics(log)
    if not diags:
        return []
    counts: dict[str, int] = {}
    for d in diags:
        for ident in IDENT_RE.findall(d["message"]):
            counts[ident] = counts.get(ident, 0) + 1
    ranked = []
    seen = set()
    # Pass 1: located diagnostics, in log order (the tool's own ranking).
    for d in diags:
        if d["loc"] and d["loc"] not in seen:
            seen.add(d["loc"])
            ranked.append({"where": d["loc"], "signal": "",
                           "reason": f"{d['code']}: {d['message'][:120]}"})
    # Pass 2: recurring identifiers (cross-diagnostic suspects).
    for ident, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        if ident not in seen:
            seen.add(ident)
            ranked.append({"where": "", "signal": ident,
                           "reason": f"named in {counts[ident]} diagnostic(s)"})
    # Pass 3: any remaining unlocated diagnostic, by code then message.
    for d in sorted([d for d in diags if not d["loc"]],
                    key=lambda d: (d["code"], d["message"])):
        key = (d["code"], d["message"])
        if key not in seen:
            seen.add(key)
            ranked.append({"where": "", "signal": "",
                           "reason": f"{d['code']}: {d['message'][:120]}"})
    for i, s in enumerate(ranked[:top_n]):
        s["rank"] = i + 1
    return ranked[:top_n]


def format_suspects(suspects: list[dict]) -> str:
    """One block for the closure prompt. Empty -> '' (caller omits it)."""
    if not suspects:
        return ""
    lines = ["Ranked fault suspects (fix rank 1 first):"]
    for s in suspects:
        at = s["where"] or ("signal `%s'" % s["signal"] if s["signal"]
                            else "artifact")
        lines.append(f"{s['rank']}. {at} — {s['reason']}")
    return "\n".join(lines)
