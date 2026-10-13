"""Unit tests for the P4 exit demonstration (pure Python, no EDA tools)."""
import unittest

from demo_p4_exit import FifoFRM, build_intent, run_demo


class TestDemoChain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rep = run_demo()

    def test_verdict(self):
        self.assertEqual(self.rep["verdict"], "DEMONSTRATED")

    def test_intent_and_mutant(self):
        self.assertEqual(self.rep["steps"]["intent_valid"], [])
        self.assertTrue(self.rep["steps"]["mutant_killed"])

    def test_closure_pass(self):
        self.assertEqual(self.rep["steps"]["closure"]["disposition"], "PASS")

    def test_trace_complete(self):
        self.assertEqual(self.rep["steps"]["trace"]["completeness"], 1.0)

    def test_ledger_sound(self):
        lg = self.rep["steps"]["ledger"]
        self.assertTrue(lg["chain_ok"])
        self.assertEqual(lg["audit"], 1.0)

    def test_formal_honest_about_host(self):
        f = self.rep["steps"]["formal"]
        self.assertEqual(f["verdict"], "PROVE")
        self.assertIn("UNAVAILABLE", f["execution"])

    def test_frm_mirror(self):
        fifo = FifoFRM()
        for v in (1, 2, 3, 4):
            fifo.push(v)
        self.assertEqual((fifo.full(), fifo.count()), (1, 4))
        bad = FifoFRM(mutant_full_stuck0=True)
        for v in (1, 2, 3, 4):
            bad.push(v)
        self.assertEqual(bad.full(), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
