"""EDA adapter maturity registry (P4-10) — L1..L5 per tool x function.

Levels: L1 parser tested · L2 import/export integrated · L3 execution
integrated · L4 real execution validated · L5 reproducibility + disagreement
qualified. Levels are EVIDENCE-BACKED: each entry cites the artifact proving
it. One qualified Vivado function never implies full Vivado support.
"""
from __future__ import annotations

from dataclasses import dataclass

LEVELS = ("L1", "L2", "L3", "L4", "L5")


@dataclass(frozen=True)
class AdapterEntry:
    tool: str            # verilator | yosys | symbiyosys | vcs | questa | xcelium | vivado-xsim | uvm-gen
    function: str        # lint | sim | formal | log-parse | block-run | tlm-gen | ...
    level: str
    evidence: str        # repo artifact proving the level (file or CI job)
    limits: str = ""     # what is explicitly NOT covered


REGISTRY: tuple[AdapterEntry, ...] = (
    AdapterEntry("verilator", "lint+sim", "L4", "vericlave.yml P0 gate runs Verilator on CI",
                 "version-pinned per requirements; sby-gated formal separate"),
    AdapterEntry("yosys", "synth-check", "L4", "vericlave.yml installs + runs yosys -V gated checks",
                 ""),
    AdapterEntry("symbiyosys", "formal-proof", "L4", "SBY_SMOKE.json 9/9 + GATES_ABDE.json ok+buggy pairs",
                 "bounded policies per formal_policy.py; no unbounded claims"),
    AdapterEntry("vcs", "log-parse", "L1", "test_adoption.py VCS fixture (Error-/UVM_ERROR/TEST FAILED)",
                 "no real VCS execution; syntax validated against fixture only"),
    AdapterEntry("questa", "log-parse", "L1", "test_adoption.py Questa fixture (** Error/vsim/UVM/FAIL)",
                 "no real Questa execution"),
    AdapterEntry("xcelium", "log-parse", "L1", "test_adoption.py Xcelium fixture (*E/*W/UVM_FATAL)",
                 "no real Xcelium execution"),
    AdapterEntry("vivado-xsim", "block-run", "L4", "vivado_adapter.py block runs + VIVADO_GATES.json",
                 "QUALIFIED FUNCTIONS ONLY — never cited as full Vivado support"),
    AdapterEntry("uvm-gen", "tlm-skeleton", "L1", "test_adoption.py structural assertions on 5 generated files",
                 "templates unexecuted in-simulator; solving stays in-simulator"),
)


def level_of(tool: str, function: str = "") -> str:
    """Highest registered level for tool (+function); unknown -> L0 (absent)."""
    hits = [e.level for e in REGISTRY if e.tool == tool and (not function or e.function == function)]
    return max(hits) if hits else "L0"


def qualified(tool: str, function: str = "", minimum: str = "L4") -> bool:
    """Gate helper: is this tool x function qualified to at least `minimum`?"""
    got = level_of(tool, function)
    return got != "L0" and LEVELS.index(got) >= LEVELS.index(minimum)
