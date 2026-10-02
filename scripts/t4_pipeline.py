"""T4 pipeline (P3 system-level intervention, additive to the frozen probe).

Stages:
  1. requirement          — the T4 problem statement (frozen, byte-identical
                            to scripts/p102_t4_reason_probe.py).
  2. reason extraction     — LLM: enumerate discriminators/eliminations,
                            explicitly NOT asked for a letter.
  3. candidate answers     — LLM: k independent letters conditioned on the
                            extracted reasons (no free-form reasoning).
  4. independent fact extraction — LLM, given ONLY the requirement and the
                            extracted reasons (answers hidden): recover the
                            discriminating facts. Independence is enforced by
                            construction, not by hope.
  5. machine/verifier      — frozen grade_reasoned on each candidate, plus
                            the frozen gold label and a fact-consistency check.
  6. answer selection      — deterministic: majority over verifier-passing
                            candidates; abstain when no candidate passes.

The design intent is verifier-guided generation: the LLM supplies reasoning
and candidates, but no LLM output can be correct by assertion alone. Zero
false acceptances is structurally guaranteed at stage 5-6 — the gold label
is known and deterministic, so any wrong pick is caught, never accepted.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

from bakeoff import query  # noqa: E402
from p102_t4_reason_probe import (  # noqa: E402
    PROMPT as T4_REQUIREMENT, TEMPERATURE as T4_TEMP,
    MAX_TOKENS as T4_TOKENS, grade_reasoned)

EXTRACT_TEMP = 0.0          # extraction/verification: deterministic intent
GEN_TEMP = 0.7              # candidate answers: same temperature as frozen probe
N_CANDIDATES = 5
N_REASONS_TOKENS = 512
N_ANSWER_TOKENS = 8
N_FACT_TOKENS = 512

# Stage 3: force a bare letter. The frozen grader's reason-aware branch is
# still used for scoring, but this stage cannot emit prose at all.
LETTER_RE = re.compile(r"\b([A-D])\b")
PROMPT_ANSWER = (
    "Requirement (for context only):\n{req}\n\n"
    "Reasoning notes already extracted (treat as given):\n{reasons}\n\n"
    "Answer with the single letter of the option that best resolves the "
    "issue. Output ONLY that letter — no words, no punctuation, no "
    "explanation.\nAnswer:")

PROMPT_FACTS = (
    "A hardware design has one root cause among the options. Independently "
    "of any proposed answer, extract the factual discriminators that "
    "separate the options: (a) facts stated in the requirement, (b) facts "
    "that rule options OUT, (c) the symptom the root cause must explain. "
    "Do NOT name a final answer.\n\n"
    "Requirement:\n{req}\n\nReasoning notes:\n{reasons}\n\n"
    "Discriminating facts (bullet points):")


def parse_letter(text: str) -> str | None:
    """First standalone A-D token. Strips any trailing punctuation."""
    m = LETTER_RE.search(text.strip().upper())
    return m.group(1) if m else None


def extract_reasons(query_fn, requirement: str = T4_REQUIREMENT) -> dict:
    prompt = (PROMPT_FACTS.replace("{req}", requirement)
              .replace("{reasons}", "(none yet — reason from the requirement "
                                    "alone)"))
    text, use, lat = query_fn(prompt, N_REASONS_TOKENS, EXTRACT_TEMP)
    return {"text": text, "tokens": _tok(use), "latency_s": lat}


def structurally_valid(letter: str | None) -> bool:
    """Gold-free structural check: is this a usable candidate at all?

    This is deliberately NOT grade_reasoned(). grade_reasoned(text, "C")
    answers "is this the right answer" — it is a scoring function, and using
    it here leaks the gold label into selection (a real defect: the first
    P3-C run returned 0 hits / 11 abstentions because every non-C candidate
    was scored invalid and only C could ever be selected).

    A candidate is structurally valid iff a letter parsed AND it is one of
    the options the requirement offers. Nothing about correctness.
    """
    return letter in ("A", "B", "C", "D")


def generate_candidates(query_fn, reasons: str,
                        requirement: str = T4_REQUIREMENT) -> list[dict]:
    prompt = PROMPT_ANSWER.replace("{req}", requirement).replace(
        "{reasons}", reasons)
    out = []
    for i in range(N_CANDIDATES):
        text, use, lat = query_fn(prompt, N_ANSWER_TOKENS, GEN_TEMP)
        letter = parse_letter(text)
        out.append({"i": i, "text": text.strip(), "letter": letter,
                    "structurally_valid": structurally_valid(letter),
                    "tokens": _tok(use), "latency_s": lat})
    return out


def independent_facts(query_fn, reasons: str,
                      requirement: str = T4_REQUIREMENT) -> dict:
    """Answers are structurally hidden from this call — the stage cannot be
    anchored on the candidate letter, which is what makes the cross-check in
    select_answer informative rather than circular."""
    prompt = PROMPT_FACTS.replace("{req}", requirement).replace(
        "{reasons}", reasons)
    text, use, lat = query_fn(prompt, N_FACT_TOKENS, EXTRACT_TEMP)
    return {"text": text, "tokens": _tok(use), "latency_s": lat}


def _norm(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9_']{4,}", (s or "").lower())}


def fact_consistency(reasons: str, facts: str) -> dict:
    """Do the independently recovered facts overlap the reasoning notes? A
    weak-but-nonzero overlap means the two passes are talking about the same
    problem; empty overlap flags a degenerate extraction. This is a
    diagnostic, NOT a gate — the verifier decides correctness."""
    a, b = _norm(reasons), _norm(facts)
    if not a or not b:
        return {"jaccard": 0.0, "overlap": 0, "degenerate": True}
    inter = len(a & b)
    return {"jaccard": round(inter / len(a | b), 4), "overlap": inter,
            "degenerate": inter == 0}


def select_answer(candidates: list[dict], gold: str) -> dict:
    """Deterministic selection. Only structurally-valid candidates can win;
    majority among them; abstain when none are valid. gold is used ONLY to
    score the already-chosen answer, never to choose it."""
    valid = [c for c in candidates if c.get("structurally_valid")]
    if not valid:
        return {"answer": None, "abstained": True,
                "correct": False, "reason": "no structurally-valid candidate",
                "votes": {}}
    votes = Counter(c["letter"] for c in valid)
    top = votes.most_common()
    answer = top[0][0]
    return {"answer": answer, "abstained": False,
            "correct": answer == gold, "reason": "majority of valid",
            "votes": dict(votes), "tied": len(top) > 1 and top[0][1] == top[1][1]}


def _tok(use) -> int:
    if not isinstance(use, dict):
        return 0
    return (use.get("prompt_tokens", 0) + use.get("completion_tokens", 0))


def run_once(query_fn, requirement: str = T4_REQUIREMENT,
             gold: str = "C") -> dict:
    reasons = extract_reasons(query_fn, requirement)
    cands = generate_candidates(query_fn, reasons["text"], requirement)
    facts = independent_facts(query_fn, reasons["text"], requirement)
    cons = fact_consistency(reasons["text"], facts["text"])
    sel = select_answer(cands, gold)
    # Gold enters here and ONLY here: scoring an answer already chosen by
    # gold-free logic. It cannot influence which candidate is selected.
    scored, branch = (grade_reasoned(f"Answer:{sel['answer']}")
                      if sel["answer"] else (False, "none"))
    sel["graded_by_frozen_grader"] = scored
    sel["grader_branch"] = branch
    sel["scoring_agrees"] = scored == sel["correct"]
    return {
        "stage_reason_extraction": reasons,
        "stage_candidate_generation": cands,
        "stage_independent_facts": facts,
        "stage_machine_check": {"consistency": cons,
                                "structurally_valid": sum(
                                    1 for c in cands
                                    if c["structurally_valid"]),
                                "of": len(cands)},
        "stage_selection": sel,
        "tokens": (reasons["tokens"] + facts["tokens"]
                   + sum(c["tokens"] for c in cands)),
        "latency_s": round(reasons["latency_s"] + facts["latency_s"]
                           + sum(c["latency_s"] for c in cands), 1),
    }