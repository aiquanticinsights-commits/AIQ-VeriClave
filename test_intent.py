"""Unit tests for the structured verification-intent schema (no infra)."""
import unittest

from intent import Clock, Reset, Signal, VerificationIntent


def good_intent(**kw):
    d = {"requirement_id": "REQ-001", "module": "wb_dma",
         "artifact": "sva",
         "signals": [Signal("full", 1), Signal("count", 8)],
         "clocks": [Clock("clk", 10.0)],
         "reset": Reset("rst_n", "active-low", "async"),
         "temporal": ["|->", "##1"]}
    d.update(kw)
    return VerificationIntent(**d)


class TestIntentValid(unittest.TestCase):
    def test_good_intent_passes(self):
        self.assertEqual(good_intent().validate(), [])
        self.assertTrue(good_intent().valid)

    def test_round_trip(self):
        it = good_intent()
        back = VerificationIntent.from_dict(it.to_dict())
        self.assertEqual(back.validate(), [])
        self.assertEqual(back.signals[1].width, 8)
        self.assertEqual(back.reset.polarity, "active-low")


class TestIntentRejects(unittest.TestCase):
    def test_bad_artifact(self):
        self.assertIn("artifact", " ".join(good_intent(artifact="haiku").validate()))

    def test_empty_signals(self):
        errs = good_intent(signals=[]).validate()
        self.assertTrue(any("signals empty" in e for e in errs))

    def test_zero_width(self):
        it = good_intent(signals=[Signal("x", 0)])
        self.assertTrue(any("width" in e for e in it.validate()))

    def test_undeclared_clock(self):
        it = good_intent(signals=[Signal("x", 1, "clk2")])
        self.assertTrue(any("clk2" in e for e in it.validate()))

    def test_bad_period(self):
        it2 = good_intent()
        it2.clocks = [Clock("clk", -1.0)]
        self.assertTrue(any("period" in e for e in it2.validate()))

    def test_bad_reset(self):
        it = good_intent(reset=Reset("r", "sometimes", "async"))
        self.assertTrue(any("polarity" in e for e in it.validate()))
        it = good_intent(reset=Reset("r", "active-high", "eventually"))
        self.assertTrue(any("kind" in e for e in it.validate()))

    def test_missing_ids(self):
        it = good_intent(requirement_id="  ", module="")
        errs = it.validate()
        self.assertTrue(any("requirement_id" in e for e in errs))
        self.assertTrue(any("module" in e for e in errs))

    def test_from_dict_dict_inputs(self):
        d = {"requirement_id": "R", "module": "m", "artifact": "test",
             "signals": [{"name": "a", "width": 4, "clock": "clk"}],
             "clocks": [{"name": "clk", "period_ns": 20.0}],
             "reset": {"name": "rst", "polarity": "active-high", "kind": "sync"}}
        self.assertEqual(VerificationIntent.from_dict(d).validate(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
