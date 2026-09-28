"""Simulator log adapters — one failure-event model across open + commercial tools.

Gap closed: previously Verilator-only. Commercial teams run VCS / Questa /
Xcelium / Vivado-xsim; their logs now normalize into the same FailureEvent
stream the Judge and sign-off ledger consume. Constraint solving itself stays
inside the simulator (see uvm_gen.py boundary note); adapters parse results.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class FailureEvent:
    tool: str
    severity: str          # "error" | "failure" | "warning"
    message: str
    file: str = ""
    line: int = 0
    sim_time: str = ""
    raw: str = ""


class SimAdapter:
    """Base: subclasses declare (regex, severity) rules + file:line extraction."""
    name = "base"
    rules: tuple = ()      # ((pattern, severity), ...)
    filepat = re.compile(r"([A-Za-z0-9_./\\-]+\.(?:sv|v|svh|vhdl?|vhd))[\(:, :]+(\d+)")

    def parse_log(self, text: str) -> list[FailureEvent]:
        events = []
        for ln in text.splitlines():
            s = ln.strip()
            if not s:
                continue
            for pat, sev in self.rules:
                if re.search(pat, s):
                    m = self.filepat.search(s)
                    events.append(FailureEvent(
                        tool=self.name, severity=sev, message=s[:300],
                        file=m.group(1) if m else "",
                        line=int(m.group(2)) if m else 0, raw=s[:300]))
                    break
        return events


class VerilatorAdapter(SimAdapter):
    name = "verilator"
    rules = ((r"%Error", "error"), (r"Assertion failed", "failure"),
             (r"\bFAILED\b|\bfailed\b", "failure"), (r"%Warning", "warning"))


class VCSAdapter(SimAdapter):
    """Synopsys VCS: vlogan/vcs/elab + simv runtime lines."""
    name = "vcs"
    rules = ((r"\bError-", "error"), (r"UVM_ERROR|UVM_FATAL", "failure"),
             (r"TEST (FAILED|failed)|test failed", "failure"),
             (r"\bWarning-", "warning"), (r"Lint-[A-Z]+", "warning"))


class QuestaAdapter(SimAdapter):
    """Siemens Questa (vlog/vsim): '** Error' / UVM / Break lines."""
    name = "questa"
    rules = ((r"\*\* Error", "error"), (r"UVM_ERROR|UVM_FATAL", "failure"),
             (r"# FAIL|Break in Module|TEST FAILED", "failure"),
             (r"\*\* Warning", "warning"))


class XceliumAdapter(SimAdapter):
    """Cadence Xcelium (xmvlog/xmelab/xmsim): E,/W, prefixes + UVM."""
    name = "xcelium"
    rules = ((r"\*E,[A-Z0-9]+", "error"), (r"UVM_ERROR|UVM_FATAL", "failure"),
             (r"TEST FAILED|ncsim: \*E", "failure"),
             (r"\*W,[A-Z0-9]+", "warning"))


class VivadoAdapter(SimAdapter):
    """AMD Vivado xsim / labtools runtime lines."""
    name = "vivado-xsim"
    rules = ((r"^ERROR:", "error"), (r"Failure:|Test (Failed|FAILED)", "failure"),
             (r"^WARNING:", "warning"), (r"UVM_ERROR", "failure"))


ADAPTERS: dict[str, SimAdapter] = {a.name: a for a in
    (VerilatorAdapter(), VCSAdapter(), QuestaAdapter(), XceliumAdapter(), VivadoAdapter())}


def detect_tool(text: str) -> str:
    """Best-effort tool identification from log banners (for routing)."""
    probes = (("vcs", r"VCS-[A-Z]|Chronologic VCS|synopsys.*vcs"),
              ("questa", r"Questa|vsim-|Mentor Graphics|QuestaSim"),
              ("xcelium", r"xmsim|xmvlog|Xcelium|ncsim"),
              ("vivado-xsim", r"xsim|XSim|Vivado Simulator"),
              ("verilator", r"Verilator|%Error|verilated"))
    low = text[:4000]
    for tool, pat in probes:
        if re.search(pat, low, re.IGNORECASE):
            return tool
    return "verilator"  # default: open-toolchain home flow


def normalize(text: str, tool: str = "") -> list[FailureEvent]:
    """Parse any supported log into FailureEvents (auto-detects tool)."""
    tool = tool or detect_tool(text)
    adapter = ADAPTERS.get(tool, ADAPTERS["verilator"])
    return adapter.parse_log(text)


def summarize(events: list[FailureEvent]) -> dict:
    sev = [e.severity for e in events]
    return {"errors": sev.count("error"), "failures": sev.count("failure"),
            "warnings": sev.count("warning"), "total": len(events)}
