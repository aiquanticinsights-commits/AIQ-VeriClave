"""Unit tests for the independent re-runner (fast; no full re-run inside)."""
import json
import unittest

from p5_rerun import compare_against_baseline, strip_meta

BASE = r'C:\Projects\ChipDesign\AIQ-VeriClave'


class TestRerunCompare(unittest.TestCase):
    def test_match_on_identical(self):
        d = {"overall": "PASS", "freeze_intact": True,
             "families": {"a": {"verdict": "PASS"}}, "reproducible": True}
        with open(f'{BASE}\\P5_EXECUTION.json', encoding='utf-8') as f:
            base = json.load(f)
        # compare baseline against itself via a copy
        res = compare_against_baseline(json.loads(json.dumps(base)))
        self.assertTrue(res["match"])
        self.assertEqual(res["verdict"], "REPRODUCED")

    def test_mismatch_detected(self):
        with open(f'{BASE}\\P5_EXECUTION.json', encoding='utf-8') as f:
            base = json.load(f)
        tampered = json.loads(json.dumps(base))
        fam = sorted(tampered["families"])[0]
        tampered["families"][fam]["verdict"] = "FAIL"
        res = compare_against_baseline(tampered)
        self.assertFalse(res["match"])
        self.assertEqual(res["verdict"], "FINDING-NON-REPRODUCIBLE")

    def test_meta_excluded(self):
        d = {"overall": "PASS", "reproducible": True}
        self.assertNotIn("reproducible", strip_meta(d))
        self.assertIn("overall", strip_meta(d))

    def test_baseline_wellformed(self):
        with open(f'{BASE}\\P5_EXECUTION.json', encoding='utf-8') as f:
            base = json.load(f)
        self.assertEqual(base["overall"], "PASS")
        self.assertTrue(base["freeze_intact"])
        self.assertEqual(len(base["families"]), 4)

    def test_rerun_record_shape(self):
        with open(f'{BASE}\\P5_RERUN.json', encoding='utf-8') as f:
            rec = json.load(f)
        self.assertEqual(rec["comparison"]["verdict"], "REPRODUCED")
        self.assertEqual(rec["executor"], "independent-clean-process")


if __name__ == "__main__":
    unittest.main(verbosity=2)
