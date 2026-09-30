"""Exception-review dashboard (frozen item 3, Gate D).

The frozen architecture demands measured human efficiency — review time,
rejection/override rates — not asserted scalability. This CLI is the
instrument: it walks a run report exception-first (escalations and weak
closes before clean closes), times every disposition, and writes a
REVIEW_<run_id>.json record. `--exceptions-only` measures the
exception-only workflow the architecture prescribes (engineers review
unresolved failures + sign-off, not every artifact).

Dispositions: accept (agree with machine verdict) / reject (send back —
requires a reason, feeds closure) / override (human disagrees with a PASS;
requires a reason) / skip (no time; recorded as unreviewed, never as accept).

Only interactive use produces measurements; unit tests inject input_fn/clock.
"""
from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
VALID = ("a", "r", "o", "s")
NAMES = {"a": "accept", "r": "reject", "o": "override", "s": "skip"}


def order_review(tasks: list[dict], exceptions_only: bool = False) -> list[dict]:
    """Escalations first, then weak closes (approvals < 2), then clean.
    exceptions_only=True drops clean closes entirely (exception workflow)."""
    def rank(t: dict) -> int:
        if t.get("escalated_to_human"):
            return 0
        if t.get("approvals", 0) < 2:
            return 1
        return 2

    ordered = sorted(tasks, key=rank)
    if exceptions_only:
        ordered = [t for t in ordered if rank(t) < 2]
    return ordered


def describe(task: dict) -> str:
    lines = [f"--- {task.get('task')} [{task.get('kind')}] "
             f"rounds={task.get('rounds')} approvals={task.get('approvals')} "
             f"escalated={task.get('escalated_to_human')}"]
    art = (task.get("artifact") or "")[:300]
    if art:
        lines.append(f"    artifact: {art}")
    hist = task.get("history", [])
    if hist:
        lines.append("    rounds: " + ", ".join(
            f"r{h.get('round')}:{h.get('approvals')}" for h in hist))
    return "\n".join(lines)


def run_review(tasks: list[dict], input_fn=None,
               clock=time.perf_counter) -> dict:
    """Interactive review. Returns the dispositions record (times measured).
    input_fn defaults to console input (resolved lazily so tests can patch
    builtins.input)."""
    if input_fn is None:
        input_fn = input
    items = []
    for t in tasks:
        print(describe(t), flush=True)
        start = clock()
        while True:
            ans = input_fn("disposition [a]ccept [r]eject [o]verride "
                           "[s]kip: ").strip().lower()
            if ans in VALID:
                break
            print("  enter a, r, o, or s", flush=True)
        reason = ""
        if ans in ("r", "o"):
            reason = input_fn("reason (required): ").strip()
            while not reason:
                reason = input_fn("reason (required): ").strip()
        dt = clock() - start
        items.append({"task": t.get("task"), "machine": "escalated"
                      if t.get("escalated_to_human") else "closed",
                      "disposition": NAMES[ans], "reason": reason,
                      "seconds": round(dt, 1),
                      "artifact_shown": bool((t.get("artifact") or "").strip())})
        print(f"  recorded {NAMES[ans]} in {dt:.1f}s", flush=True)
    return {"items": items}


def summarize(items: list[dict]) -> dict:
    done = [i for i in items if i["disposition"] != "skip"]
    n = len(items)
    total = sum(i["seconds"] for i in done)
    return {
        "tasks_presented": n,
        "tasks_dispositioned": len(done),
        "evidence_items_reviewed": len(done),
        "engineer_review_time_s": round(total, 1),
        "engineer_review_time_per_task_s": round(total / len(done), 1)
        if done else None,
        "human_rejection_rate": round(
            sum(1 for i in done if i["disposition"] == "reject") / len(done), 4)
        if done else None,
        "human_override_rate": round(
            sum(1 for i in done if i["disposition"] == "override") / len(done),
            4) if done else None,
        "unreviewed": n - len(done),
    }


def load_tasks(report_path: str) -> tuple[list[dict], dict]:
    with open(report_path, encoding="utf-8") as f:
        rep = json.load(f)
    partial_path = os.path.join(HERE, "P0D_PARTIAL.json")
    hist: dict[str, list] = {}
    try:
        with open(partial_path, encoding="utf-8") as f:
            part = json.load(f)
        for tid, r in part.get("results", {}).items():
            hist[tid] = r.get("history", [])
    except (OSError, ValueError):
        pass
    tasks = []
    for t in rep.get("tasks_detail", []):
        t = dict(t)
        t.setdefault("history", hist.get(t.get("task", ""), []))
        tasks.append(t)
    return tasks, rep


def main() -> int:
    args = sys.argv[1:]
    if not args or "--help" in args:
        print("usage: review.py REPORT.json [--exceptions-only] "
              "[--reviewer NAME] [--resume REVIEW.json]", flush=True)
        return 2
    resume_path = ""
    for i, a in enumerate(args):
        if a == "--resume" and i + 1 < len(args):
            resume_path = args[i + 1]
    positional = [a for n, a in enumerate(args)
                  if a.endswith(".json") and a != resume_path
                  and not (n > 0 and args[n - 1] == "--resume")]
    report_path = positional[0] if positional else ""
    if not report_path:
        print("FATAL: provide REPORT.json", flush=True)
        return 2
    exceptions_only = "--exceptions-only" in args
    reviewer = ""
    for i, a in enumerate(args):
        if a == "--reviewer" and i + 1 < len(args):
            reviewer = args[i + 1]
    if not reviewer:
        reviewer = input("reviewer name (required): ").strip()
        while not reviewer:
            reviewer = input("reviewer name (required): ").strip()
    tasks, rep = load_tasks(report_path)
    ordered = order_review(tasks, exceptions_only)
    prior_items: dict[str, dict] = {}
    if resume_path:
        try:
            with open(resume_path, encoding="utf-8") as f:
                prior = json.load(f)
            if prior.get("run_id") and prior.get("run_id") != rep.get("run_id"):
                print(f"WARNING: resume record is for run "
                      f"{prior.get('run_id')}, report is "
                      f"{rep.get('run_id')} — continuing anyway, tasks "
                      f"matched by id", flush=True)
            for it in prior.get("items", []):
                if it.get("disposition") != "skip":
                    prior_items[it.get("task", "")] = it
            if prior.get("reviewer") and not any(
                    a == "--reviewer" for a in args):
                reviewer = prior["reviewer"]
        except (OSError, ValueError) as exc:
            print(f"FATAL: cannot read resume file: {exc}", flush=True)
            return 2
    fresh = [t for t in ordered if t.get("task") not in prior_items]
    print(f"{len(ordered)} items ({len(tasks)} total, "
          f"exceptions_only={exceptions_only}, "
          f"resumed={len(prior_items)})", flush=True)
    fresh_items = run_review(fresh)["items"]
    merged = {it["task"]: it for it in fresh_items}
    merged.update(prior_items)  # prior dispositions preserved verbatim
    record = {"items": [merged[t["task"]] for t in ordered
                        if t["task"] in merged]}
    record.update(summarize(record["items"]))
    record.update({"reviewer": reviewer, "run_id": rep.get("run_id", ""),
                   "report": os.path.basename(report_path),
                   "exceptions_only": exceptions_only,
                   "signoff": "PENDING"})
    out = os.path.join(HERE, f"REVIEW_{record['run_id'] or 'manual'}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    print(f"review_time_per_task={record['engineer_review_time_per_task_s']}s "
          f"reject={record['human_rejection_rate']} "
          f"override={record['human_override_rate']} -> {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
