"""Constitutional policy — what is deterministic, where LLMs may act.

Evidence-First AI Principle: no AI-generated verification artifact is valid
because a model claims it valid. It becomes valid only after passing the
appropriate deterministic verification and evidence checks. The LLM may
propose evidence-producing actions; it must never manufacture the evidence.
"""
from __future__ import annotations

# Operations that MUST remain deterministic (adopted as-is). Anything here
# implemented by an LLM call is a policy violation, not an optimization.
DETERMINISTIC_OPS = frozenset({
    "syntax-validation", "compilation", "rtl-simulation",
    "reference-model-comparison", "assertion-execution", "formal-proof",
    "mutation-generation", "mutation-kill-measurement", "coverage-measurement",
    "requirement-traceability", "evidence-recording", "test-reproducibility",
    "pass-fail-thresholds", "security-privacy-rules", "artifact-hashing",
    "versioning",
})

# LLM lanes: the only jobs an LLM may take (each output still needs evidence).
LLM_LANES = {
    "A-requirement-decomposition": "split NL requirements into atomic REQ-IDs",
    "B-verification-plan": "scenarios, assertions, directed tests, corner cases, coverage objectives",
    "C-sva-generation": "propose SVA; compile + formal proof accept/reject it",
    "D-failure-explanation": "likely causes + new tests from failing sim context",
    "E-bug-localization": "ranked suspect blocks, evidence-backed",
    "F-repair-proposals": "RTL/verification diffs, through the pipeline, human-signed",
}

# Small specialized models beat the giant on narrow jobs (adopted table,
# extended with medium-coding-model tier for generation-shaped tasks).
SMALL_MODELS = {
    "requirement-classification": "small-encoder",
    "requirement-id-mapping": "small-classifier",
    "failure-classification": "small-classifier",
    "error-categorization": "small-model",
    "router": "86m-encoder",
    "bug-localization": "small-model-plus-evidence",
    "candidate-ranking": "small-reranker",
    "token-cost-routing": "deterministic",
    "sva-generation": "medium-coding-model",
    "test-generation": "medium-coding-model",
    "bug-classification": "small-model",
}

# Actions that MUST carry a human signature before taking effect.
HUMAN_SIGNOFF_ACTIONS = frozenset({
    "rtl-merge", "sign-off", "tapeout-release", "baseline-update",
    "threshold-change", "repair-merge",
})


def is_deterministic(op: str) -> bool:
    """True if the operation must be computed deterministically."""
    return op in DETERMINISTIC_OPS


def requires_human_signoff(action: str) -> bool:
    """True if the action needs a human signature (repair merges, sign-off...)."""
    return action in HUMAN_SIGNOFF_ACTIONS


def assert_no_auto_merge(action: str) -> None:
    """Guard: raise if a merge/sign-off action lacks human approval upstream."""
    if requires_human_signoff(action):
        raise PermissionError(
            f"action '{action}' requires human sign-off; autonomous merge denied")
