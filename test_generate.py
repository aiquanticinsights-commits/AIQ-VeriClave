"""Unit tests for typed generation (no infra; determinism asserted)."""
import unittest

from generate import (generate, generate_checker, generate_covergroup,
                      generate_sva, generate_test)
from intent import Clock, Reset, Signal, VerificationIntent


def fir_intent(**kw):
    d = {"requirement_id": "REQ-FIR", "module": "async_fifo",
         "artifact": "sva",
         "signals": [Signal("full", 1), Signal("count", 4)],
         "clocks": [Clock("clk", 10.0)],
         "reset": Reset("rst_n", "active-low", "async"),
         "temporal": ["|->"]}
    d.update(kw)
    return VerificationIntent(**d)


class TestSva(unittest.TestCase):
    def test_width_properties_present(self):
        out = generate_sva(fir_intent())
        self.assertIn("$bits(full) == 1", out)
        self.assertIn("$bits(count) == 4", out)
        self.assertIn("REQ-FIR", out)
        self.assertIn("@(posedge clk", out)
        self.assertIn("rst_n", out)

    def test_no_reset_form(self):
        it = fir_intent()
        it.reset = None
        out = generate_sva(it)
        self.assertIn("@(posedge clk)", out)
        self.assertNotIn("rst_n", out)

    def test_deterministic(self):
        self.assertEqual(generate_sva(fir_intent()), generate_sva(fir_intent()))


class TestCovergroup(unittest.TestCase):
    def test_coverpoints(self):
        out = generate_covergroup(fir_intent(artifact="coverage"))
        self.assertIn("covergroup cg_REQ-FIR", out)
        self.assertIn("cp_full", out)
        self.assertIn("cp_count", out)
        self.assertIn("endgroup", out)


class TestChecker(unittest.TestCase):
    def test_checker_executes(self):
        ns: dict = {}
        exec(generate_checker(fir_intent(artifact="checker")), ns)
        self.assertEqual(ns["check"]({"full": 0, "count": 5}), [])
        bad = ns["check"]({"full": 3, "count": 5})
        self.assertTrue(any("full" in v for v in bad))

    def test_widths_table(self):
        out = generate_checker(fir_intent(artifact="checker"))
        self.assertIn("'count': 4", out)
        self.assertIn("REQ-FIR", out)


class TestTestOutline(unittest.TestCase):
    def test_outline_contents(self):
        out = generate_test(fir_intent(artifact="test"))
        self.assertIn("rst_n", out)
        self.assertIn("full[1b]", out)
        self.assertIn("|->", out)
        self.assertIn("FRM", out)


class TestRefusal(unittest.TestCase):
    def test_invalid_intent_refused_all_lanes(self):
        bad = fir_intent(signals=[])
        for fn in (generate_sva, generate_covergroup, generate_checker, generate_test):
            with self.assertRaises(ValueError, msg=fn.__name__):
                fn(bad)

    def test_unknown_artifact_refused(self):
        it = fir_intent()
        it.artifact = "haiku"
        with self.assertRaises(ValueError):
            generate(it)

    def test_dispatch_all_kinds(self):
        for kind in ("sva", "test", "coverage", "checker"):
            out = generate(fir_intent(artifact=kind))
            self.assertTrue(out.strip())


if __name__ == "__main__":
    unittest.main(verbosity=2)
