"""Unit tests for machine-readable verifier feedback (no infra)."""
import json
import os
import unittest

from diagnostics import (DIAGNOSTICS, REMEDY, Diagnostic, diagnose,
                         from_failure_event, remedy_for)


class TestSchema(unittest.TestCase):
    def test_eleven_frozen_codes(self):
        self.assertEqual(len(DIAGNOSTICS), 11)
        for c in ("SYNTAX_ERROR", "FORMAL_COUNTEREXAMPLE", "ASSERTION_FAIL",
                  "TIMEOUT", "UNPROVEN", "MUTANT_SURVIVED", "TRACE_MISMATCH",
                  "WIDTH_MISMATCH", "SIGNAL_NOT_FOUND", "RESET_MISMATCH",
                  "CLOCK_DOMAIN_MISMATCH"):
            self.assertIn(c, DIAGNOSTICS)

    def test_matches_bench_manifest(self):
        bench = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'P4_BENCH_v1.json'),
                               encoding='utf-8'))
        self.assertEqual(set(bench["diagnostics"]), DIAGNOSTICS)

    def test_unknown_code_rejected(self):
        with self.assertRaises(ValueError):
            diagnose("VIBES_OFF")
        with self.assertRaises(ValueError):
            remedy_for("VIBES_OFF")


class TestRouting(unittest.TestCase):
    def test_every_code_has_remedy(self):
        for c in DIAGNOSTICS:
            self.assertTrue(remedy_for(c))

    def test_remedies_distinct_enough(self):
        # targeted, not one generic retry: at least 8 distinct remedies
        self.assertGreaterEqual(len(set(REMEDY.values())), 8)

    def test_from_failure_event(self):
        d = from_failure_event("vcs", "error", "Error-foo: syntax bar")
        self.assertEqual(d.code, "SYNTAX_ERROR")
        d = from_failure_event("verilator", "failure", "Assertion failed at t=5")
        self.assertEqual(d.code, "ASSERTION_FAIL")
        d = from_failure_event("sby", "failure", "engine timed out after 300s")
        self.assertEqual(d.code, "TIMEOUT")
        d = from_failure_event("x", "warning", "mysterious wobble")
        self.assertEqual(d.code, "TRACE_MISMATCH")
        self.assertEqual(d.source, "x")


if __name__ == "__main__":
    unittest.main(verbosity=2)
