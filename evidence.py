"""Evidence ledger — append-only, hash-chained record of verification truth.

Every accepted artifact links requirement -> artifact -> machine checks ->
verdict -> human sign-off. Audit completeness is computed, not asserted:
C4 (zero silently-dropped gaps) is the fraction of ledger entries carrying
both evidence and disposition.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


@dataclass
class EvidenceRecord:
    requirement_id: str
    artifact: str            # e.g. "TB/wb_dma/fr m v3", "SVA/fifo_full"
    checks: dict             # e.g. {"syntax": True, "equiv": True, "proof": False}
    verdict: str             # "PASS" | "FAIL" | "DISPOSITIONED"
    signed_by: str = ""      # human identity; empty = unsigned
    prev_hash: str = ""
    hash: str = field(default="", init=False)

    def seal(self) -> str:
        body = json.dumps([self.requirement_id, self.artifact, self.checks,
                           self.verdict, self.signed_by, self.prev_hash],
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
                               r.verdict, r.signed_by, r.prev_hash], sort_keys=True)
            if hashlib.sha256(body.encode()).hexdigest() != r.hash:
                return False
            prev = r.hash
        return True

    def audit_completeness(self) -> float:
        """Fraction of records with verdict + (evidence or disposition).

        C4 demands 1.0: no record may sit verdict-less or evidence-less.
        """
        if not self.records:
            return 1.0
        ok = sum(1 for r in self.records
                 if r.verdict in ("PASS", "FAIL", "DISPOSITIONED")
                 and (r.checks or r.verdict == "DISPOSITIONED"))
        return ok / len(self.records)

    def signoff(self, requirement_id: str, human: str) -> EvidenceRecord:
        """Human sign-off record. Empty human identity is rejected outright."""
        if not human or not human.strip():
            raise ValueError("sign-off requires a named human; anonymous sign-off denied")
        return self.append(EvidenceRecord(requirement_id, "SIGN-OFF",
                                          {"reviewed": True}, "PASS", signed_by=human))

    def to_json(self) -> str:
        return json.dumps([r.__dict__ for r in self.records], indent=2)
