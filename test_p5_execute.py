"""Unit tests for P5 independent execution (pure Python, frozen inputs read-only)."""
import unittest

from p5_execute import (Arbiter, FAMILIES, Fifo, Intc, ResetSync, freeze_guard,
                        run_family, run_suite)


class TestFrms(unittest.TestCase):
    def test_fifo_drain_order(self):
        f = Fifo()
        for v in (1, 2, 3, 4):
            f.push(v)
        self.assertEqual([f.pop() for _ in range(4)], [1, 2, 3, 4])
        self.assertIsNone(f.pop())

    def test_arbiter_rotation(self):
        a = Arbiter()
        self.assertEqual([a.grant([1, 1, 1, 1]) for _ in range(4)], [0, 1, 2, 3])
        self.assertEqual(a.grant([0, 0, 0, 0]), -1)

    def test_intc_priority_threshold_claim(self):
        ic = Intc()
        for i in (0, 2, 3):
            ic.raise_irq(i)
        self.assertEqual(ic.winner(), 3)
        ic.claim(3)
        self.assertEqual(ic.winner(), 2)
        lone = Intc()
        lone.raise_irq(0)
        self.assertEqual(lone.winner(), -1)

    def test_resetsync_latency(self):
        r = ResetSync()
        outs = [r.tick(1 if t >= 1 else 0) for t in range(6)]
        self.assertEqual(outs, [0, 0, 0, 1, 1, 1])


class TestP5Verdicts(unittest.TestCase):
    def test_all_families_pass_clean(self):
        for fam in FAMILIES:
            with self.subTest(family=fam):
                v = run_family(fam)
                self.assertEqual(v["verdict"], "PASS")
                self.assertEqual(v["golden_fa"], 0)
                self.assertTrue(all(m["killed"] for m in v["mutants"].values()))
                self.assertEqual(v["closure"]["disposition"], "PASS")
                self.assertEqual(v["trace"]["completeness"], 1.0)
                self.assertTrue(v["ledger_ok"])

    def test_mutant_counts(self):
        expected = {"async-fifo": 3, "round-robin-arbiter": 2,
                    "interrupt-controller": 3, "reset-synchronizer": 2}
        for fam, n in expected.items():
            self.assertEqual(len(run_family(fam)["mutants"]), n)

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            run_family("quantum-fifo")

    def test_deterministic_rerun(self):
        a = run_family("reset-synchronizer")
        b = run_family("reset-synchronizer")
        self.assertEqual(a["verdict"], b["verdict"])
        self.assertEqual(a["mutants"], b["mutants"])

    def test_freeze_guard_shape(self):
        g = freeze_guard()
        self.assertEqual(sorted(g), ["P4_BENCH_v1.json", "P4_HELDOUT_v1.json", "P5_FREEZE_v1.json"])
        for h in g.values():
            self.assertEqual(len(h), 64)

    def test_suite_overall(self):
        out = run_suite()
        self.assertTrue(out["freeze_intact"])
        self.assertEqual(out["overall"], "PASS")
        self.assertEqual(sorted(out["families"]), sorted(FAMILIES))


if __name__ == "__main__":
    unittest.main(verbosity=2)
