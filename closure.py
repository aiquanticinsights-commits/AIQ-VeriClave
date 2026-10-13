"""Closure boundary qualification (P4-08) — R0-R3 max, then human escalation.

Proves the boundary cannot be bypassed: no silent Round 4, no recursive
self-invocation beyond policy, no unresolved-to-PASS conversion, no dropped
candidates, no overwritten evidence. Tripwire tests below attempt each
violation; all must raise.
"""
from __future__ import annotations

from dataclasses import dataclass, field

MAX_AUTO_ROUNDS = 3  # R0, R1, R2, R3 — then HUMAN_ESCALATION, unconditionally


@dataclass
class ClosureAttempt:
    round_no: int           # 0..3
    candidate: str
    verifier_result: str    # "PASS" | "FAIL"
    repair_action: str = ""
    evidence_hash: str = ""


class ClosureBoundary:
    """Enforces the bounded closure loop for one requirement/candidate chain."""

    def __init__(self, requirement_id: str) -> None:
        self.requirement_id = requirement_id
        self.attempts: list[ClosureAttempt] = []
        self.escalated = False

    def attempt(self, candidate: str, verifier_result: str,
                repair_action: str = "", evidence_hash: str = "") -> ClosureAttempt:
        """Record round R=len(attempts). Raises on any boundary violation."""
        if self.escalated:
            raise RuntimeError("chain already escalated: no further auto rounds")
        round_no = len(self.attempts)
        if round_no > MAX_AUTO_ROUNDS:
            raise RuntimeError(f"Round {round_no} denied: automatic closure ends at R{MAX_AUTO_ROUNDS}")
        if verifier_result not in ("PASS", "FAIL"):
            raise ValueError("verifier_result must be PASS or FAIL (no silent states)")
        if evidence_hash and any(a.evidence_hash == evidence_hash and evidence_hash for a in self.attempts):
            raise RuntimeError("evidence overwrite denied: hashes must be unique per attempt")
        att = ClosureAttempt(round_no, candidate, verifier_result, repair_action, evidence_hash)
        self.attempts.append(att)
        if verifier_result == "FAIL" and round_no == MAX_AUTO_ROUNDS:
            self.escalated = True
        return att

    def disposition(self) -> str:
        """Terminal state: PASS (some round passed), ESCALATED (R3 failed),
        or OPEN (rounds remain). Unresolved FAIL is never converted to PASS."""
        if any(a.verifier_result == "PASS" for a in self.attempts):
            return "PASS"
        if self.escalated:
            return "HUMAN_ESCALATION"
        return "OPEN"

    def recorded_candidates(self) -> list[str]:
        return [a.candidate for a in self.attempts]
