"""Tests for the P3 final decision gate: every number in it recomputed
from frozen evidence; training authorized nowhere; status exact."""
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


class TestFinalGate(unittest.TestCase):
    def test_r4_facts_recomputed(self):
        cyc = load("R4_CYCLE_1.json")
        gate = load("P3_FINAL_DECISION_GATE.json")
        self.assertEqual(len(cyc["rows"]), 22)
        self.assertEqual(cyc["closed"], 19)
        self.assertEqual(cyc["false_acceptances"], 0)
        self.assertIn("19/22", json.dumps(gate))

    def test_d1_numbers_recomputed(self):
        from p3d_readiness_v2 import measure_scale
        got = {}
        for n in ["P2_M2_LLAMA.json", "P2_M2_DEEPSEEK.json",
                  "P3_PIPELINE_LLAMA.json", "P3_A_QWEN14B.json",
                  "P3_A_T4_REMEASURE.json", "P3_C_PIPELINE_QWEN.json"]:
            got[n] = load(n)
        m = measure_scale(got)
        v2 = load("P3_D_READINESS_V2.json")
        # Live recomputation must equal the committed assessment.
        self.assertEqual(m["positive_trajectories"],
                         v2["measurements"]["d1_scale"]["positive_trajectories"])
        # Grade follows the frozen rule (FAIL below 1000), whatever the count.
        expect = "PASS" if m["positive_trajectories"] >= 1000 else "FAIL"
        self.assertEqual(v2["grades"]["d1_scale"], expect)
        gate = load("P3_FINAL_DECISION_GATE.json")
        self.assertIn("183", json.dumps(gate))
        self.assertIn("817", json.dumps(gate))

    def test_remaining_are_live_failures(self):
        v2 = load("P3_D_READINESS_V2.json")
        gate = load("P3_FINAL_DECISION_GATE.json")
        failing = {k for k, g in v2["grades"].items() if g == "FAIL"}
        self.assertEqual(failing, {"d1_scale", "d10_economics"})
        self.assertIn("d1_scale", json.dumps(gate["remaining_constraints"]))
        self.assertIn("d10_economics",
                      json.dumps(gate["remaining_constraints"]))

    def test_decision_and_no_training(self):
        gate = load("P3_FINAL_DECISION_GATE.json")
        self.assertEqual(
            gate["decision"],
            "P3 = CLOSED → SYSTEM DIRECTION VALIDATED / TRAINING NOT AUTHORIZED")
        self.assertFalse(gate["training_authorized"])
        self.assertIn("never here", gate["next"].lower())
        self.assertIn("P4", gate["next"])

    def test_lineage_intact(self):
        gate = load("P3_FINAL_DECISION_GATE.json")
        self.assertIn("untouched", gate["lineage"])
        for t in ("P3-A", "P3-B", "P3-C", "P3-D"):
            self.assertIn(t, gate["tracks"])
        self.assertEqual(len(gate["remediation_completed"]), 5)


if __name__ == "__main__":
    unittest.main()
