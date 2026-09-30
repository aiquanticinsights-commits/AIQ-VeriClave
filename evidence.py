"""Evidence ledger — append-only, hash-chained record of verification truth.

Every accepted artifact links requirement -> artifact -> machine checks ->
verdict -> human sign-off. Audit completeness is computed, not asserted:
C4 (zero silently-dropped gaps) is the fraction of ledger entries carrying
both evidence and disposition. Frozen architecture: external-tool execution
uses explicit states — EXECUTED / NOT_EXECUTED / PASS / FAIL / UNPROVEN /
UNAVAILABLE / SKIPPED_BY_POLICY (+ DISPOSITIONED for closure dispositions).
NOT_EXECUTED must never silently become PASS: an explicitly recorded
NOT_EXECUTED is complete; a missing or verdict-less entry is not.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

# Frozen verdict set (architecture addendum: evidence-ledger states, plus
# the V6 formal-disposition taxonomy: SIM_COVERED / NOT_APPLICABLE).
KNOWN_VERDICTS = frozenset({
    "PASS", "FAIL", "DISPOSITIONED", "EXECUTED",
    "NOT_EXECUTED", "UNPROVEN", "UNAVAILABLE", "SKIPPED_BY_POLICY",
    "SIM_COVERED", "NOT_APPLICABLE",
})

# Verdicts that are complete without per-check evidence because the record
# itself IS the disposition (explicitly recorded, never silent).
EVIDENCE_OPTIONAL = frozenset({
    "DISPOSITIONED", "NOT_EXECUTED", "SKIPPED_BY_POLICY", "UNAVAILABLE",
    "NOT_APPLICABLE",
})


@dataclass
class EvidenceRecord:
    requirement_id: str
    artifact: str            # e.g. "TB/wb_dma/frm v3", "SVA/fifo_full"
    checks: dict             # e.g. {"syntax": True, "equiv": True, "proof": False}
    verdict: str             # one of KNOWN_VERDICTS
    signed_by: str = ""      # human identity; empty = unsigned
    # Provenance (frozen addendum: every EDA/tool run records these where known)
    tool: str = ""
    tool_version: str = ""
    rtl_commit: str = ""
    run_id: str = ""
    artifact_hashes: dict = field(default_factory=dict)
    prev_hash: str = ""
    hash: str = field(default="", init=False)

    def seal(self) -> str:
        body = json.dumps([self.requirement_id, self.artifact, self.checks,
                           self.verdict, self.signed_by, self.tool,
                           self.tool_version, self.rtl_commit, self.run_id,
                           self.artifact_hashes, self.prev_hash],
                          sort_keys=True)
        self.hash = hashlib.sha256(body.encode()).hexdigest()
        return self.hash


class EvidenceLedger:
    def __init__(self) -> None:
        self.records: list[EvidenceRecord] = []

    def append(self, rec: EvidenceRecord) -> EvidenceRecord:
        rec.prev_hash = self.records[-1].hash if self.records else "GENESIS"
        rec.seal()
        self.records.append(rec)
        return rec

    def verify_chain(self) -> bool:
        """Hash-chain integrity (tamper evidence for the audit trail)."""
        prev = "GENESIS"
        for r in self.records:
            if r.prev_hash != prev:
                return False
            body = json.dumps([r.requirement_id, r.artifact, r.checks,
                               r.verdict, r.signed_by, r.tool, r.tool_version,
                               r.rtl_commit, r.run_id, r.artifact_hashes,
                               r.prev_hash], sort_keys=True)
            if hashlib.sha256(body.encode()).hexdigest() != r.hash:
                return False
            prev = r.hash
        return True

    def audit_completeness(self) -> float:
        """Fraction of records with a known verdict + (evidence or explicit
        disposition). C4 demands 1.0: no record may sit verdict-less,
        under an unknown verdict, or evidence-less without an explicit
        disposition state. NOT_EXECUTED recorded explicitly is complete —
        it must never be rewritten as PASS (see record_not_executed).
        UNPROVEN carries its bounded run as evidence (checks required)."""
        if not self.records:
            return 1.0
        ok = sum(1 for r in self.records
                 if r.verdict in KNOWN_VERDICTS
                 and (r.checks or r.verdict in EVIDENCE_OPTIONAL))
        return ok / len(self.records)

    def record_not_executed(self, requirement_id: str, artifact: str,
                            reason: str, run_id: str = "") -> EvidenceRecord:
        """Explicit NOT_EXECUTED (tool unavailable/skipped-by-policy): the
        ledger records the gap instead of dropping it. The returned record
        must never be mutated into PASS — mutating any sealed record breaks
        verify_chain() by construction."""
        return self.append(EvidenceRecord(requirement_id, artifact,
                                          {"reason": reason}, "NOT_EXECUTED",
                                          run_id=run_id))

    def signoff(self, requirement_id: str, human: str) -> EvidenceRecord:
        """Human sign-off record. Empty human identity is rejected outright."""
        if not human or not human.strip():
            raise ValueError("sign-off requires a named human; anonymous sign-off denied")
        return self.append(EvidenceRecord(requirement_id, "SIGN-OFF",
                                          {"reviewed": True}, "PASS", signed_by=human))

    def to_json(self) -> str:
        return json.dumps([r.__dict__ for r in self.records], indent=2)
