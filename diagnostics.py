"""Machine-readable verifier feedback (P4-07) — the 11-code diagnostic schema.

Codes are frozen in P4_BENCH_v1.json; this module is their executable form:
producers emit Diagnostic records, consumers (closure loop) route on codes —
never on free-text LLM self-correction. Prompt-only retries score 0.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Frozen diagnostic vocabulary (must match P4_BENCH_v1.json "diagnostics").
DIAGNOSTICS = frozenset({
    "SYNTAX_ERROR", "FORMAL_COUNTEREXAMPLE", "ASSERTION_FAIL", "TIMEOUT",
    "UNPROVEN", "MUTANT_SURVIVED", "TRACE_MISMATCH", "WIDTH_MISMATCH",
    "SIGNAL_NOT_FOUND", "RESET_MISMATCH", "CLOCK_DOMAIN_MISMATCH",
})

# Targeted remedy per code (GoGoTB root-cause discipline: each code routes
# to a distinct remediation, not a generic retry).
REMEDY = {
    "SYNTAX_ERROR": "fix-syntax",
    "FORMAL_COUNTEREXAMPLE": "constrain-or-weaken-property",
    "ASSERTION_FAIL": "check-stimulus-then-design",
    "TIMEOUT": "bound-depth-or-abstract",
    "UNPROVEN": "formal-policy-triage",
    "MUTANT_SURVIVED": "strengthen-checkers",
    "TRACE_MISMATCH": "reconcile-frm-vs-rtl",
    "WIDTH_MISMATCH": "fix-declaration-from-intent",
    "SIGNAL_NOT_FOUND": "reconcile-hierarchy",
    "RESET_MISMATCH": "fix-reset-polarity-kind",
    "CLOCK_DOMAIN_MISMATCH": "add-synchronizer-or-constraint",
}


@dataclass(frozen=True)
class Diagnostic:
    code: str
    detail: str = ""
    source: str = ""          # e.g. "verilator", "sby", "mutant-run", "trace-check"
    signal: str = ""
    cycle: int = -1

    def __post_init__(self):
        if self.code not in DIAGNOSTICS:
            raise ValueError(f"unknown diagnostic '{self.code}'; frozen set has 11 codes")


def diagnose(code: str, detail: str = "", source: str = "",
             signal: str = "", cycle: int = -1) -> Diagnostic:
    """Producer entry point — unknown codes raise instead of passing through."""
    return Diagnostic(code, detail, source, signal, cycle)


def remedy_for(code: str) -> str:
    """Consumer contract: every code maps to exactly one targeted remedy."""
    if code not in REMEDY:
        raise ValueError(f"no remedy for unknown code '{code}'")
    return REMEDY[code]


def from_failure_event(tool: str, severity: str, message: str) -> Diagnostic:
    """Bridge sim_adapters.FailureEvent -> Diagnostic (severity-driven default;
    callers refine with signal/cycle context where available)."""
    msg = message.lower()
    if severity == "error" or "syntax" in msg:
        code = "SYNTAX_ERROR"
    elif "assert" in msg or "fail" in msg:
        code = "ASSERTION_FAIL"
    elif "timeout" in msg or "timed out" in msg:
        code = "TIMEOUT"
    else:
        code = "TRACE_MISMATCH"
    return Diagnostic(code, detail=message[:200], source=tool)
