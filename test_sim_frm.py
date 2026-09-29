"""Unit tests for sim/FRM co-simulation (FRM pure; live sim needs Verilator).

FRM transliteration, DSL gate, and comparator run everywhere. The live
RTL-vs-FRM equivalence test runs wherever Verilator is reachable (WSL on
Windows, native on Linux CI) and skips otherwise.
"""
import os
import shutil
import tempfile
import unittest

from sim_frm import (WbDmaFrm, assemble_stim, compare_traces, fpr_campaign,
                     fuzz_stim, grade_llm_stimulus, tool_ok, validate_stim)

XFER = ["rst",
        "w 0 00001000", "w 4 00002000", "w 8 00000002", "w c 00000007",
        "w 14 00000001", "tick 10", "w c 00000006", "tick 4", "r 10"]


class TestDSL(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_stim(["RST", "W 0 A0", "R 10", "TICK 5"]),
                         ["rst", "w 0 a0", "r 10", "tick 5"])

    def test_rejects(self):
        for bad in (["W 0"], ["X 1"], ["w 0 1 2"], ["TICK 0"],
                    ["tick 1001"], ["W ZZ 1"], ["rm -rf /"]):
            with self.assertRaises(ValueError, msg=bad):
                validate_stim(bad)


class TestFRM(unittest.TestCase):
    def test_reset_values(self):
        f = WbDmaFrm()
        self.assertEqual((f.src_addr, f.word_count, f.ctrl, f.status), (0, 0, 0, 0))
        self.assertFalse(f.irq())

    def test_write_read_roundtrip(self):
        f = WbDmaFrm()
        tr = f.run_stim(["rst", "w 0 12345678", "r 0"])
        self.assertIn("R 00000000 12345678", tr)
        self.assertIn("W 00000000 12345678 ack=1", tr)

    def test_ack_timing(self):
        f = WbDmaFrm()
        tr = f.run_stim(["rst", "w c 1"])
        self.assertTrue(all("ack=1" in t for t in tr if t.startswith("W")))

    def test_transfer_completes_with_irq(self):
        f = WbDmaFrm()
        tr = f.run_stim(XFER)
        self.assertIn("IRQ 1", tr)
        self.assertIn("R 00000010 00000002", tr)

    def test_transfer_without_enable_no_irq(self):
        stim = [s for s in XFER if not s.startswith("w 14")]
        tr = WbDmaFrm().run_stim(stim)
        self.assertNotIn("IRQ 1", tr)
        self.assertIn("R 00000010 00000002", tr)

    def test_status_clear(self):
        f = WbDmaFrm()
        tr = f.run_stim(XFER + ["w 10 0000000f", "r 10"])
        self.assertIn("R 00000010 00000000", tr)


class TestCompare(unittest.TestCase):
    def test_match(self):
        r = compare_traces(["a", "b"], ["a", "b"])
        self.assertTrue(r["match"])
        self.assertEqual(r["events"], 2)

    def test_first_divergence(self):
        r = compare_traces(["a", "X"], ["a", "Y"])
        self.assertFalse(r["match"])
        self.assertEqual((r["first_diverge"], r["frm"], r["rtl"]),
                         (1, "X", "Y"))

    def test_length_mismatch(self):
        r = compare_traces(["a"], ["a", "b"])
        self.assertFalse(r["match"])
        self.assertEqual(r["first_diverge"], 1)


class TestFuzz(unittest.TestCase):
    def test_deterministic_and_valid(self):
        a, b = fuzz_stim(3), fuzz_stim(3)
        self.assertEqual(a, b)
        self.assertNotEqual(fuzz_stim(3), fuzz_stim(4))
        validate_stim(a)  # every fuzz program passes the DSL gate

    def test_fpr_small_campaign(self):
        if not _sim_available():
            self.skipTest("needs Verilator + wb_dma RTL")
        import tempfile
        work = tempfile.mkdtemp(prefix="wbfpr_test_")
        try:
            rep = fpr_campaign([0, 1, 2], workdir=work)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        self.assertEqual(rep["n"], 3)
        self.assertEqual(rep["mismatches"], 0)
        self.assertEqual(rep["fpr"], 0.0)


class TestStimSlots(unittest.TestCase):
    def test_valid_assembly(self):
        prog = assemble_stim("SRC: 1000\nDST: 2000\nCOUNT: 1\nCTRL: 7\n"
                             "IRQEN: 1\nWAIT: 28")
        self.assertEqual(prog, ["rst", "w 0 00001000", "w 4 00002000",
                                "w 8 1", "w c 7", "w 14 1", "tick 40",
                                "r 10"])
        validate_stim(prog)  # assembled output always passes the DSL gate

    def test_rejects(self):
        self.assertIsNone(assemble_stim("SRC: 1000\nDST: 2000"))  # incomplete
        self.assertIsNone(assemble_stim(  # count out of range
            "SRC: 1000\nDST: 2000\nCOUNT: 99\nCTRL: 7\nIRQEN: 1\nWAIT: 40"))
        self.assertIsNone(assemble_stim(  # start bit clear
            "SRC: 1000\nDST: 2000\nCOUNT: 1\nCTRL: 6\nIRQEN: 1\nWAIT: 40"))
        self.assertIsNone(assemble_stim("free prose"))
        self.assertIsNone(assemble_stim(  # non-hex
            "SRC: xyz\nDST: 2000\nCOUNT: 1\nCTRL: 7\nIRQEN: 1\nWAIT: 40"))


def _sim_available():
    from sim_frm import DEFAULT_RTL
    return tool_ok() and os.path.isfile(DEFAULT_RTL)


@unittest.skipUnless(_sim_available(), "needs Verilator + wb_dma RTL")
class TestLiveCoSim(unittest.TestCase):
    def test_frm_matches_rtl_on_transfer(self):
        from sim_frm import co_sim
        work = tempfile.mkdtemp(prefix="wbsim_test_")
        try:
            res = co_sim(XFER, workdir=work)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        self.assertTrue(res["match"], msg=str(res)[:1500])
        self.assertGreater(res.get("events", 0), 5)

    def test_llm_round_verdict(self):
        work = tempfile.mkdtemp(prefix="wbsim_test_")
        try:
            v = grade_llm_stimulus(XFER, workdir=work)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        self.assertTrue(v["verdict"])
        self.assertTrue(v["sim_equiv"])
        self.assertTrue(v["transfer_completed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
