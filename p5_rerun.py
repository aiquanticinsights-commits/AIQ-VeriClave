"""P5 independent re-run — second executor, clean process, frozen baseline.

Independence properties (methodological, same machine):
1. Runs in a FRESH Python subprocess (no shared imports/state with any prior run).
2. Reads ONLY frozen inputs (P5 freeze record enforced inside run_suite).
3. Compares canonical JSON (sort_keys) of families+overall against the
   committed P5_EXECUTION.json baseline (minus run-metadata keys).
4. Any mismatch (or frozen drift) is a FINDING, never averaged away.

Full E3 additionally wants a second human/machine executor; this runner makes
that a one-command operation for whoever does it next.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
BASELINE = os.path.join(BASE, "P5_EXECUTION.json")
RUN_META_KEYS = ("reproducible",)


def rerun_in_clean_process() -> dict:
    """Execute the suite in a fresh interpreter; return its parsed output."""
    prog = ("import json, sys; sys.path.insert(0, %r);"
            "from p5_execute import run_suite;"
            "print(json.dumps(run_suite(), sort_keys=True))" % BASE)
    out = subprocess.run([sys.executable, "-c", prog], capture_output=True,
                         text=True, timeout=300, cwd=BASE)
    if out.returncode != 0:
        raise RuntimeError(f"clean-process run failed: {out.stderr[-2000:]}")
    # last non-empty line is the JSON (unittest noise impossible here, but be safe)
    lines = [ln for ln in out.stdout.splitlines() if ln.strip().startswith("{")]
    return json.loads(lines[-1])


def strip_meta(d: dict) -> dict:
    return {k: v for k, v in d.items() if k not in RUN_META_KEYS}


def compare_against_baseline(fresh: dict, baseline_path: str = BASELINE) -> dict:
    """Byte-level comparison on canonical JSON. Returns the finding record."""
    with open(baseline_path, encoding="utf-8") as f:
        base = json.load(f)
    a = json.dumps(strip_meta(fresh), sort_keys=True)
    b = json.dumps(strip_meta(base), sort_keys=True)
    return {"match": a == b,
            "fresh_overall": fresh.get("overall"),
            "baseline_overall": base.get("overall"),
            "fresh_freeze_intact": fresh.get("freeze_intact"),
            "families_compared": sorted(fresh.get("families", )),
            "verdict": ("REPRODUCED" if a == b and fresh.get("freeze_intact")
                        else "FINDING-NON-REPRODUCIBLE")}


if __name__ == "__main__":
    fresh = rerun_in_clean_process()
    finding = compare_against_baseline(fresh)
    record = {"executor": "independent-clean-process",
              "baseline": "P5_EXECUTION.json (committed)",
              "fresh": {k: (v if k != "families" else
                             {f: {"verdict": vv["verdict"]} for f, vv in v.items()})
                        for k, v in fresh.items()},
              "comparison": finding}
    with open(os.path.join(BASE, "P5_RERUN.json"), "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    print(json.dumps(finding, indent=2))
