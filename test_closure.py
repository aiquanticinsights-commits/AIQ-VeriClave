"""Tripwire tests for the closure boundary (no infra). Each test attempts a
forbidden behavior; all must raise — that is the qualification evidence."""
import unittest

from closure import MAX_AUTO_ROUNDS, ClosureBoundary


class TestBoundary(unittest.TestCase):
    def test_three_rounds_then_escalation(self):
        c = ClosureBoundary("R-1")
        for r in range(4):
            c.attempt(f"cand{r}", "FAIL", evidence_hash=f"h{r}")
        self.assertTrue(c.escalated)
        self.assertEqual(c.disposition(), "HUMAN_ESCALATION")

    def test_no_silent_round_four(self):
        c = ClosureBoundary("R-1")
        for r in range(4):
            c.attempt(f"cand{r}", "FAIL", evidence_hash=f"h{r}")
        with self.assertRaises(RuntimeError):
            c.attempt("sneaky", "FAIL", evidence_hash="h9")

    def test_no_attempts_after_escalation(self):
        c = ClosureBoundary("R-1")
        for r in range(4):
            c.attempt(f"cand{r}", "FAIL", evidence_hash=f"h{r}")
        with self.assertRaises(RuntimeError):
            c.attempt("late", "PASS", evidence_hash="h10")

    def test_unresolved_fail_never_becomes_pass(self):
        c = ClosureBoundary("R-1")
        c.attempt("c0", "FAIL", evidence_hash="h0")
        self.assertEqual(c.disposition(), "OPEN")
        self.assertNotEqual(c.disposition(), "PASS")

    def test_pass_wins(self):
        c = ClosureBoundary("R-1")
        c.attempt("c0", "FAIL", evidence_hash="h0")
        c.attempt("c1", "PASS", evidence_hash="h1")
        self.assertEqual(c.disposition(), "PASS")

    def test_no_evidence_overwrite(self):
        c = ClosureBoundary("R-1")
        c.attempt("c0", "FAIL", evidence_hash="same")
        with self.assertRaises(RuntimeError):
            c.attempt("c1", "FAIL", evidence_hash="same")

    def test_no_dropped_candidates(self):
        c = ClosureBoundary("R-1")
        c.attempt("c0", "FAIL", evidence_hash="h0")
        c.attempt("c1", "FAIL", evidence_hash="h1")
        self.assertEqual(c.recorded_candidates(), ["c0", "c1"])

    def test_reject_nonbinary_verdict(self):
        c = ClosureBoundary("R-1")
        with self.assertRaises(ValueError):
            c.attempt("c0", "MAYBE", evidence_hash="h0")

    def test_max_is_three(self):
        self.assertEqual(MAX_AUTO_ROUNDS, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
