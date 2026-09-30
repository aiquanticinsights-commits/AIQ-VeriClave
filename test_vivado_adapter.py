"""Unit tests for the Vivado adapter (canned logs/files — no Vivado needed)."""
import os
import tempfile
import unittest

from evidence import EvidenceLedger
from vivado_adapter import (collect_block, note, normalize_evidence,
                            parse_drc, parse_timing, parse_util, to_ledger,
                            write_batch_tcl)

TIMING = """
| Design Timing Summary
| ---------------------
|     WNS(ns)      |    WHS(ns)     |    WPWS(ns)    |
|     -------      |    --------    |    --------    |
|         3.412    |        0.089   |        4.500   |
|     TNS(ns)      |    THS(ns)     |
|         0.000    |        0.000   |
"""
UTIL = """
| Slice Logic
| ------------
|     Site Type     | Used | Fixed |
| Slice LUTs*       |  124 |     0 |
| Slice Registers   |   67 |     0 |
| Block RAM Tile    |    0 |     0 |
| DSPs              |    0 |     0 |
"""
DRC_CLEAN = "Checking DRCs ...\nNo DRC violations were found.\n"


class TestParsers(unittest.TestCase):
    def test_timing(self):
        t = parse_timing(TIMING)
        self.assertAlmostEqual(t["wns_ns"], 3.412)
        self.assertAlmostEqual(t["whs_ns"], 0.089)

    def test_timing_absent(self):
        t = parse_timing("no clocks found\n")
        self.assertIsNone(t["wns_ns"])

    def test_util(self):
        u = parse_util(UTIL)
        self.assertEqual((u["lut"], u["ff"], u["bram"], u["dsp"]),
                         (124, 67, 0, 0))

    def test_util_absent(self):
        self.assertIsNone(parse_util("nothing")["lut"])

    def test_drc(self):
        self.assertEqual(parse_drc(DRC_CLEAN),
                         {"violations": 0, "clean": True})
        self.assertIsNone(parse_drc("")["clean"])
        bad = parse_drc("CRITICAL WARNING [DRC UCIO-1] foo")
        self.assertFalse(bad["clean"])


class TestNote(unittest.TestCase):
    def test_note_format(self):
        line = note("X is missing", "do Y instead")
        self.assertIn("LIMITATION", line)
        self.assertIn("alternative", line)


class TestTcl(unittest.TestCase):
    def test_batch_content(self):
        d = tempfile.mkdtemp()
        p = write_batch_tcl(
            [{"top": "gate_a_stop", "src": "a.sv", "outdir": d + "/a"},
             {"top": "gate_e_speed", "src": "e.sv", "outdir": d + "/e"}],
            os.path.join(d, "batch.tcl"), part="xc7a100tcsg324-1",
            xdc=os.path.join(d, "gates.xdc"))
        text = open(p, encoding="utf-8").read()
        self.assertIn("gate_a_stop", text)
        self.assertIn("synth_design", text)
        self.assertIn("opt_design", text)
        self.assertIn("place_design", text)
        self.assertIn("route_design", text)
        self.assertIn("report_drc", text)
        self.assertIn("write_checkpoint", text)
        self.assertIn("read_xdc", text)
        self.assertTrue(os.path.isdir(d + "/a"))  # outdirs pre-created


class TestCollectLedger(unittest.TestCase):
    def _outdir(self, timing=True, dcp=True):
        d = tempfile.mkdtemp()
        if timing:
            open(os.path.join(d, "timing.rpt"), "w").write(TIMING)
        open(os.path.join(d, "util.rpt"), "w").write(UTIL)
        open(os.path.join(d, "drc.rpt"), "w").write(DRC_CLEAN)
        if dcp:
            open(os.path.join(d, "post_route.dcp"), "w").write("fake")
        return d

    def test_collect_pass(self):
        res = collect_block(self._outdir())
        self.assertEqual(res["checks"]["synth"], "PASS")
        self.assertEqual(res["checks"]["util"]["lut"], 124)

    def test_collect_missing_dcp(self):
        res = collect_block(self._outdir(dcp=False))
        self.assertEqual(res["checks"]["synth"], "FAIL")

    def test_ledger_pass_and_fail(self):
        from evidence import EvidenceRecord  # noqa: F401 (contract import)
        good = {"tool": "AMD Vivado", "tool_version": "2026.1",
                "target_device": "x", "rtl_commit": "", "run_id": "r",
                "requirement_ids": [],
                "vivado": {"status": "PASS",
                           "checks": {"synth": "PASS",
                                      "drc": {"clean": True}},
                           "duration_s": 1.0, "reason": ""},
                "artifacts": [], "artifact_hashes": {},
                "limitations": [], "evidence_hash": "ab12"}
        L = EvidenceLedger()
        to_ledger(L, "R-A", good, "vivado/gate_a")
        self.assertEqual(L.records[0].verdict, "PASS")
        bad = dict(good)
        bad["vivado"] = dict(good["vivado"], status="FAIL")
        L2 = EvidenceLedger()
        to_ledger(L2, "R-A", bad, "vivado/gate_a")
        self.assertEqual(L2.records[0].verdict, "NOT_EXECUTED")

    def test_evidence_schema(self):
        from vivado_adapter import normalize_evidence as ne
        ev = ne(__import__("vivado_adapter").VivadoRun(
            status="PASS", run_id="r"))
        for k in ("tool", "tool_version", "target_device", "run_id",
                  "vivado", "artifacts", "artifact_hashes", "limitations",
                  "evidence_hash"):
            self.assertIn(k, ev)


if __name__ == "__main__":
    unittest.main(verbosity=2)
