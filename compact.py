"""CliffCompaction rules — truncate/drop only, never rephrase, never re-compact.

Findings encoded: tool results dominate context (~56% outputs + ~28% calls);
sliding windows invalidate KV cache; summary-of-summary chains drift. So:
grow naturally, compact at budget, drop tool-output bulk first, keep prefixes
stable so caches survive between compactions.
"""
from __future__ import annotations

from dataclasses import dataclass, field

COMPACT_MARK = "[COMPACTED]"
TRUNC_KEEP_HEAD = 400
TRUNC_KEEP_TAIL = 200


@dataclass
class Turn:
    role: str
    content: str
    compacted: bool = False
    tool_output: bool = False  # tool results are the first eviction candidates


def truncate(text: str, head: int = TRUNC_KEEP_HEAD,
             tail: int = TRUNC_KEEP_TAIL) -> str:
    """Head+tail slice with an explicit marker (no rephrasing, no LLM call)."""
    if len(text) <= head + tail + 32:
        return text
    return (text[:head] + f"\n[...truncated {len(text) - head - tail} chars...]\n"
            + text[-tail:])


def should_compact(token_estimate: int, budget: int) -> bool:
    """Compact only at budget exhaustion (cliff profile preserves cache)."""
    return token_estimate >= budget


def compact_history(turns: list[Turn], keep_last: int = 4) -> list[Turn]:
    """Drop old tool outputs first, then old non-compacted turns; keep the
    most recent `keep_last` turns verbatim. Previously compacted blocks are
    discarded, never re-compacted (prevents drift accumulation)."""
    if not turns:
        return []
    recent = turns[-keep_last:]
    older = turns[:-keep_last]
    # Already-compacted history is dropped outright (never stack compactions).
    older = [t for t in older if not t.compacted]
    # Tool outputs go first (they dominate token mass).
    kept_old = [t for t in older if not t.tool_output]
    dropped_tools = [t for t in older if t.tool_output]
    summary = None
    if dropped_tools:
        summary = Turn("system",
                       f"{COMPACT_MARK} dropped {len(dropped_tools)} tool-output "
                       f"turns ({sum(len(t.content) for t in dropped_tools)} chars)",
                       compacted=True)
    head = [t for t in kept_old
            if not (len(t.content) > TRUNC_KEEP_HEAD + TRUNC_KEEP_TAIL)]
    long_kept = [Turn(t.role, truncate(t.content), compacted=True)
                 for t in kept_old if len(t.content) > TRUNC_KEEP_HEAD + TRUNC_KEEP_TAIL]
    out = (head + long_kept + ([summary] if summary else []) + recent)
    return out


def estimate_tokens(text: str) -> int:
    """Rough 4-chars-per-token estimate (budgets only, never billing)."""
    return max(1, len(text) // 4)
