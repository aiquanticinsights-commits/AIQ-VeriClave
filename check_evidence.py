"""Evidence-schema check (CI gate, frozen §24): every committed evidence
JSON carries its required keys. Unknown/missing files are skipped, never
failed (dev-machine-only evidence still validates when present)."""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

SCHEMA = {
    "P0B_BASELINE.json": ("benchmark", "winner", "candidates", "signoff"),
    "P0B_V2_BASELINE.json": ("benchmark", "winner", "candidates", "signoff"),
    "P0D_REPORT.json": ("tasks", "closed", "audit_completeness", "signoff"),
    "P0D_REPORT_V1.json": ("tasks", "closed", "signoff"),
    "P0D_REPORT_V2.json": ("tasks", "closed", "audit_completeness", "signoff"),
    "P0D_SKELETON.json": ("tasks", "closed", "strategy", "signoff"),
    "P0D_T1FORMAL.json": ("tasks", "closed", "signoff"),
    "P0D_T9RERUN.json": ("tasks", "closed", "signoff"),
    "FORMAL_WB_DMA.json": ("run_id", "report", "evidence", "signoff"),
    "FORMAL_REALBLOCKS.json": ("run_id", "blocks", "signoff"),
    "SIM_FRM_WB_DMA.json": ("vectors", "rtl_hash", "signoff"),
    "SIM_FRM_LLM.json": ("model", "result", "signoff"),
    "SIM_FRM_FPR.json": ("fpr_campaign", "signoff"),
    "MUTATION_WB_DMA.json": ("total", "killed", "score", "c1_target",
                             "benchmark", "rows"),
    "REPAIR_CLOSURE.json": ("by_arm", "rows", "signoff"),
    "REPAIR_CLOSURE_V1.json": ("by_arm", "rows", "signoff"),
    "REPAIR_CLOSURE_V2.json": ("by_arm", "rows", "signoff"),
    "GATES_ABDE.json": ("gates", "checklist", "signoff"),
    "VIVADO_GATES.json": ("blocks", "checklist", "signoff"),
    "PORTABILITY.json": ("env_a", "env_b", "rows", "signoff"),
    "E2_PORTABILITY_REPORT.json": ("benchmark", "git_commit", "comparison",
                                   "overall", "signoff"),
    "SBY_SMOKE.json": ("environment", "status", "formal_result", "yosys",
                       "sby", "solver"),
    "A_IRQ_DISPOSITION.json": ("requirement_id", "formal", "alternative",
                               "disposition", "human_signoff"),
    "GATE_B_ACCEPTANCE.json": ("gate", "decision", "human_signoff",
                               "approved_evidence"),
    "mutation_gap_report.json": (),
    "mutation_dispositions.json": (),
}


def check_one(path: str, keys: tuple) -> tuple[bool, str]:
    if not os.path.isfile(path):
        return True, "absent (dev-machine evidence), skipped"
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except ValueError as exc:
        return False, f"invalid JSON: {exc}"
    if isinstance(doc, dict):
        missing = [k for k in keys if k not in doc]
        if missing:
            return False, f"missing keys: {missing}"
        return True, "ok"
    if isinstance(doc, list):
        return (True, "ok") if doc else (False, "empty list")
    return False, "not a JSON object"


def main() -> int:
    bad = 0
    for name, keys in sorted(SCHEMA.items()):
        ok, msg = check_one(os.path.join(HERE, name), keys)
        print(f"{'ok  ' if ok else 'FAIL'} {name}: {msg}", flush=True)
        bad += not ok
    print(f"evidence schema: {'PASS' if not bad else f'{bad} FAILURES'}",
          flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
