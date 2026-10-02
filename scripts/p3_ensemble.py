"""P3-B: ensemble / complementary-model analysis.

No new model runs. The frozen P2 artifacts already record, per sample/case,
what each model produced, so the ensemble ceiling can be derived from frozen
evidence alone:

  T4  — N=20 independent samples of ONE question per model. For each sample
        index i we know both models' graded pick, so consensus and
        disagreement are measurable. Two models cannot form a majority, so
        the honest quantities are: consensus-correct rate, consensus-wrong
        rate, and disagreement rate (where an ensemble has to break a tie).
  R2  — 20 cases per model with per-case closure. The union of closed cases
        is the ensemble ceiling (oracle selection). The intersection is what
        both models agree on. Per-case disagreement is the exploitable
        complementarity.

Both derive ONLY from P2_M2_LLAMA.json / P2_M2_DEEPSEEK.json. This is an
upper bound: it assumes a perfect selector. A real selector can only do
worse, so the ceiling bounds the track.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def t4_analysis(llama: dict, deepseek: dict) -> dict:
    L = {s["i"]: s for s in llama["t4"]["samples"]}
    D = {s["i"]: s for s in deepseek["t4"]["samples"]}
    shared = sorted(set(L) & set(D))
    both_c = sum(1 for i in shared
                 if L[i]["ok"] and D[i]["ok"])
    both_wrong = sum(1 for i in shared
                     if not L[i]["ok"] and not D[i]["ok"])
    disagree = sum(1 for i in shared
                   if L[i]["ok"] != D[i]["ok"])
    n = len(shared)
    return {"n_paired": n,
            "both_correct": both_c,
            "both_wrong": both_wrong,
            "disagree": disagree,
            "consensus_correct_rate": round(both_c / n, 4) if n else None,
            "consensus_wrong_rate": round(both_wrong / n, 4) if n else None,
            "disagreement_rate": round(disagree / n, 4) if n else None,
            "note": "Two models cannot form a majority. Consensus-correct is "
                    "the ensemble's guaranteed floor; disagreement rate is "
                    "the fraction needing a tiebreak, where an 8B tiebreak "
                    "must beat the stronger single model to add value."}


def r2_analysis(llama: dict, deepseek: dict) -> dict:
    L = llama["r2"]["rows"]
    D = deepseek["r2"]["rows"]
    cases = sorted(set(L) & set(D))
    l_closed = {c for c in cases if L[c]["closed"]}
    d_closed = {c for c in cases if D[c]["closed"]}
    union = l_closed | d_closed
    inter = l_closed & d_closed
    return {"n_cases": len(cases),
            "llama_closed": len(l_closed),
            "deepseek_closed": len(d_closed),
            "union_closed_oracle_ceiling": len(union),
            "both_closed": len(inter),
            "only_llama": sorted(l_closed - d_closed),
            "only_deepseek": sorted(d_closed - l_closed),
            "neither": sorted(set(cases) - union),
            "complementary": bool(d_closed - l_closed) and
                             bool(l_closed - d_closed) or
                             bool(d_closed - l_closed),
            "note": "union_closed_oracle_ceiling assumes a perfect per-case "
                    "selector. A verifier-guided selector can reach it only "
                    "if it can identify WHICH model is right per case — that "
                    "is the whole difficulty of this track."}


def main() -> int:
    with open(os.path.join(HERE, "P2_M2_LLAMA.json"), encoding="utf-8") as f:
        llama = json.load(f)
    with open(os.path.join(HERE, "P2_M2_DEEPSEEK.json"), encoding="utf-8") as f:
        deepseek = json.load(f)
    doc = {"track": "P3-B", "method": "frozen P2 artifacts only — no new "
           "model runs",
           "sources": ["P2_M2_LLAMA.json", "P2_M2_DEEPSEEK.json"],
           "t4": t4_analysis(llama, deepseek),
           "r2": r2_analysis(llama, deepseek),
           "date": "2026-10-02"}
    out = os.path.join(HERE, "P3_B_ENSEMBLE.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    print(json.dumps({k: doc[k] for k in ("t4", "r2")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())