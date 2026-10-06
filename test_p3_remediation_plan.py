"""Consistency tests for the P3 Constraint Remediation Plan. The plan is
frozen before execution: every binding constraint must have coverage, every
item must be measurable, ordering must hold, training must be absent."""
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


class TestRemediationPlan(unittest.TestCase):
    def test_every_binding_constraint_covered(self):
        gate = load("P3_OVERALL_GATE.json")
        plan = load("P3_REMEDIATION_PLAN.json")
        constrained = {c["id"] for c in gate["binding_constraints"]}
        covered = {i["constraint"] for i in plan["items"]}
        self.assertEqual(covered, constrained)

    def test_every_item_measurable(self):
        plan = load("P3_REMEDIATION_PLAN.json")
        for item in plan["items"]:
            self.assertTrue(item["acceptance"], item["id"])
            self.assertTrue(item["remeasure"], item["id"])
            self.assertTrue(item["experiment"], item["id"])

    def test_heldout_first(self):
        """Scale/diversity/walls items must depend on the held-out split."""
        plan = load("P3_REMEDIATION_PLAN.json")
        by_id = {i["id"]: i for i in plan["items"]}
        self.assertEqual(by_id["R-1"]["depends_on"], [])
        for rid in ("R-2b", "R-2a", "R-3", "R-4"):
            self.assertIn("R-1", by_id[rid]["depends_on"], rid)
        # Scale last among data items: needs the expanded pool.
        self.assertIn("R-2b", by_id["R-4"]["depends_on"])
        self.assertIn("R-2a", by_id["R-4"]["depends_on"])

    def test_no_training_anywhere(self):
        plan = load("P3_REMEDIATION_PLAN.json")
        self.assertFalse(plan["training_authorized"])
        blob = json.dumps(plan).lower()
        for token in ("sft", "finetun", "lora", "trainer", "p4 authorized"):
            self.assertNotIn(token, blob, token)
        self.assertIn("no training", blob)

    def test_re_measure_rule_points_at_frozen_assessor(self):
        plan = load("P3_REMEDIATION_PLAN.json")
        self.assertIn("p3d_readiness_v2.py", plan["re_measure_rule"])
        self.assertIn("SEPARATE", plan["re_measure_rule"])


if __name__ == "__main__":
    unittest.main()
