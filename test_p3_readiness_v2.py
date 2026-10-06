"""Hermetic tests for the P3-D v2 readiness assessor. No artifacts, no
models, no training: grading logic is tested on synthetic inputs, and the
NO-TRAINING guardrail is tested against the assessor's own source."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

from p3d_readiness_v2 import grade_dimension, overall_verdict  # noqa: E402

SRC = os.path.join(HERE, "scripts", "p3d_readiness_v2.py")


class TestGradingLogic(unittest.TestCase):
    def test_scale_threshold(self):
        self.assertEqual(
            grade_dimension("d1_scale", {"positive_trajectories": 1000}),
            "PASS")
        self.assertEqual(
            grade_dimension("d1_scale", {"positive_trajectories": 999}),
            "FAIL")
        self.assertEqual(grade_dimension("d1_scale", None), "UNMEASURABLE")

    def test_balance_needs_count_and_fraction(self):
        self.assertEqual(
            grade_dimension("d3_balance", {"positives": 100, "labeled": 500,
                                           "fraction": 0.2}), "PASS")
        self.assertEqual(
            grade_dimension("d3_balance", {"positives": 200, "labeled": 2000,
                                           "fraction": 0.1}), "FAIL")
        self.assertEqual(
            grade_dimension("d3_balance", {"positives": 50, "labeled": 100,
                                           "fraction": 0.5}), "FAIL")

    def test_diversity_needs_real_family(self):
        m = {"n_task_families": 3, "n_design_families": 2,
             "n_real_families": 0}
        self.assertEqual(grade_dimension("d2_diversity", m), "FAIL")
        m["n_real_families"] = 1
        self.assertEqual(grade_dimension("d2_diversity", m), "PASS")

    def test_overall_precedence(self):
        all_pass = {f"d{i}": "PASS" for i in range(1, 11)}
        self.assertEqual(overall_verdict(all_pass), "READY")
        g = dict(all_pass)
        g["d8_heldout"] = "FAIL"
        self.assertEqual(overall_verdict(g), "NOT READY")
        # Unmeasurable dominates: missing evidence blocks, never passes.
        g["d8_heldout"] = "UNMEASURABLE"
        self.assertEqual(overall_verdict(g), "BLOCKED")

    def test_dataset_exists_is_not_sufficient(self):
        """Volume alone (all other dims failing) must be NOT READY."""
        g = {f"d{i}": "FAIL" for i in range(1, 11)}
        g["d1_scale"] = "PASS"
        self.assertEqual(overall_verdict(g), "NOT READY")


class TestNoTrainingGuardrail(unittest.TestCase):
    """The assessor must be incapable of training: no training libraries,
    no training-data outputs, exactly one assessment file written."""

    def test_no_training_imports_or_calls(self):
        with open(SRC, encoding="utf-8") as f:
            src = f.read().lower()
        for token in ("torch", "transformers", "peft", "trl", "trainer",
                      "lora", "tokenizer", "finetun", "backprop", "optimizer",
                      "gradient", ".fit(", "dataloader"):
            self.assertNotIn(token, src, token)

    def test_writes_only_the_assessment_file(self):
        with open(SRC, encoding="utf-8") as f:
            src = f.read()
        self.assertIn("P3_D_READINESS_V2.json", src)
        for token in ("jsonl", "parquet", "safetensors", ".bin\"",
                      "prompt_completion", "train_split"):
            self.assertNotIn(token, src, token)

    def test_read_only_sources(self):
        """Sources are opened read-only; the only write target is OUT."""
        with open(SRC, encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn('open(OUT, "r', src)
        self.assertEqual(src.count('"w"'), 1)


if __name__ == "__main__":
    unittest.main()
