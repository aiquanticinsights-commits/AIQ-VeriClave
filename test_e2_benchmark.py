"""Unit tests for the E2 portability benchmark (pure compare + skip paths)."""
import unittest

from scripts.run_portability_benchmark import compare, mutant_spot


def _side(unitt=True, sha="aaa", lint=True, sby="PASS", mut=None):
    return {"checks": {
        "unittest": {"pass": unitt, "tests": ["1"]},
        "frm_traces": {"pass": True, "sha": sha, "events": 1},
        "verilator_lint": {"pass": lint, "rc": 0},
        "yosys_synth": {"pass": True, "rc": 0},
        "sby_demo": {"pass": True, "status": sby}},
        "_mut_spot": {"classifications": mut if mut is not None else {}}}


class TestCompare(unittest.TestCase):
    def test_all_equivalent(self):
        m = {"M001": "KILLED", "M002": "SURVIVED"}
        rows = compare(_side(mut=m), _side(mut=dict(m)),
                       {"formal_result": "PASS"})
        bad = {k: v for k, v in rows.items() if v["variance"] not in ("none",)}
        self.assertEqual(bad, {})

    def test_diverged(self):
        rows = compare(_side(mut={"M001": "KILLED"}),
                       _side(mut={"M001": "SURVIVED"}),
                       {"formal_result": "PASS"})
        self.assertEqual(rows["mutation/spot"]["variance"], "DIVERGED")

    def test_unmeasured(self):
        rows = compare(_side(), _side(), {"formal_result": "PASS"})
        # empty mutant spots on both sides -> UNMEASURED, never EQUIVALENT
        self.assertEqual(rows["mutation/spot"]["variance"], "UNMEASURED")

    def test_formal_fail(self):
        rows = compare(_side(), _side(), {"formal_result": "FAIL"})
        self.assertEqual(rows["formal/sby-demo"]["variance"], "DIVERGED")


class TestLegParsing(unittest.TestCase):
    def test_markers(self):
        from scripts.run_portability_benchmark import parse_leg_output
        log = ('noise\n@@PORTABILITY@@\n{"a": 1}\n@@MUT@@\n{"b": 2}\n'
               'mutant spot done: x\ntail')
        doc, mut = parse_leg_output(log)
        self.assertEqual((doc, mut), ({"a": 1}, {"b": 2}))

    def test_malformed_raises(self):
        from scripts.run_portability_benchmark import parse_leg_output
        with self.assertRaises((IndexError, ValueError)):
            parse_leg_output("no markers here")
        with self.assertRaises((IndexError, ValueError)):
            parse_leg_output("@@PORTABILITY@@\n{bad\n@@MUT@@\n{}")


class TestSpotSkip(unittest.TestCase):
    def test_skip_without_rtl(self):
        import sim_frm
        from scripts.run_portability_benchmark import mutant_spot
        orig = sim_frm.DEFAULT_RTL
        try:
            sim_frm.DEFAULT_RTL = "/nonexistent/x.v"
            res = mutant_spot("/tmp/never")
            self.assertEqual(res["classifications"], {})
            self.assertIn("skipped", res)
        finally:
            sim_frm.DEFAULT_RTL = orig


if __name__ == "__main__":
    unittest.main(verbosity=2)
