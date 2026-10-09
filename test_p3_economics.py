"""Tests for the R-5 economics memo: structure, authority, documented
rates, and the d10 grading rule (EV conclusion, not mere existence)."""
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

from p3d_readiness_v2 import grade_dimension  # noqa: E402

CHAIN = ("model", "parameters_b", "quantization", "lora_rank", "seq_len",
         "dataset_tokens", "gpu_type", "train_gpu_hours", "rate_used_usd_per_hr",
         "total_cash_usd")


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


class TestMemoStructure(unittest.TestCase):
    def test_three_scenarios_with_full_chain(self):
        m = load("P3_R5_ECONOMICS_MEMO.json")
        self.assertEqual(len(m["scenarios"]), 3)
        self.assertEqual([s["name"] for s in m["scenarios"]],
                         ["Minimum", "Expected", "Stress"])
        for s in m["scenarios"]:
            for k in CHAIN:
                self.assertIn(k, s, (s["name"], k))
            self.assertIn("band_usd", s)

    def test_rates_documented_not_invented(self):
        m = load("P3_R5_ECONOMICS_MEMO.json")
        self.assertTrue(m["reference_rates"]["rates"])
        for r in m["reference_rates"]["rates"]:
            self.assertIn("source", r)
            self.assertIn("page_date", r)
            self.assertGreater(r["usd_per_hr"], 0)

    def test_figures_marked(self):
        m = load("P3_R5_ECONOMICS_MEMO.json")
        blob = json.dumps(m)
        self.assertIn("measured", blob)
        self.assertIn("reference", blob)
        self.assertIn("assumption", blob)

    def test_authority_fields_exact(self):
        m = load("P3_R5_ECONOMICS_MEMO.json")
        self.assertEqual(m["spend_owner"], "AIQI founder / project owner")
        self.assertEqual(m["r5_spending_authority_usd"], 0)
        self.assertEqual(m["r5_analysis_spend_usd"], 0)
        self.assertEqual(m["training_spend_authorization"],
                         "NOT GRANTED by R-5")
        self.assertFalse(m["training_authorized"])
        self.assertEqual(m["future_training_budget"],
                         "TBD after R-5 and P3 decision gate")

    def test_conclusion_is_conditional(self):
        m = load("P3_R5_ECONOMICS_MEMO.json")
        self.assertEqual(m["economic_conclusion"], "JUSTIFIED_IF")
        self.assertTrue(m["economic_conclusion_gates"])


class TestD10Grading(unittest.TestCase):
    def test_justified_passes(self):
        self.assertEqual(
            grade_dimension("d10_economics",
                            {"memo_exists": True, "conclusion": "JUSTIFIED"}),
            "PASS")

    def test_conditional_fails(self):
        self.assertEqual(
            grade_dimension(
                "d10_economics",
                {"memo_exists": True, "conclusion": "JUSTIFIED_IF"}),
            "FAIL")

    def test_absent_fails(self):
        self.assertEqual(
            grade_dimension("d10_economics",
                            {"memo_exists": False, "conclusion": None}),
            "FAIL")


if __name__ == "__main__":
    unittest.main()
