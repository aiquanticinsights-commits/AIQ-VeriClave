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
        """The gate's binding list is a FROZEN snapshot of the D failures
        at gate time. Remediation may only CLEAR listed constraints: the
        current failing set must be a subset (no new failures), while the
        gate list itself never changes."""
        gate = load("P3_OVERALL_GATE.json")
        d = load("P3_D_READINESS_V2.json")
        failing_now = {k for k, g in d["grades"].items() if g == "FAIL"}
        constrained = {c["id"] for c in gate["binding_constraints"]}
        self.assertEqual(
            constrained, {"d1_scale", "d2_diversity", "d5_failure_modes",
                          "d8_heldout", "d10_economics"})
        self.assertTrue(failing_now <= constrained,
                        f"new failures appeared: {failing_now - constrained}")

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


class TestRemediationStatus(unittest.TestCase):
    def test_status_matches_live_grades(self):
        """The status record must equal the frozen gate list minus the
        currently-passing dimensions: remaining == live FAILs, cleared ==
        gate constraints already PASS."""
        gate = load("P3_OVERALL_GATE.json")
        d = load("P3_D_READINESS_V2.json")
        s = load("P3_REMEDIATION_STATUS.json")
        constrained = {c["id"] for c in gate["binding_constraints"]}
        failing_now = {k for k, g in d["grades"].items() if g == "FAIL"}
        remaining = {r.split(":")[0] for r in
                     s["remaining_binding_constraints"]}
        cleared = {c.split(":")[0] for c in
                   s["cleared_through_remeasurement"]}
        self.assertEqual(remaining, failing_now & constrained)
        self.assertEqual(cleared, constrained - failing_now)
        self.assertEqual(s["p3d_training_readiness"], d["verdict"])
        self.assertFalse(s["training_authorized"])
        self.assertIn("do not replace the original frozen benchmark",
                      s["r2b"])


if __name__ == "__main__":
    unittest.main()
