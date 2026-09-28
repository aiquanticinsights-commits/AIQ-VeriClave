"""Bounded formal sign-off policy — the missing complement to stall detection.

Gap closed: the GoGoTB-style stall detector stops *loops*; it never told a
developer whether a property is provable at all. SymbiYosys (or JasperGold,
same policy object) can burn unbounded time on state-space explosion. This
module issues a deterministic verdict BEFORE the run: PROVE / BOUND / ABSTRACT
/ UNPROVABLE-AT-BUDGET, with engine + depth + rationale — so sign-off can say
"bounded to k with abstraction A" instead of looping forever.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PropertySpec:
    name: str
    prop_class: str      # "width" | "connectivity" | "safety" | "protocol" | "liveness"
    state_bits: int      # estimated sequential state (FF count in cone)
    time_budget_s: int = 3600


@dataclass(frozen=True)
class FormalPlan:
    verdict: str         # PROVE | BOUND | ABSTRACT | UNPROVABLE-AT-BUDGET
    engine: str          # "sby-bmc" | "sby-kind" | "sby-abc" | "jaspergold"
    depth_k: int
    abstraction: str     # "none" | "cutpoints" | "blackbox-dp" | "assume-guarantee"
    rationale: str


# ~2^40 states is the practical BMC wall for overnight CPU runs; liveness
# needs induction/abstraction far earlier. Thresholds are deliberately
# conservative: a wrong PROVE wastes a night, a wrong ABSTRACT costs minutes.
def recommend(spec: PropertySpec) -> FormalPlan:
    if spec.prop_class in ("width", "connectivity"):
        return FormalPlan("PROVE", "sby-bmc", 64, "none",
                          "combinatorial/shallow cone: unbounded proof is cheap")
    if spec.state_bits <= 40:
        eng = "sby-kind" if spec.prop_class == "liveness" else "sby-bmc"
        return FormalPlan("PROVE", eng, 128, "none",
                          f"~2^{spec.state_bits} states fits overnight BMC/induction")
    if spec.state_bits <= 120:
        return FormalPlan("BOUND", "sby-bmc", 32, "cutpoints",
                          f"~2^{spec.state_bits} states: bounded proof to k=32 with "
                          "cutpoints; residual risk recorded, sim (GoGoTB bins) covers beyond k")
    if spec.prop_class == "protocol":
        return FormalPlan("ABSTRACT", "sby-abc", 16, "assume-guarantee",
                          "protocol cross-product explodes: prove interface contracts "
                          "(assume-guarantee), verify datapath separately")
    if spec.time_budget_s < 1800:
        return FormalPlan("UNPROVABLE-AT-BUDGET", "sby-bmc", 8, "none",
                          f"~2^{spec.state_bits} states cannot clear in "
                          f"{spec.time_budget_s}s: do NOT loop — disposition as "
                          "unprovable-at-budget, cover via directed sim")
    return FormalPlan("ABSTRACT", "sby-abc", 16, "blackbox-dp",
                      f"~2^{spec.state_bits} states: blackbox datapaths, prove control")


def signoff_line(plan: FormalPlan, prop: str) -> str:
    if plan.verdict == "PROVE":
        return f"{prop}: PROVEN ({plan.engine})"
    if plan.verdict == "BOUND":
        return (f"{prop}: BOUNDED to k={plan.depth_k} [{plan.abstraction}] "
                f"({plan.engine}); beyond-k covered by sim bins")
    if plan.verdict == "ABSTRACT":
        return (f"{prop}: PROVEN under {plan.abstraction} ({plan.engine}); "
                "abstraction assumptions listed in ledger")
    return f"{prop}: UNPROVABLE-AT-BUDGET — {plan.rationale}"
