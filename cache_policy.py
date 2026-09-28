"""Redacted-prefix caching policy — privacy-safe prompt-cache boundaries.

Rule (user decision): cache ONLY redacted/spec-level prefixes. Anything that
can identify DUT internals (RTL bodies, VCD values, netlists, waveforms) goes
to the prompt TAIL and is never cached. Redaction fails closed: uncertain
content is treated as sensitive.
"""
from __future__ import annotations

import re

# Content classes allowed in the cached prefix (stable, reusable, non-sensitive).
CACHEABLE_KINDS = {"system-prompt", "spec", "frm-template", "tool-defs"}

# Minimal tool schemas per pipeline stage (ai-ensemble filter analogue for
# live sessions: only these tools are exposed, cutting 21-57K tokens/turn).
TOOL_SCHEMAS: dict[str, tuple[str, ...]] = {
    "harness": ("read", "glob", "bash-sim", "report"),
    "mutate": ("read", "glob", "bash-sim", "edit-verif"),
    "localize": ("read", "vcd-slice", "report"),
    "close": ("read", "bash-sim", "report"),
    "ensemble": ("read", "report"),
}

# Patterns that mark DUT-sensitive content (fail closed on any hit).
_SENSITIVE = (
    re.compile(r"\b(module|endmodule|always\s*@|assign\s+\w+\s*=)"),
    re.compile(r"\b[0-9a-fA-F]{9,}\b"),          # long hex literals (weights/addrs)
    re.compile(r"\bb[01xzXZ_]{17,}"),            # wide bit vectors
    re.compile(r"^#\d+\s*$", re.MULTILINE),      # VCD timestamps
    re.compile(r"\$dump(vars|file|scope)"),      # VCD structure
    re.compile(r"\b(reg|wire)\s+(\[\d+:\d+\]\s+)?\w+"),  # net declarations
)

_REDACTED = "[REDACTED-DUT]"


def contains_sensitive(text: str) -> bool:
    """True if any DUT-sensitivity pattern hits."""
    return any(p.search(text) for p in _SENSITIVE)


def redact(text: str) -> str:
    """Mask sensitive spans; fail closed (uncertain -> mask the line)."""
    out = []
    for ln in text.splitlines():
        masked = ln
        for p in _SENSITIVE:
            masked = p.sub(_REDACTED, masked)
        # Any line that still carries structural HDL keywords is dropped fully.
        if re.search(r"\b(module|endmodule|always\s*@)\b", masked):
            masked = _REDACTED
        out.append(masked)
    return "\n".join(out)


def classify(kind: str, text: str) -> str:
    """Return 'cache' (stable prefix) or 'tail' (dynamic, never cached)."""
    if kind not in CACHEABLE_KINDS:
        return "tail"
    return "tail" if contains_sensitive(text) else "cache"


def order_prompt(blocks: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Stable cacheable blocks first, dynamic content last (cache-boundary
    control: prefixes survive across turns, tails churn cheaply)."""
    cached = [(k, t) for k, t in blocks if classify(k, t) == "cache"]
    tail = [(k, t) for k, t in blocks if classify(k, t) != "cache"]
    return cached + tail


def stage_tools(stage: str) -> tuple[str, ...]:
    """Minimal tool schema for a pipeline stage (unknown stage -> read-only)."""
    return TOOL_SCHEMAS.get(stage, ("read",))
