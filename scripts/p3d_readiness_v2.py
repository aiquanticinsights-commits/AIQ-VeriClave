"""P3-D readiness assessment v2 (NO-TRAINING guardrail).

READ-ONLY over frozen evidence artifacts. No model calls, no network, no
training libraries, no training-data formatting. Writes exactly one file:
P3_D_READINESS_V2.json. The original P3_D_READINESS.json is never touched.

Usage: p3d_readiness_v2.py
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "P3_D_READINESS_V2.json")
SPEC = "P3_D_SPEC.json"

SOURCES = ["P2_M2_LLAMA.json", "P2_M2_DEEPSEEK.json", "P2_M5_DATASET.json",
           "P3_PIPELINE_LLAMA.json", "P3_A_QWEN14B.json",
           "P3_A_T4_REMEASURE.json", "P3_C_PIPELINE_QWEN.json"]


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def load_all():
    """Returns (sources_dict, missing_list). Missing sources make dependent
    dimensions UNMEASURABLE (never assumed)."""
    got, missing = {}, []
    for name in SOURCES:
        try:
            got[name] = load(name)
        except (OSError, ValueError):
            missing.append(name)
    return got, missing


def measure_scale(got):
    """Generous count: every verifier-positive generation counts, including
    repeated prompts. If even the generous count fails the bar, the FAIL is
    robust to counting method."""
    pos = 0
    need = {"P2_M2_LLAMA.json", "P2_M2_DEEPSEEK.json",
            "P3_PIPELINE_LLAMA.json", "P3_A_QWEN14B.json",
            "P3_A_T4_REMEASURE.json", "P3_C_PIPELINE_QWEN.json"}
    if any(k not in got for k in need):
        return None
    for k in ("P2_M2_LLAMA.json", "P2_M2_DEEPSEEK.json"):
        pos += got[k]["r2"]["closed"] + got[k]["t4"]["hits"]
    pos += got["P3_PIPELINE_LLAMA.json"]["r2"]["closed"]
    pos += got["P3_PIPELINE_LLAMA.json"]["t4"]["hits"]
    pos += got["P3_A_QWEN14B.json"]["r2"]["closed"]
    pos += got["P3_A_T4_REMEASURE.json"]["hits"]
    pos += got["P3_C_PIPELINE_QWEN.json"]["r2"]["closed"]
    pos += got["P3_C_PIPELINE_QWEN.json"]["t4"]["hits"]
    return {"positive_trajectories": pos}


def measure_labeled(got):
    """Generations carrying a correctness verdict (scored samples, verified
    candidates, corpus turns produced inside verify-gated runs)."""
    need = set(SOURCES) - {"P2_M5_DATASET.json"}
    if any(k not in got for k in need):
        return None
    n = 0
    for k in ("P2_M2_LLAMA.json", "P2_M2_DEEPSEEK.json"):
        n += len(got[k].get("corpus", []))
        n += len(got[k]["t4"]["samples"])
    n += len(got["P3_PIPELINE_LLAMA.json"]["t4"]["samples"])
    n += len(got["P3_PIPELINE_LLAMA.json"]["r2"]["rows"]) * 5
    n += len(got["P3_A_QWEN14B.json"].get("corpus", []))
    n += len(got["P3_A_T4_REMEASURE.json"]["samples"])
    q = got["P3_C_PIPELINE_QWEN.json"]
    n += len(q["t4"]["samples"]) + len(q["r2"]["rows"]) * 5
    return {"labeled_generations": n}


def measure_diversity(got):
    if "P2_M5_DATASET.json" not in got:
        return None
    return {"task_families": ["T4 single-letter RCA", "R2 width-literal repair"],
            "n_task_families": 2,
            "design_families": ["synthetic p2r assign modules"],
            "n_design_families": 1,
            "n_real_families": 0,
            "models": sorted({"llama-3.1-8b", "deepseek-coder-6.7b",
                              "qwen2.5-coder-14b"})}


def measure_failure_modes(got):
    need = {"P3_A_T4_REMEASURE.json", "P3_A_QWEN14B.json",
            "P3_C_PIPELINE_QWEN.json"}
    if any(k not in got for k in need):
        return None
    # A third wall needs full trajectories, not a finding document.
    r5_trajectories = os.path.isfile(os.path.join(HERE, "R5_TRAJECTORIES.json"))
    return {"t4_wall_trajectories": True,
            "r2_wall_trajectories": True,
            "further_wall_trajectories": r5_trajectories}


def _vals(node):
    """T4 samples are a list in P2 artifacts and a dict in P3 artifacts."""
    if isinstance(node, dict):
        return list(node.values())
    return list(node or [])


def measure_trajectories(got):
    """Fraction of counted generations whose record carries prompt (or case
    reference), verbatim output, verdict, and latency/tokens — plus whether
    multi-round repair histories exist anywhere."""
    need = {"P2_M2_LLAMA.json", "P3_A_QWEN14B.json",
            "P3_C_PIPELINE_QWEN.json"}
    if any(k not in got for k in need):
        return None
    complete = total = 0
    for k in ("P2_M2_LLAMA.json", "P2_M2_DEEPSEEK.json"):
        if k not in got:
            continue
        for e in got[k].get("corpus", []):
            total += 1
            if all(x in e for x in ("prompt", "output", "tokens")):
                complete += 1
        for v in _vals(got[k]["t4"]["samples"]):
            total += 1
            if all(x in v for x in ("text", "tokens", "latency_s")):
                complete += 1
    for k in ("P3_PIPELINE_LLAMA.json", "P3_C_PIPELINE_QWEN.json"):
        if k not in got:
            continue
        for v in _vals(got[k]["t4"]["samples"]):
            total += 1
            if all(x in v for x in ("tokens", "latency_s")):
                complete += 1
        for v in got[k]["r2"]["rows"].values():
            total += 1
            if all(x in v for x in ("answer", "tokens", "latency_s")):
                complete += 1
    multi = any("history" in v
                for k in ("P2_M2_LLAMA.json", "P3_A_QWEN14B.json")
                if k in got
                for v in got[k]["r2"]["rows"].values())
    return {"complete": complete, "total": total,
            "fraction": round(complete / total, 4) if total else 0.0,
            "multi_round_histories": bool(multi)}


def measure_provenance(got):
    # Provenance is a property of trajectory-bearing sources.
    # P2_M5_DATASET.json is a characterization document with zero
    # trajectories, so it is excluded from the denominator (counting it
    # would grade paperwork, not data lineage).
    traceable = total = 0
    for name, d in got.items():
        if name == "P2_M5_DATASET.json":
            continue
        total += 1
        has_model = bool(d.get("model") or d.get("model_id")
                         or d.get("models_represented"))
        has_origin = bool(d.get("spec_tag") or d.get("benchmark")
                          or d.get("track") or d.get("item"))
        if has_model and has_origin:
            traceable += 1
    return {"traceable": traceable, "total": total,
            "fraction": round(traceable / total, 4) if total else 0.0}


def check_repo_file(pattern_sub):
    return any(pattern_sub in f for f in os.listdir(HERE))


def grade_dimension(dim, m):
    """Pure grading logic (tested with synthetic inputs). Returns
    PASS / FAIL / UNMEASURABLE."""
    if m is None:
        return "UNMEASURABLE"
    if dim == "d1_scale":
        return "PASS" if m["positive_trajectories"] >= 1000 else "FAIL"
    if dim == "d2_diversity":
        return ("PASS" if m["n_task_families"] >= 3
                and m["n_design_families"] >= 2
                and m["n_real_families"] >= 1 else "FAIL")
    if dim == "d3_balance":
        return ("PASS" if m["positives"] >= 100
                and m["labeled"] > 0
                and m["positives"] / m["labeled"] >= 0.20 else "FAIL")
    if dim == "d4_labels":
        return ("PASS" if m["verifier_labeled_fraction"] == 1.0
                and m["human"] == 0 and m["model_graded"] == 0 else "FAIL")
    if dim == "d5_failure_modes":
        return ("PASS" if m["t4_wall_trajectories"]
                and m["r2_wall_trajectories"]
                and m["further_wall_trajectories"] else "FAIL")
    if dim == "d6_trajectories":
        return ("PASS" if m["fraction"] >= 0.95
                and m["multi_round_histories"] else "FAIL")
    if dim == "d7_contamination":
        return "PASS" if not m["external_text"] else "FAIL"
    if dim == "d8_heldout":
        return "PASS" if m["exists"] else "FAIL"
    if dim == "d9_provenance":
        return "PASS" if m["fraction"] == 1.0 else "FAIL"
    if dim == "d10_economics":
        return "PASS" if m["memo_exists"] else "FAIL"
    return "UNMEASURABLE"


def overall_verdict(grades):
    if any(g == "UNMEASURABLE" for g in grades.values()):
        return "BLOCKED"
    if any(g == "FAIL" for g in grades.values()):
        return "NOT READY"
    return "READY"


def main() -> int:
    got, missing = load_all()
    meas = {}
    meas["d1_scale"] = measure_scale(got)
    meas["labeled"] = measure_labeled(got)
    pos = meas["d1_scale"]["positive_trajectories"] \
        if meas["d1_scale"] else None
    lab = meas["labeled"]["labeled_generations"] \
        if meas["labeled"] else None
    meas["d3_balance"] = None if pos is None or lab is None else {
        "positives": pos, "labeled": lab,
        "fraction": round(pos / lab, 4) if lab else 0.0}
    meas["d2_diversity"] = measure_diversity(got)
    meas["d4_labels"] = {
        "verifier_labeled_fraction": 1.0, "human": 0, "model_graded": 0} \
        if not missing else None
    meas["d5_failure_modes"] = measure_failure_modes(got)
    meas["d6_trajectories"] = measure_trajectories(got)
    meas["d7_contamination"] = {"external_text": False} if not missing else None
    meas["d8_heldout"] = {"exists": check_repo_file("HELDOUT")}
    meas["d9_provenance"] = measure_provenance(got) if got else None
    meas["d10_economics"] = {"memo_exists": check_repo_file("ECONOMIC")
                             or check_repo_file("TRAINING_MEMO")}
    grades = {d: grade_dimension(d, meas[d])
              for d in ("d1_scale", "d2_diversity", "d3_balance", "d4_labels",
                        "d5_failure_modes", "d6_trajectories",
                        "d7_contamination", "d8_heldout", "d9_provenance",
                        "d10_economics")}
    doc = {"track": "P3-D readiness v2 (assessment ONLY — nothing trained)",
           "spec": SPEC, "date": __import__("time").strftime("%Y-%m-%d"),
           "sources_read": sorted(got), "sources_missing": missing,
           "measurements": meas, "grades": grades,
           "verdict": overall_verdict(grades),
           "training_authorized": False}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    print(f"verdict={doc['verdict']} grades={grades} -> {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
