"""Unit tests for the frozen P4 benchmark protocol (no infra)."""
import json
import os
import unittest

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'P4_BENCH_v1.json')
REQUIRED_DIAGNOSTICS = {"SYNTAX_ERROR", "FORMAL_COUNTEREXAMPLE", "ASSERTION_FAIL",
                        "TIMEOUT", "UNPROVEN", "MUTANT_SURVIVED", "TRACE_MISMATCH",
                        "WIDTH_MISMATCH", "SIGNAL_NOT_FOUND", "RESET_MISMATCH",
                        "CLOCK_DOMAIN_MISMATCH"}


def load():
    with open(PATH, encoding='utf-8') as f:
        return json.load(f)


class TestP4BenchFrozen(unittest.TestCase):
    def test_loads_and_frozen(self):
        d = load()
        self.assertEqual(d["status"], "frozen")
        self.assertEqual(d["freeze"]["version"], "P4_BENCH_v1")
        self.assertTrue(d["freeze"]["date"])
        self.assertIn("no change", d["freeze"]["rule"].lower())

    def test_tracks_cover_p405_to_p409(self):
        tracks = load()["tracks"]
        covered = sorted({c for t in tracks.values() for c in t.get("covers", [])})
        for need in ("P4-05", "P4-06", "P4-07", "P4-08", "P4-09"):
            self.assertIn(need, covered, need)

    def test_each_track_has_bar_and_grader(self):
        for name, t in load()["tracks"].items():
            self.assertTrue(t.get("bar"), name)
            self.assertTrue(t.get("grader"), name)

    def test_diagnostic_schema_complete(self):
        diags = set(load()["diagnostics"])
        self.assertEqual(diags, REQUIRED_DIAGNOSTICS)

    def test_closure_boundary_encoded(self):
        t = load()["tracks"]["closure_boundary"]
        self.assertIn("R0", t["bar"] + t.get("grader", "") or "")
        blob = json.dumps(t)
        self.assertIn("Round 4", blob)

    def test_regression_guard_and_human_signoff(self):
        acc = load()["acceptance_global"]
        self.assertTrue(acc["human_signoff_required"])
        self.assertEqual(acc["false_acceptances_max"], 0)
        self.assertIn("P0", acc["regression_guard"])

    def test_cpu_only_environment(self):
        env = load()["environment"]
        blob = json.dumps(env).lower()
        self.assertIn("cpu", blob)
        self.assertTrue(env.get("python", "").startswith("3."))


if __name__ == "__main__":
    unittest.main(verbosity=2)
