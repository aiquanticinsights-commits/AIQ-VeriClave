"""AIQ-VeriClave reference scaffold — ensemble router + eval harness (CPU-only).

Real backends (Verilator/SymbiYosys/LLM endpoints) plug in behind the
Verifier/Generator protocols; the shipped mocks let any developer run the
full loop and read a metrics report with zero infra. See
AIQ_VERICLAVE_MODEL_BLUEPRINT.md §3 (architecture) and §6 (rating).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


# --------------------------------------------------------------------------
# Task model
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Task:
    task_id: str
    kind: str            # "mutant-kill" | "sva-validity" | "localization" | "coverage"
    difficulty: int      # 1 (easy) .. 5 (hard)
    payload: dict = field(default_factory=dict)


@dataclass
class Candidate:
    task_id: str
    generator: str
    output: str
    # machine-verifier verdicts, e.g. {"syntax": True, "equiv": False, ...}
    verdicts: dict = field(default_factory=dict)

    @property
    def approvals(self) -> int:
        return sum(1 for v in self.verdicts.values() if v is True)


# --------------------------------------------------------------------------
# Router — RouteMoA-inspired heuristic scorer (no training required).
# Picks top-k generators per task kind; a learned 86M scorer slots in later.
# MODEL-AGNOSTIC P0 (frozen architecture, 2026-09-29): P0 never names a
# foundation model. "selected-open-llm" is the bake-off winner alias —
# P0-A starts it on gpt-oss-20b (local LMStudio) until the P0-B bake-off
# (BAKEOFF_CANDIDATES, same benchmark, correctness/quality/resources/
# latency/tokens/cost) freezes the baseline. Capability priors below are
# pre-bake-off placeholders replaced by measured values at baseline freeze.
# --------------------------------------------------------------------------

# P0-B bake-off slate (approved 2026-09-28): same verification benchmark,
# selection on measured bands — never general benchmarks alone.
BAKEOFF_CANDIDATES = ("gpt-oss-20b", "deepseek-coder-6.7b", "llama-3.1-8b",
                      "qwen3-coder-next")

# Bake-off winner alias. P0 code paths reference ONLY this name.
BASELINE_GENERATOR = "selected-open-llm"

# Capability prior per generator family, per task kind (0..1). Frozen P0-B v2
# (2026-09-29, wb_dma-v2, n=10/kind): trio + alias carry MEASURED bake-off
# rates (see P0B_V2_BASELINE.json); remote entries remain published bands
# until live backends replace them. v2 scope note: sva-validity here is
# SYNTACTIC validity (lint-clean immediate forms), not FPV-proven — C2 still
# needs the loop/formal at scale. Small-n caveat retired for the trio.
CAPABILITY = {
    "selected-open-llm": {"mutant-kill": 0.2, "sva-validity": 1.0, "localization": 0.5, "coverage": 1.0},
    "gpt-oss-20b":        {"mutant-kill": 0.70, "sva-validity": 0.65, "localization": 0.60, "coverage": 0.59},
    "deepseek-coder-6.7b": {"mutant-kill": 0.3, "sva-validity": 0.0, "localization": 0.3, "coverage": 1.0},
    "llama-3.1-8b":       {"mutant-kill": 0.2, "sva-validity": 1.0, "localization": 0.5, "coverage": 1.0},
    "qwen3-coder-next":   {"mutant-kill": 0.71, "sva-validity": 0.66, "localization": 0.62, "coverage": 0.60},
    "deepseek-v3.2":      {"mutant-kill": 0.70, "sva-validity": 0.64, "localization": 0.60, "coverage": 0.58},
    "glm-4.7":            {"mutant-kill": 0.72, "sva-validity": 0.63, "localization": 0.61, "coverage": 0.59},
    "minimax-m2.5":       {"mutant-kill": 0.71, "sva-validity": 0.62, "localization": 0.60, "coverage": 0.58},
    "kimi-k2.5":          {"mutant-kill": 0.70, "sva-validity": 0.62, "localization": 0.59, "coverage": 0.57},
}

# Per-call cost weights (relative); local LMStudio trio cheapest (no API spend).
COST = {
    "selected-open-llm": 1.0,
    "gpt-oss-20b": 1.0,
    "deepseek-coder-6.7b": 1.1,
    "llama-3.1-8b": 1.2,
    "qwen3-coder-next": 1.5,
    "deepseek-v3.2": 4.0,
    "glm-4.7": 3.0,
    "minimax-m2.5": 2.0,
    "kimi-k2.5": 3.5,
}

# Per-1M-token prices in USD (editable; local trio = nominal operating bands —
# local inference has no per-token bill, values keep cost math meaningful).
# Tuple: (input $/1M, output $/1M, cached-read $/1M).
PRICE = {
    "selected-open-llm": (0.05, 0.20, 0.005),
    "gpt-oss-20b": (0.05, 0.20, 0.005),
    "deepseek-coder-6.7b": (0.05, 0.20, 0.005),
    "llama-3.1-8b": (0.05, 0.20, 0.005),
    "qwen3-coder-next": (0.20, 0.80, 0.02),
    "deepseek-v3.2": (1.00, 3.00, 0.10),
    "glm-4.7": (0.80, 2.40, 0.08),
    "minimax-m2.5": (0.30, 1.20, 0.03),
    "kimi-k2.5": (0.60, 3.00, 0.06),
}

# Hard per-task budget (USD). Combos pricing above this are never shortlisted
# (cheapest generator always survives, so the list is never empty).
TASK_BUDGET_USD = 0.50


def mock_tokens(difficulty: int) -> tuple[int, int]:
    """Conservative per-call token shape: input grows with difficulty
    (RTL block + VCD slice + history), output stays small (draft/decision)."""
    return 1500 + 800 * difficulty, 400 + 100 * difficulty


def estimate_call_cost(gen: str, difficulty: int) -> float:
    """Upper-bound USD for one uncached call (no cache credit — conservative)."""
    it, ot = mock_tokens(difficulty)
    pi, po, _ = PRICE[gen]
    return it / 1e6 * pi + ot / 1e6 * po


def cheapest(task: Task) -> str:
    """Cheapest generator (cascade round-1 pick)."""
    return min(CAPABILITY, key=lambda n: COST[n])


def bon_width(task: Task) -> int:
    """Adaptive BoN width: 3 / 5 / 8 by difficulty (accepted assumption:
    easy tasks stay easy; §6 bands re-validate per release)."""
    if task.difficulty <= 2:
        return 3
    if task.difficulty <= 4:
        return 5
    return 8


def score_generator(name: str, task: Task) -> float:
    """Performance-first, then cost — mirrors RouteMoA ranking priority."""
    perf = CAPABILITY[name][task.kind]
    # Harder tasks discount cheap-but-weak picks less; easy tasks favor cheap.
    cost_penalty = (COST[name] - 1.0) * 0.01 * (6 - task.difficulty)
    return perf - cost_penalty


def route(task: Task, k: int = 3, max_cost_usd: float | None = None) -> list[str]:
    """Top-k generator shortlist for a task (RouteMoA default k=3).

    With max_cost_usd set, shortlist members pricing above budget are dropped;
    the cheapest generator always survives so the list is never empty."""
    ranked = sorted(CAPABILITY, key=lambda n: score_generator(n, task), reverse=True)
    short = ranked[:k]
    if max_cost_usd is not None:
        cheap = cheapest(task)
        short = [g for g in short if estimate_call_cost(g, task.difficulty) <= max_cost_usd]
        if cheap not in short:
            short = [cheap] + short
    return short


# --------------------------------------------------------------------------
# Aggregation — majority vote + Judge filter (TUMIX min-2-rounds discipline
# and CorrectBench "discard unproven" rule live here in full implementation).
# --------------------------------------------------------------------------

def judge_filter(cands: list[Candidate], required: tuple[str, ...] = ("syntax",)) -> list[Candidate]:
    """Drop any candidate failing a required machine verdict. Never repairs into truth."""
    return [c for c in cands if all(c.verdicts.get(r, False) for r in required)]


def majority_vote(cands: list[Candidate]) -> Candidate | None:
    """Most approvals wins; ties broken by generator score order (stable)."""
    if not cands:
        return None
    order = list(CAPABILITY)

    def tiebreak(c: Candidate) -> int:
        try:
            return -order.index(c.generator)
        except ValueError:
            return 0  # unknown generators sort last, stably

    best = max(cands, key=lambda c: (c.approvals, tiebreak(c)))
    return best


def run_task(task: Task, generate, verify, k: int | None = None,
             min_rounds: int = 2, max_rounds: int = 3,
             cascade: bool = True, max_cost_usd: float | None = None) -> dict:
    """One task through generate→verify→judge→(bounded closure).

    k=None selects the adaptive BoN width for the task difficulty.
    cascade=True runs round 1 on the cheapest generator only and escalates
    to the full shortlist solely on Judge fail (inverts always-ensemble cost).
    Closure boundary (frozen architecture): at most max_rounds automatic
    rounds; a task with no winner afterwards sets escalated_to_human=True —
    no automatic fourth round is ever permitted.
    """
    if k is None:
        k = bon_width(task)
    shortlist = route(task, k=k, max_cost_usd=max_cost_usd)
    rounds, winner, history = 0, None, []
    while rounds < max_rounds:
        rounds += 1
        # Cascade: cheapest-only first round; full shortlist from round 2.
        active = [cheapest(task)] if (cascade and rounds == 1) else shortlist
        cands = []
        for g in active:
            out = generate(g, task, rounds)
            cands.append(Candidate(task.task_id, g, out, verify(g, task, out)))
        judged = judge_filter(cands)
        winner = majority_vote(judged)
        history.append([(c.generator, c.approvals) for c in cands])
        # TUMIX discipline: never stop before min_rounds (overconfident early exit).
        if rounds >= min_rounds and winner is not None and winner.approvals >= 3:
            break
    return {"task_id": task.task_id, "winner": winner.generator if winner else None,
            "approvals": winner.approvals if winner else 0, "rounds": rounds,
            "shortlist": shortlist, "history": history,
            "bon_width": k, "cascaded": cascade,
            "escalated_to_human": winner is None}
