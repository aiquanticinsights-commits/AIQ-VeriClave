"""Unit tests for the canonical verification reward (no infra)."""
import unittest

from rewards import (GROUP_SIZE, WEIGHTS, compute_reward, group_normalize,
                     select_best)


class TestReward(unittest.TestCase):
    def test_perfect_artifact(self):
        r = compute_reward({"killed": True, "proven": True, "coverage": 1.0,
                            "localized": True}, cost=0.0)
        self.assertAlmostEqual(r, 1.0 + 1.0 + 0.5 + 0.5)

    def test_cost_penalizes_monotonically(self):
        base = {"killed": True, "proven": True, "coverage": 1.0, "localized": True}
        self.assertGreater(compute_reward(base, 0.0), compute_reward(base, 2.0))

    def test_failed_artifact_nonpositive(self):
        r = compute_reward({"killed": False, "proven": False, "coverage": 0.0,
                            "localized": False}, cost=1.0)
        self.assertLessEqual(r, 0.0)

    def test_coverage_clamped(self):
        a = compute_reward({"coverage": 99.0})
        b = compute_reward({"coverage": 1.0})
        self.assertAlmostEqual(a, b)

    def test_group_size_matches_bon(self):
        lo, hi = GROUP_SIZE
        self.assertTrue(5 <= lo <= hi <= 8)


class TestGroupRelative(unittest.TestCase):
    def test_zero_mean_unit_scale(self):
        adv = group_normalize([1.0, 2.0, 3.0, 4.0])
        self.assertAlmostEqual(sum(adv), 0.0, places=9)

    def test_empty(self):
        self.assertEqual(group_normalize([]), [])

    def test_select_best_is_argmax(self):
        outs = ["a", "b", "c"]
        best, adv = select_best(outs, [0.1, 0.9, 0.5])
        self.assertEqual(best, "b")
        self.assertGreater(adv, 0.0)

    def test_ties_stable_earliest(self):
        best, _ = select_best(["x", "y"], [0.5, 0.5])
        self.assertEqual(best, "x")


if __name__ == "__main__":
    unittest.main(verbosity=2)
