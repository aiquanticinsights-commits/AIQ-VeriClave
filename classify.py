"""Mutation classification + Gate A acceptance (frozen V6 objective).

Score (doc §4 — frozen BEFORE any result is viewed):
    score = killed / (killed + valid surviving)
where valid surviving excludes EQUIVALENT / INVALID / INFRA_FAILURE.
EQUIVALENT enters ONLY via a human-authored dispositions map
{id: reason} — the machine never declares equivalence (survivor-analysis
rule). Gate A acceptance (§7) is a pure function of the evidence dict.
"""
from __future__ import annotations

import json

C1_TARGET = 0.95


def classify(results: dict, catalog: list[dict],
             dispositions: dict | None = None) -> dict:
    """results: {id: {status, by, ...}}. Returns the full report dict."""
    dispositions = dispositions or {}
    by_id = {m["id"]: m for m in catalog}
    rows = []
    for mid, r in results.items():
        status = r.get("status", "INFRA_FAILURE")
        if mid in dispositions and status == "SURVIVED":
            status = "EQUIVALENT"
        rows.append({"id": mid,
                     "op": r.get("op", by_id.get(mid, {}).get("op", "?")),
                     "status": status,
                     "by": r.get("by", ""),
                     "detail": r.get("detail", "")[:200],
                     "disposition": dispositions.get(mid, "")})
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    killed = counts.get("KILLED", 0)
    survived = counts.get("SURVIVED", 0)
    denom = killed + survived
    return {
        "total": len(rows),
        "killed": killed,
        "survived": survived,
        "equivalent": counts.get("EQUIVALENT", 0),
        "invalid": counts.get("INVALID", 0),
        "infra_failures": counts.get("INFRA_FAILURE", 0),
        "executable": killed + survived,
        "score": round(killed / denom, 4) if denom else 0.0,
        "c1_target": C1_TARGET,
        "c1_met": denom > 0 and killed / denom >= C1_TARGET,
        "rows": rows,
    }


def gate_a_accepts(evidence: dict) -> tuple[bool, list[str]]:
    """Gate A acceptance (§7): deterministic regression + required formals
    PROVEN + C1 + every unprovable property dispositioned + no silent drops
    + ledger complete. Returns (accept, reasons). Pure function of data."""
    reasons = []
    ok = True

    def need(cond: bool, why: str):
        nonlocal ok
        reasons.append(("PASS: " if cond else "FAIL: ") + why)
        ok = ok and cond

    need(bool(evidence.get("regression_pass")), "deterministic regression green")
    need(bool(evidence.get("formals_proven")), "required formal properties PROVEN")
    need(evidence.get("c1", 0.0) >= C1_TARGET,
         f"C1 {evidence.get('c1', 0.0)} >= {C1_TARGET}")
    gaps = evidence.get("unproven", [])
    need(all(g.get("reason") and g.get("alternative") and g.get("disposition")
             for g in gaps),
         f"{len(gaps)} unprovable properties each carry reason+alternative+disposition")
    need(evidence.get("silent_drops", 0) == 0, "zero silently-dropped gaps")
    need(evidence.get("audit_complete", 0.0) == 1.0, "ledger audit 1.0")
    return ok, reasons


def write_report(report: dict, path: str) -> str:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return path
