"""Human-review dashboard rollup (Gate D measurement surface).

Joins a run report (machine side: what closed, what escalated) with a
REVIEW record (human side: dispositions + timings) into the frozen §16
dashboard. Exception rate is the headline metric: the share of tasks the
machine could NOT disposition alone — the workload AIQ-VeriClave must
minimize without weakening sign-off. The dashboard never hides
uncertainty: unreviewed exceptions and missing evidence are counted loudly.
"""
from __future__ import annotations


def rollup(run: dict, review: dict | None = None) -> dict:
    """run: P0D-style report (tasks/closed/escalated_to_human/audit...).
    review: REVIEW record or None (no human run yet — fields stay None,
    never fabricated)."""
    total = run.get("tasks", 0)
    exc = run.get("escalated_to_human", 0)
    d = {
        "tasks_processed": total,
        "auto_accepted": run.get("closed", 0),
        "exceptions": exc,
        "human_review_rate": round(exc / total, 4) if total else None,
        "audit_completeness": run.get("audit_completeness"),
        "median_decision_time_s": None,
        "reject_rate": None,
        "override_rate": None,
        "evidence_opened_per_task": None,
        "missing_evidence": None,
        "reviewer": None,
    }
    if review is not None:
        items = review.get("items", [])
        done = [i for i in items if i.get("disposition") != "skip"]
        times = sorted(i.get("seconds", 0) for i in done)
        import statistics as _st
        median = _st.median(times) if times else None
        d.update({
            "median_decision_time_s": median,
            "reject_rate": round(sum(1 for i in done
                                     if i.get("disposition") == "reject")
                                 / len(done), 4) if done else None,
            "override_rate": round(sum(1 for i in done
                                       if i.get("disposition") == "override")
                                   / len(done), 4) if done else None,
            "evidence_opened_per_task": round(len(done) / total, 2)
            if total else None,
            "missing_evidence": sum(1 for i in done
                                    if not i.get("artifact_shown", True)),
            "reviewer": review.get("reviewer"),
        })
    return d


def _pct(v) -> str:
    return "?" if v is None else f"{100 * v:6.1f}%"


def _num(v, fmt="%6s") -> str:
    return "?" if v is None else (fmt % v)


def _who(v) -> str:
    s = "" if v is None else str(v)
    return "?" if not s else s[:27]


def render(d: dict) -> str:
    """ASCII dashboard. Unknown renders as '?', never as 0."""
    return "\n".join([
        "┌───────────────────────────────────────┐",
        "│       HUMAN REVIEW DASHBOARD          │",
        "├───────────────────────────────────────┤",
        f"│ Tasks processed              {d['tasks_processed']:>4}       │",
        f"│ Auto-accepted                {d['auto_accepted']:>4}       │",
        f"│ Exceptions                    {d['exceptions']:>4}       │",
        f"│ Human review rate         {_pct(d['human_review_rate'])}      │",
        f"│ Median decision time {_num(d['median_decision_time_s'], '%7.1f s')}    │",
        f"│ Reject rate               {_pct(d['reject_rate'])}      │",
        f"│ Override rate             {_pct(d['override_rate'])}      │",
        f"│ Evidence opened/task {_num(d['evidence_opened_per_task'], '%6.2f')}     │",
        f"│ Missing evidence              {_num(d['missing_evidence'], '%3d')}       │",
        f"│ Reviewer: {_who(d['reviewer']):<27} │",
        "└───────────────────────────────────────┘",
    ])
