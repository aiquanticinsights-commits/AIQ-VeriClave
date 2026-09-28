"""Eval harness — runs task suites through run_task() and emits a metrics report.

Mock generator/verifier backends model published accuracy bands so the loop,
gates, and report format are exercisable with zero infra. Real backends:
  - generate -> OpenAI-compatible endpoint (vLLM/Ollama/FreeLLMAPI/OmniRoute)
  - verify   -> Verilator (equiv), Yosys/sv-parser (syntax), SymbiYosys (proof),
               BugGen-mutant kill check, requirement-ID trace check.
Report maps 1:1 onto blueprint §6 (C1–C5 + cost).
"""
from __future__ import annotations

import json
import random
import time

from router import PRICE, Task, mock_tokens, run_task

# Mock per-generator, per-kind success probabilities. Frozen P0-B v1: local
# trio mirrors MEASURED bake-off rates (P0B_BASELINE.json, wb_dma-v1, n=1-2);
# remote entries remain published-band stand-ins until live backends replace
# the mocks in production runs.
MOCK_P = {
    "selected-open-llm":   {"mutant-kill": 0.0, "sva-validity": 0.5, "localization": 0.5, "coverage": 1.0},
    "gpt-oss-20b":         {"mutant-kill": 0.70, "sva-validity": 0.65, "localization": 0.60, "coverage": 0.59},
    "deepseek-coder-6.7b": {"mutant-kill": 0.0, "sva-validity": 0.0, "localization": 0.5, "coverage": 1.0},
    "llama-3.1-8b":        {"mutant-kill": 0.0, "sva-validity": 0.5, "localization": 0.5, "coverage": 1.0},
    "qwen3-coder-next":   {"mutant-kill": 0.71, "sva-validity": 0.66, "localization": 0.62, "coverage": 0.60},
    "deepseek-v3.2":      {"mutant-kill": 0.70, "sva-validity": 0.64, "localization": 0.60, "coverage": 0.58},
    "glm-4.7":            {"mutant-kill": 0.72, "sva-validity": 0.63, "localization": 0.61, "coverage": 0.59},
    "minimax-m2.5":       {"mutant-kill": 0.71, "sva-validity": 0.62, "localization": 0.60, "coverage": 0.58},
    "kimi-k2.5":          {"mutant-kill": 0.70, "sva-validity": 0.62, "localization": 0.59, "coverage": 0.57},
}

VERDICT_KEYS = ("syntax", "equiv", "proof")


def mock_generate(gen: str, task: Task, _round: int) -> str:
    return f"{gen}::draft::{task.task_id}::r{_round}"


def mock_verify(gen: str, task: Task, _out: str, rng: random.Random) -> dict:
    p = MOCK_P[gen][task.kind]
    # syntax nearly always holds for these generators; equiv/proof carry the risk.
    return {"syntax": rng.random() < 0.98,
            "equiv": rng.random() < p,
            "proof": rng.random() < p}


def make_suite(n_per_kind: int = 25, seed: int = 7) -> list[Task]:
    rng = random.Random(seed)
    kinds = ["mutant-kill", "sva-validity", "localization", "coverage"]
    suite, i = [], 0
    for kind in kinds:
        for _ in range(n_per_kind):
            i += 1
            suite.append(Task(f"T{i:03d}", kind, rng.randint(1, 5)))
    return suite


class TokenLedger:
    """Per-task, per-stage token + USD accounting (the gate every cost
    lever reports to). Later rounds earn cached-read credit: stable prefixes
    (spec/FRM/tool-defs) hit cache, dynamic tails (VCD/slices) do not."""

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def record(self, task_id: str, stage: str, generator: str,
               input_tok: int, output_tok: int, cached_frac: float = 0.0) -> None:
        pi, po, pc = PRICE[generator]
        cached_frac = max(0.0, min(1.0, cached_frac))
        fresh = input_tok * (1.0 - cached_frac)
        cost = (fresh / 1e6 * pi + input_tok * cached_frac / 1e6 * pc
                + output_tok / 1e6 * po)
        self.rows.append({"task": task_id, "stage": stage, "generator": generator,
                          "input": input_tok, "output": output_tok,
                          "cached_frac": cached_frac, "cost_usd": cost})

    def summary(self) -> dict:
        total_in = sum(r["input"] for r in self.rows)
        total_out = sum(r["output"] for r in self.rows)
        total_cached = sum(r["input"] * r["cached_frac"] for r in self.rows)
        by_gen: dict[str, float] = {}
        for r in self.rows:
            by_gen[r["generator"]] = by_gen.get(r["generator"], 0.0) + r["cost_usd"]
        return {"input_tokens": total_in, "output_tokens": total_out,
                "cached_input_tokens": int(total_cached),
                "cost_usd": round(sum(r["cost_usd"] for r in self.rows), 6),
                "by_generator_usd": {g: round(c, 6) for g, c in by_gen.items()},
                "calls": len(self.rows)}


