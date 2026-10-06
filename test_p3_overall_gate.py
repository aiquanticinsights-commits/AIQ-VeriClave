"""Consistency tests for the P3 Overall Decision Gate. The gate is a
readout, not a new measurement: every claim in it must match the frozen
track verdicts, and training must be authorized nowhere."""
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


class TestOverallGate(unittest.TestCase):
    def test_track_table_matches_verdicts(self):
        gate = load("P3_OVERALL_GATE.json")
        a = load("P3_A_VERDICT.json")
        b = load("P3_B_ENSEMBLE_VERDICT.json")
        c = load("P3_C_QWEN_VERDICT.json")
        d = load("P3_D_READINESS_V2.json")
        self.assertIn("PARTIAL", a["m3_overall"]["verdict"])
        self.assertIn("FAIL", b["overall_verdict"])
        self.assertEqual(b["closure"]["status"], "CLOSED / FAIL")
        self.assertTrue(c["overall_verdict"].startswith("PASS"))
        self.assertIn("human_approval", c)
        self.assertEqual(d["verdict"], "NOT READY")
        self.assertEqual(d["closure"]["status"], "CLOSED / NOT READY")
        self.assertEqual(gate["tracks"]["P3-A"]["result"], "FAIL / PARTIAL")
        self.assertIn("FAIL", gate["tracks"]["P3-B"]["result"])
        self.assertIn("PASS", gate["tracks"]["P3-C"]["result"])
        self.assertIn("NOT READY", gate["tracks"]["P3-D"]["result"])

    def test_binding_constraints_are_exactly_the_d_failures(self):
        gate = load("P3_OVERALL_GATE.json")
        d = load("P3_D_READINESS_V2.json")
        failing = sorted(k for k, g in d["grades"].items() if g == "FAIL")
        constrained = sorted(c["id"] for c in gate["binding_constraints"])
        self.assertEqual(constrained, failing)
        self.assertEqual(len(constrained), 5)

    def test_training_authorized_nowhere(self):
        gate = load("P3_OVERALL_GATE.json")
        d = load("P3_D_READINESS_V2.json")
        self.assertFalse(gate["training_authorized"])
        self.assertFalse(d["training_authorized"])
        self.assertFalse(d["closure"]["training_authorization"].startswith(
            "AUTHORIZED"))
        blob = json.dumps(gate).lower()
        self.assertNotIn("qwen solved verification", blob)
        self.assertIn("TRAINING NOT AUTHORIZED", blob.upper())

    def test_status_string(self):
        gate = load("P3_OVERALL_GATE.json")
        self.assertEqual(
            gate["status"],
            "P3 = CLOSED → SYSTEM DIRECTION VALIDATED / TRAINING NOT AUTHORIZED")


if __name__ == "__main__":
    unittest.main()
