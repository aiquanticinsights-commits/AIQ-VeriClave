"""P0 minimal system profile + BoN ablation runner (adopted as-is).

P0 = deterministic router + ONE primary generator + BoN=3 + machine checks +
Judge + evidence + ≤3 closure rounds. No GRPO, no learned router, no ensemble
beyond BoN. The ablation runner (n=1/3/5/8) answers "does more generation
actually help C1/C2/C3/cost?" before n=8 is ever paid for.
"""
from __future__ import annotations

from router import estimate_call_cost, run_task

P0_PROFILE = {
    "generators": ["qwen3-coder-next"],  # Generator-01 (replaceable, not married)
    "bon": 3,
    "router": "deterministic",
    "min_rounds": 2,
    "max_rounds": 3,
    "train": "nothing",                  # P0 trains nothing, by decision
    "inference": "llama.cpp-gguf-local",  # CPU-first: quantized local runtime
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

# P0 benchmark split: own IP first, external held-out never leaking into
# training, prompts, thresholds, mutation templates, or judge tuning.
P0_BENCHMARKS = {
    "P0-A": "RideProtect-RV v2.5 (internal development set)",
    "P0-B": "MIPI CSI-2 (internal validation set)",
    "P0-C": "external held-out designs (independent evaluation only)",
}

# P0 dashboard fields (every run reports all of these; no cherry-picking).
DASHBOARD_FIELDS = ("tasks", "candidates", "syntax_valid", "sim_valid",
                    "assertions_proven", "mutants_detected", "kill_rate",
                    "top3_localization", "closure_rate", "audit_complete",
                    "false_positive_rate", "avg_cost_per_task",
                    "avg_cpu_time_per_task", "avg_tokens_per_task")


def run_ablation(task, generate, verify, ns: tuple[int, ...] = (1, 3, 5)) -> dict:
    """Same task across BoN widths (CPU-first P0 default n=1/3/5; n=8 only as
    an extended option): closure/rounds/approvals + estimated cost, so wider
    sampling must *earn* its keep over n=3 before adoption."""
    rows = {}
    for n in ns:
        r = run_task(task, generate, verify, k=n, min_rounds=2, max_rounds=3,
                     cascade=False)
        cost = n * r["rounds"] * estimate_call_cost("qwen3-coder-next",
                                                    task.difficulty)
        rows[n] = {"closed": r["winner"] is not None, "rounds": r["rounds"],
                   "approvals": r["approvals"], "est_cost_usd": round(cost, 6)}
    return rows
