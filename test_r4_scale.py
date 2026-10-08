"""Hermetic tests for the R-4 scale runner. No models, no lint: pool rule,
row shape, config pins. The pool rule (constraint agreement) is the frozen
gate that keeps misleading prompts out of scale data."""
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

from r4_scale_run import (MODEL_ID, SPEC_TAG, TIMEOUT_R2, build_row,  # noqa: E402
                          pool_cases)


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


class TestR4Pool(unittest.TestCase):
    def test_pool_is_p2_plus_agreeing_r2b(self):
        """Amendment A1: agreement now requires width match too. Cycle-1
        lesson: R2B-R-00/01 matched on expect (0==0) but computed width 4
        vs true width 1 — a wrong-line constraint. Both are excluded with
        recorded width-mismatch reasons; the pool is P2-only until
        agreeing real cases exist."""
        pool, excluded = pool_cases()
        origins = [o for o, _ in pool]
        self.assertEqual(origins.count("P2"), 20)
        self.assertEqual([c["id"] for o, c in pool if o == "R2B"], [])
        self.assertEqual(len(excluded), 11)
        wdrop = {e["id"]: e for e in excluded
                 if e["id"] in ("R2B-R-00", "R2B-R-01")}
        self.assertEqual(len(wdrop), 2)
        for e in wdrop.values():
            self.assertNotEqual(e["con_width"], e["case_width"])
        for e in excluded:
            self.assertTrue(e["reason"] or
                            e["con_width"] != e["case_width"], e["id"])

    def test_row_shape_feeds_assessor(self):
        r = {"stage_rank": {"abstained": False, "answer": "assign q = 1'b0;",
                            "n_passing": 4, "sim": "not-run"},
             "stage_constraint": {"ok": True}, "latency_s": 1.5,
             "tokens": 100}
        row = build_row("P2", {"id": "P2-R2-00"}, r, 1)
        for k in ("cycle", "origin", "case", "closed", "first_pass",
                  "n_passing", "n_candidates", "abstained", "sim",
                  "answer", "constraint", "latency_s", "tokens"):
            self.assertIn(k, row, k)
        self.assertEqual((row["cycle"], row["origin"]), (1, "P2"))
        self.assertTrue(row["closed"])

    def test_config_pins(self):
        import r4_scale_run as r
        self.assertEqual(MODEL_ID, "qwen2.5-coder-14b-instruct")
        self.assertEqual(TIMEOUT_R2, 3600)
        self.assertEqual(SPEC_TAG, "p3-r4-scale-frozen")
        self.assertTrue(r.TRAJ_PATH.endswith("R4_TRAJECTORIES.json"))


if __name__ == "__main__":
    unittest.main()
