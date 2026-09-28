"""Canonical verification reward — the executable form of the Stage-2 RL objective.

Equation (blueprint §5, §11): R = w1*kill + w2*proof + w3*cov + w4*loc - w5*cost
Scored GROUP-relative (GRPO discipline: no critic model — candidates are ranked
against their siblings, exactly the BoN n=5-8 sample set). Weights are initial
values from published bands; calibrated at the GRPO gate (PHASE 6, conditional).
"""
from __future__ import annotations

import math

WEIGHTS = {
    "mutant_kill": 1.0,    # BugGen-style: mutant detected by the artifact
    "formal_proof": 1.0,   # SymbiYosys/JasperGold: assertion proven on golden
    "coverage_delta": 0.5, # GoGoTB-style: functional bins closed by this artifact
    "localization": 0.5,   # BluesFL-style: true bug inside Top-3 shortlist
    "cost": 0.2,           # $/task-class unit; keeps cheap winners competitive
}

GROUP_SIZE = (5, 8)  # == BoN sample count: one sample set serves both


def compute_reward(verdicts: dict, cost: float = 0.0,
                   weights: dict | None = None) -> float:
    """verdicts keys: killed (bool), proven (bool), coverage (0..1 float),
    localized (bool). cost in task-cost units (see §A3 ledger)."""
    w = weights or WEIGHTS
    kill = 1.0 if verdicts.get("killed", False) else 0.0
    proof = 1.0 if verdicts.get("proven", False) else 0.0
    cov = max(0.0, min(1.0, float(verdicts.get("coverage", 0.0))))
    loc = 1.0 if verdicts.get("localized", False) else 0.0
    return (w["mutant_kill"] * kill + w["formal_proof"] * proof
            + w["coverage_delta"] * cov + w["localization"] * loc
            - w["cost"] * max(0.0, cost))


def group_normalize(rewards: list[float]) -> list[float]:
    """GRPO core: advantage = (r - group_mean) / (group_std + eps). No critic."""
    n = len(rewards)
    if n == 0:
        return []
    mean = sum(rewards) / n
    var = sum((r - mean) ** 2 for r in rewards) / n
    std = math.sqrt(var) or 1.0
    return [(r - mean) / std for r in rewards]


def select_best(outputs: list, rewards: list[float]) -> tuple:
    """Argmax over group-normalized advantages; ties -> earliest (stable)."""
    adv = group_normalize(rewards)
    best = max(range(len(outputs)), key=lambda i: (adv[i], -i))
    return outputs[best], adv[best]
