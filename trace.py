"""Requirement-to-evidence traceability (P4-09) — end-to-end chains.

Every requirement must terminate in exactly one of the seven allowed states;
no requirement may disappear between specification and final report. Chains
reference intent/artifact/evidence objects by ID (never by prose).
"""
from __future__ import annotations

from dataclasses import dataclass, field

TERMINAL_STATES = ("EXECUTED", "NOT_EXECUTED", "PASS", "FAIL", "UNPROVEN",
                   "UNAVAILABLE", "SKIPPED_BY_POLICY")


@dataclass
class TraceLink:
    requirement_id: str
    intent_id: str = ""
    artifact_id: str = ""
    execution_id: str = ""
    evidence_id: str = ""
    disposition: str = ""      # terminal state once closed


@dataclass
class Traceability:
    links: dict = field(default_factory=dict)  # requirement_id -> TraceLink

    def register(self, requirement_id: str) -> TraceLink:
        if requirement_id in self.links:
            raise ValueError(f"requirement {requirement_id} already registered (no duplicates)")
        link = TraceLink(requirement_id)
        self.links[requirement_id] = link
        return link

    def attach(self, requirement_id: str, **fields) -> TraceLink:
        if requirement_id not in self.links:
            raise KeyError(f"requirement {requirement_id} unknown: register first (no silent creation)")
        link = self.links[requirement_id]
        for k, v in fields.items():
            if not hasattr(link, k):
                raise ValueError(f"unknown trace field '{k}'")
            setattr(link, k, v)
        return link

    def close(self, requirement_id: str, disposition: str) -> TraceLink:
        if disposition not in TERMINAL_STATES:
            raise ValueError(f"disposition '{disposition}' not in {TERMINAL_STATES}")
        return self.attach(requirement_id, disposition=disposition)

    def completeness(self) -> dict:
        """Fraction of requirements with terminal dispositions + the gap list."""
        total = len(self.links)
        closed = [r for r, l in self.links.items() if l.disposition in TERMINAL_STATES]
        missing = sorted(set(self.links) - set(closed))
        return {"total": total, "closed": len(closed),
                "completeness": (len(closed) / total) if total else 1.0,
                "missing": missing}