def mock_usage(gen: str, task: Task, round_no: int, rng: random.Random) -> tuple[int, int, float]:
    """Deterministic token shape per call: difficulty-sized I/O, ±10% jitter;
    cached share grows after round 1 (stable prefix reuse)."""
    base_in, base_out = mock_tokens(task.difficulty)
    jit = 0.9 + 0.2 * rng.random()
    cached = 0.0 if round_no <= 1 else 0.6
    return int(base_in * jit), int(base_out * jit), cached


def evaluate(suite: list[Task], seed: int = 7) -> dict:
    rng = random.Random(seed)
    ledger = TokenLedger()

    def gen(g, t, r):
        out = mock_generate(g, t, r)
        it, ot, cf = mock_usage(g, t, r, rng)
        ledger.record(t.task_id, f"gen-r{r}", g, it, ot, cf)
        return out

    results, cpu_s = [], 0.0
    for t in suite:
        start = time.perf_counter()
        results.append(run_task(t, gen,
                                lambda g, ta, o: mock_verify(g, ta, o, rng)))
        cpu_s += time.perf_counter() - start
    by_kind: dict[str, dict] = {}
    for kind in {t.kind for t in suite}:
        rs = [r for r, t in zip(results, suite) if t.kind == kind]
        closed = [r for r in rs if r["winner"] is not None]
        by_kind[kind] = {"tasks": len(rs), "closed": len(closed),
                         "closure_rate": round(len(closed) / len(rs), 4),
                         "avg_rounds": round(sum(r["rounds"] for r in rs) / len(rs), 2)}
    rounds = [r["rounds"] for r in results]
    winners = [r for r in results if r["winner"] is not None]
    # Gate B: closure success = accepted among tasks that required closure
    # (ran past the TUMIX minimum or never found a winner); first-pass =
    # accepted within the minimum rounds (no extra closure iterations).
    requiring = [r for r in results if r["rounds"] > 2 or r["winner"] is None]
    requiring_closed = [r for r in requiring if r["winner"] is not None]
    report = {"total": len(results),
              "closed": sum(1 for r in results if r["winner"] is not None),
              "by_kind": by_kind}
    report["system_accuracy"] = round(report["closed"] / report["total"], 4)
    report["closure_success_rate"] = round(
        len(requiring_closed) / len(requiring), 4) if requiring else 1.0
    report["first_pass_rate"] = round(
        sum(1 for r in winners if r["rounds"] <= 2) / report["total"], 4)
    report["avg_closure_iterations"] = round(sum(rounds) / len(rounds), 2)
    srt = sorted(rounds)
    report["median_closure_iterations"] = round(
        (srt[(len(srt) - 1) // 2] + srt[len(srt) // 2]) / 2, 2)
    report["max_closure_iterations"] = max(rounds)
    report["escalated_to_human"] = sum(
        1 for r in results if r["escalated_to_human"])
    report["tokens"] = ledger.summary()
    report["avg_cpu_time_s"] = round(cpu_s / max(1, len(results)), 4)
    report["avg_cost_per_task_usd"] = round(
        ledger.summary()["cost_usd"] / max(1, len(results)), 6)
    # Gates D/E: human-efficiency and cross-env variance are measured at the
    # review dashboard / portability benchmark, not the mock harness — the
    # harness reports them as not-measured (None) rather than fabricating them.
    report["engineer_review_time_per_task"] = None
    report["human_rejection_rate"] = None
    report["human_override_rate"] = None
    report["cross_env_variance"] = None
    return report


if __name__ == "__main__":
    rep = evaluate(make_suite())
    print(json.dumps(rep, indent=2))
