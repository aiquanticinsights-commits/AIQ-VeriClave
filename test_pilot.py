"""Unit tests for the assisted pilot arm (no humans simulated, by design)."""
import json
import unittest

from pilot_assist import TASKS, run_pilot, run_task


class TestPilotMechanics(unittest.TestCase):
    def test_tasks_frozen_set(self):
        self.assertEqual(sorted(TASKS), ["interrupt-controller", "round-robin-arbiter"])

    def test_report_schema(self):
        r = run_task("round-robin-arbiter")
        for k in ("family", "llm_calls", "authoring_time_s", "artifacts_generated",
                  "false_alarms", "defects_discovered", "mutants_total",
                  "diagnostics", "iterations", "closure", "rework_rounds",
                  "evidence_completeness", "ledger_ok", "accepted_artifacts",
                  "rejected_artifacts", "total_task_time_s", "review_time_s",
                  "satisfaction", "compute_cost_usd", "verdict"):
            self.assertIn(k, r, k)

    def test_no_simulated_humans(self):
        r = run_task("interrupt-controller")
        self.assertIsNone(r["review_time_s"])
        self.assertIsNone(r["satisfaction"])

    def test_verdict_logic(self):
        for fam in TASKS:
            r = run_task(fam)
            if r["verdict"] == "PASS":
                self.assertEqual(r["false_alarms"], 0)
                self.assertEqual(r["defects_discovered"], r["mutants_total"])
                self.assertEqual(r["evidence_completeness"], 1.0)

    def test_deterministic(self):
        a = run_task("round-robin-arbiter")
        b = run_task("round-robin-arbiter")
        for k in ("verdict", "defects_discovered", "false_alarms", "closure"):
            self.assertEqual(a[k], b[k])

    def test_pilot_marks_human_pending(self):
        rep = run_pilot()
        self.assertEqual(rep["arm"], "assisted")
        self.assertIn("PENDING", rep["human_arm"])
        self.assertEqual(sorted(rep["tasks"]), sorted(TASKS))


if __name__ == "__main__":
    unittest.main(verbosity=2)
