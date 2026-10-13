"""Structured verification intent — typed IR between requirement and artifact.

P4-05: widths, signal names, clocks, reset polarity, module names, parameters,
temporal operators, and artifact type are represented EXPLICITLY so generation
never infers what should be declared. Validators fail closed: an intent that
does not type-check cannot enter the generation lane.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

ARTIFACT_TYPES = ("sva", "test", "coverage", "checker")
RESET_POLARITIES = ("active-high", "active-low")
RESET_KINDS = ("sync", "async")


@dataclass
class Signal:
    name: str
    width: int
    clock: str = "clk"


@dataclass
class Clock:
    name: str
    period_ns: float


@dataclass
class Reset:
    name: str
    polarity: str      # active-high | active-low
    kind: str          # sync | async


@dataclass
class VerificationIntent:
    requirement_id: str
    module: str
    artifact: str                        # sva | test | coverage | checker
    signals: list                        # list[Signal]
    clocks: list = field(default_factory=list)       # list[Clock]
    reset: object = None                 # Reset | None
    parameters: dict = field(default_factory=dict)
    temporal: list = field(default_factory=list)     # e.g. ["|->", "##1", "s_eventually"]
    constraints: list = field(default_factory=list)  # free-form solver hints

    def validate(self) -> list[str]:
        """Return error strings; empty means the intent type-checks."""
        errs = []
        if not self.requirement_id or not self.requirement_id.strip():
            errs.append("requirement_id missing")
        if not self.module or not self.module.strip():
            errs.append("module missing")
        if self.artifact not in ARTIFACT_TYPES:
            errs.append(f"artifact '{self.artifact}' not in {ARTIFACT_TYPES}")
        if not self.signals:
            errs.append("signals empty: nothing to verify")
        clocks = {c.name for c in self.clocks}
        for s in self.signals:
            if not s.name or not s.name.strip():
                errs.append("signal with empty name")
            if not isinstance(s.width, int) or s.width < 1:
                errs.append(f"signal '{s.name}': width must be a positive int")
            if s.clock not in clocks:
                errs.append(f"signal '{s.name}': clock '{s.clock}' not declared")
        for c in self.clocks:
            if c.period_ns <= 0:
                errs.append(f"clock '{c.name}': period_ns must be > 0")
        if self.reset is not None:
            if self.reset.polarity not in RESET_POLARITIES:
                errs.append(f"reset polarity '{self.reset.polarity}' invalid")
            if self.reset.kind not in RESET_KINDS:
                errs.append(f"reset kind '{self.reset.kind}' invalid")
        for t in self.temporal:
            if not isinstance(t, str) or not t.strip():
                errs.append("temporal operator must be a non-empty string")
        return errs

    @property
    def valid(self) -> bool:
        return not self.validate()

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @staticmethod
    def from_dict(d: dict) -> "VerificationIntent":
        sigs = [Signal(**s) if isinstance(s, dict) else s for s in d.get("signals", [])]
        clks = [Clock(**c) if isinstance(c, dict) else c for c in d.get("clocks", [])]
        rst = d.get("reset")
        if isinstance(rst, dict):
            rst = Reset(**rst)
        return VerificationIntent(
            requirement_id=d.get("requirement_id", ""), module=d.get("module", ""),
            artifact=d.get("artifact", ""), signals=sigs, clocks=clks, reset=rst,
            parameters=d.get("parameters", {}), temporal=d.get("temporal", []),
            constraints=d.get("constraints", []))
