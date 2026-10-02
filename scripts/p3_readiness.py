"""P3-D: training-readiness assessment of the existing corpus.

Readiness assessment ONLY — nothing is trained, tokenized for training, or
reformatted for training. The question is: could the existing material
support SFT/LoRA later, and what would have to change first?

Dimensions (all derived from frozen artifacts, no model calls):
  size, diversity, success/failure balance, verifier labels, contamination,
  held-out separation, trajectory quality, failure-mode representation.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    llama = load("P2_M2_LLAMA.json")
    ds = load("P2_M2_DEEPSEEK.json")
    pipe = load("P3_PIPELINE_LLAMA.json")

    # ---- size ----
    r2_turns = len(llama["corpus"]) + len(ds["corpus"])
    t4_s = len(llama["t4"]["samples"]) + len(ds["t4"]["samples"])
    pipe_t4 = len(pipe["t4"]["samples"])
    pipe_r2_prompts = sum(1 for _ in range(pipe["r2"]["n"])) * 5
    total_generations = r2_turns + t4_s + pipe_t4 + pipe_r2_prompts

    # ---- labels: all verifier-sourced? ----
    labels = {
        "t4": "frozen grade_reasoned (deterministic, known gold)",
        "r2_p2": "frozen repair.verify (value_gate + splice + lint wall)",
        "r2_p3c": "same frozen verify + independent value_gate re-derivation",
        "human_labels": 0, "model_graded_labels": 0,
    }

    # ---- success/failure balance ----
    r2_closes = (llama["r2"]["closed"] + ds["r2"]["closed"]
                 + pipe["r2"]["closed"])
    # P2: 60+58 turns produced 3 closes; P3-C: 100 candidates -> 8 closes
    r2_pos = r2_closes
    r2_neg_cases = (llama["r2"]["n"] + ds["r2"]["n"] + pipe["r2"]["n"]
                    - r2_closes)

    # ---- diversity ----
    diversity = {
        "distinct_prompts": 21 + 2,  # 20 R2 + 1 T4 (P2) + 2 pipeline prompts
        "task_families": ["T4 single-letter RCA", "R2 width-literal repair"],
        "design_families": ["synthetic p2r assign modules (1 family)"],
        "models_represented": ["llama-3.1-8b", "deepseek-coder-6.7b"],
        "widths_covered_bits": [4, 8, 12, 16],
    }

    # ---- failure-mode representation ----
    never_single = sorted(set(llama["r2"]["rows"]) -
                          {c for c, v in llama["r2"]["rows"].items()
                           if v["closed"]} -
                          {c for c, v in ds["r2"]["rows"].items()
                           if v["closed"]})
    never_pipe = sorted(c for c, v in pipe["r2"]["rows"].items()
                        if not v["closed"])

    # ---- trajectory quality ----
    traj = {
        "p2_histories": "per-round approvals/verdicts recorded in "
                        "P2_M2_*.r2.rows[*].history",
        "p3c_trajectories": "single-pass (extract->candidates->rank); "
                            "no multi-round trajectories",
        "prompts_logged": True,
        "outputs_verbatim": True,
        "latencies_and_tokens_logged": True,
    }

    gaps = [
        "Scale: ~10^2 generations vs the ~10^3-10^4 positive trajectories "
        "an SFT/LoRA run needs. Two orders of magnitude short.",
        "Positive density: 3 single-shot closes + 8 pipeline single-pass "
        "closes across 60 cases; the corpus is overwhelmingly negative.",
        "Diversity: 2 task families, 1 synthetic design family, 2 models. "
        "No real-design R2 cases; no second design family (also flagged in "
        "P2-M5 and the P3 plan's R2-expansion item).",
        "Held-out separation: none exists. No train/test split has been cut.",
        "Contamination screen: benchmark prompts are repo-authored and model "
        "outputs are fresh, so no external-text contamination — but no "
        "held-out gate means leakage cannot be PROVEN absent.",
        "Failure modes ARE represented (12-17 never-closing cases with full "
        "negative trajectories) — the one dimension that is genuinely "
        "adequate for failure-mode analysis, not for training.",
    ]

    decision = {
        "ready_for_sft_lora": False,
        "sufficient_path_exists": True,
        "sufficient_path": [
            "Expand R2 to >= 40 cases across >= 2 REAL design families "
            "(pre-registered in the P3 plan, not yet built).",
            "Collect positive trajectories at scale: the winning recipe on "
            "R2 (pipeline single-pass) must be run until positive turns "
            "number in the thousands, across cases, widths, and models.",
            "Cut and freeze a held-out split (cases NEVER used for training, "
            "scored only by the frozen verifiers) before any training.",
            "Deduplicate (21 prompts currently repeat across every turn) and "
            "re-balance so positives are not drowned.",
            "Re-assess against this same checklist. No training until the "
            "re-assessment passes.",
        ],
    }

    doc = {
        "track": "P3-D",
        "method": "frozen artifacts only — nothing trained, nothing "
                  "reformatted for training",
        "sources": ["P2_M2_LLAMA.json", "P2_M2_DEEPSEEK.json",
                    "P2_M5_DATASET.json", "P3_PIPELINE_LLAMA.json",
                    "P3_C_PIPELINE_VERDICT.json"],
        "size": {"r2_p2_turns": r2_turns, "t4_p2_samples": t4_s,
                 "p3c_t4_samples": pipe_t4,
                 "p3c_r2_candidate_calls": pipe_r2_prompts,
                 "total_generations": total_generations},
        "labels": labels,
        "success_failure_balance": {
            "r2_closes_total": r2_pos,
            "r2_non_closing_case_runs": r2_neg_cases,
            "t4_hits_total": (llama["t4"]["hits"] + ds["t4"]["hits"]
                              + pipe["t4"]["hits"]),
            "verdict": "overwhelmingly negative — suitable for "
                       "failure analysis, unsuitable as SFT positives",
        },
        "diversity": diversity,
        "contamination": {
            "external_text": "none — prompts repo-authored, outputs fresh",
            "held_out_split": "NONE — leakage cannot be proven absent",
        },
        "trajectory_quality": traj,
        "failure_mode_representation": {
            "never_close_single_shot": never_single,
            "never_close_pipeline": never_pipe,
            "adequate_for_failure_analysis": True,
        },
        "gaps": gaps,
        "decision": decision,
        "training_authorized": False,
        "date": "2026-10-02",
    }
    out = os.path.join(HERE, "P3_D_READINESS.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    print(f"generations={total_generations} "
          f"r2_closes={r2_pos} ready={decision['ready_for_sft_lora']} "
          f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())