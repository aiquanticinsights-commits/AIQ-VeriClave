"""P0 minimal system profile + BoN ablation runner (frozen architecture).

P0 = deterministic router + ONE selected generator (bake-off winner alias) +
BoN + machine checks + Judge + evidence + ≤3 closure rounds (hard stop, then
human escalation). No GRPO, no learned router, no ensemble beyond BoN. The
ablation runner (n=1/3/5; n=8 only as a measured extension) answers "does
more generation actually help C1/C2/C3/cost?" before wider sampling is paid for.
"""
from __future__ import annotations

from router import BASELINE_GENERATOR, estimate_call_cost, run_task

# Model-agnostic P0 (frozen 2026-09-29): no foundation model is named here.
# P0-A starts the alias on gpt-oss-20b (local LMStudio); P0-B bakes off
# BAKEOFF_CANDIDATES on the same benchmark and freezes the baseline.
P0_PROFILE = {
    "generators": [BASELINE_GENERATOR],  # bake-off winner alias, never a model pin
    "bon": 3,
    "router": "deterministic",
    "min_rounds": 2,
    "max_rounds": 3,                     # hard boundary: then escalate_to_human
    "train": "nothing",                  # P0 trains nothing, by decision
    "inference": "lmstudio-local",       # local OpenAI-compatible runtime (see lock-in §6)
    "compute": "local-cpu",              # local CPU default; cloud = optional
}

# PHASE 0–7 roadmap (adopted CPU-first strategy; supersedes P0–P4 shorthand).
PHASES = {
    0: "CPU-first P0 (open stack/models, no training, C1–C5 baseline)",
    1: "Model benchmark: 1B/3B/7B-class on CPU, Stage A/B baseline pick",
    2: "Verification system: selected model + BoN + Judge + closure + C1–C5",
    3: "Proprietary dataset: trajectories, mutants, failures, proofs, closures",
    4: "SFT/LoRA only if PHASE 0–2 prove a model-specific limitation",
    5: "Specialized models (router, classifiers, reranker, localization)",
    6: "GRPO experiment only if a measured residual suits RL",
    7: "Productization: local-first, optional open/accelerated cloud",
}

# P0-B baseline freeze (2026-09-28, wb_dma-v1, bakeoff.py, deterministic
# scorers, no LLM judge): winner llama-3.1-8b — highest pass rate (0.50 vs
# 0.33) AND lowest latency (46.3s vs 77.5s) AND fewest tokens (1006 vs 1490).
# gpt-oss-20b skipped (12.23 GB RAM guardrail on this machine — recorded in
# P0B_BASELINE.json, never silently dropped). Alias priors mirror the winner;
# full measured table lives in P0B_BASELINE.json (committed evidence).
BASELINE = {
    "winner": "llama-3.1-8b",
    "date": "2026-09-28",
    "benchmark_version": "wb_dma-v1",
    "evidence": "P0B_BASELINE.json",
    "runner_up": "deepseek-coder-6.7b",
    "skipped": {"gpt-oss-20b": "insufficient RAM (12.23 GB guardrail)"},
}

# P0 benchmark split: own IP first, external held-out never leaking into
# training, prompts, thresholds, mutation templates, or judge tuning.
P0_BENCHMARKS = {
    "P0-A": "RideProtect-RV v2.5 (internal development set)",
    "P0-B": "MIPI CSI-2 (internal validation set)",
    "P0-C": "external held-out designs (independent evaluation only)",
}

# P0 dashboard fields (every run reports all of these; no cherry-picking).
# Quality / efficiency / human-oversight / reproducibility per frozen Gates A–E.
# Human-efficiency fields are measured at the review dashboard; the harness
# reports None until measured (never fabricates them).
DASHBOARD_FIELDS = ("tasks", "candidates", "syntax_valid", "sim_valid",
                    "assertions_proven", "mutants_detected", "kill_rate",
                    "top3_localization", "closure_rate", "audit_complete",
                    "false_positive_rate", "avg_cost_per_task",
                    "avg_cpu_time_per_task", "avg_tokens_per_task",
                    "closure_success_rate", "first_pass_rate",
                    "avg_closure_iterations", "median_closure_iterations",
                    "max_closure_iterations", "engineer_review_time_per_task",
                    "human_rejection_rate", "human_override_rate",
                    "evidence_items_reviewed_per_task", "signoff_status",
                    "environment", "tool_versions", "model_runtime",
                    "benchmark_version", "dataset_version", "seed",
                    "artifact_hashes", "cross_env_variance")


def run_ablation(task, generate, verify, ns: tuple[int, ...] = (1, 3, 5)) -> dict:
    """Same task across BoN widths (P0 start n=1/3/5; n=8 only as a measured
    extension): closure/rounds/approvals/escalation + estimated cost, so wider
    sampling must *earn* its keep over n=3 before adoption. Cost is priced at
    the model-agnostic baseline alias (bake-off winner economics)."""
    rows = {}
    for n in ns:
        r = run_task(task, generate, verify, k=n, min_rounds=2, max_rounds=3,
                     cascade=False)
        cost = n * r["rounds"] * estimate_call_cost(BASELINE_GENERATOR,
                                                    task.difficulty)
        rows[n] = {"closed": r["winner"] is not None, "rounds": r["rounds"],
                   "approvals": r["approvals"], "est_cost_usd": round(cost, 6),
                   "escalated_to_human": r["escalated_to_human"]}
    return rows
