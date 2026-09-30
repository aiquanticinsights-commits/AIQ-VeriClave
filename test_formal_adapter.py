"""Unit tests for the vendor-neutral formal adapter (no sby needed).

Live sby runs happen on the dev machine only (recorded in FORMAL_WB_DMA.json);
every unit here uses canned logs / missing files / policy skips / mocks.
"""
import os
import shutil
import tempfile
import unittest
from unittest import mock

from evidence import EvidenceLedger
from formal_adapter import (EDA_STATUS, FormalRun, collect_artifacts,
                            normalize_evidence, parse_sby_log, prove_wb_prop,
                            report_status, run_formal, to_ledger)

PASS_LOG = """SBY v0.68
engine_0: Status: passed
engine_0: Assert `A_ACK' passed
engine_0: Assert `A_IRQ' passed
SBY [prove] DONE (PASS, rc=0)
"""

FAIL_LOG = """SBY v0.68
engine_0: Check `A_ACK' failed
SBY [prove] DONE (FAIL, rc=1)
"""

TIMEOUT_LOG = """SBY v0.68
engine_0: smtbmc running ...
TIMEOUT reached, killing engine
"""


class TestGrammar(unittest.TestCase):
    def test_pass(self):
        status, asserts = parse_sby_log(PASS_LOG)
        self.assertEqual(status, "PASS")
        self.assertEqual(asserts.get("A_ACK"), "PASS")

    def test_pass_names_supplied_asserts(self):
        status, asserts = parse_sby_log("SBY x DONE (PASS, rc=0)\n",
                                        ("A_ACK", "A_CYC"))
        self.assertEqual(status, "PASS")
        self.assertEqual(asserts, {"A_ACK": "PASS", "A_CYC": "PASS"})

    def test_fail_names_failed_assert(self):
        log = "summary: failed assertion wb_dma_formal.A_IRQ blah\nDONE (FAIL, rc=2)\n"
        status, asserts = parse_sby_log(log, ("A_ACK", "A_IRQ", "A_CYC"))
        self.assertEqual(status, "FAIL")
        self.assertEqual(asserts.get("A_IRQ"), "FAIL")
        self.assertEqual(asserts.get("A_ACK"), "UNKNOWN")

    def test_fail(self):
        status, asserts = parse_sby_log(FAIL_LOG)
        self.assertEqual(status, "FAIL")
        self.assertEqual(asserts.get("A_ACK"), "FAIL")

    def test_timeout_is_unproven_never_pass(self):
        status, _ = parse_sby_log(TIMEOUT_LOG)
        self.assertEqual(status, "UNPROVEN")

    def test_empty_log_is_unproven(self):
        self.assertEqual(parse_sby_log("")[0], "UNPROVEN")

    def test_status_vocabulary(self):
        for s in ("EXECUTED", "NOT_EXECUTED", "PASS", "FAIL", "UNPROVEN",
                  "UNAVAILABLE", "SKIPPED_BY_POLICY"):
            self.assertIn(s, EDA_STATUS)


class TestNeverRaises(unittest.TestCase):
    def test_missing_sby_file(self):
        r = run_formal("/nonexistent/x.sby", tempfile.mkdtemp())
        self.assertEqual(r.status, "NOT_EXECUTED")

    def test_policy_skip(self):
        r = run_formal("/nonexistent/x.sby", tempfile.mkdtemp(),
                       skip_reason="no license on runner")
        self.assertEqual(r.status, "SKIPPED_BY_POLICY")
        self.assertIn("license", r.reason)

    def test_collect_empty_dir(self):
        self.assertEqual(collect_artifacts(tempfile.mkdtemp()), [])

    def test_report_line(self):
        r = FormalRun(status="PASS", asserts={"A": "PASS"},
                      tool_version="0.68", target="wb_dma")
        s = report_status(r)
        self.assertIn("PASS", s)
        self.assertIn("wb_dma", s)


class TestLedgerMapping(unittest.TestCase):
    def _ev(self, status):
        return {"tool": "SymbiYosys", "tool_version": "0.68",
                "target_device": "wb_dma", "rtl_commit": "abc",
                "run_id": "r1",
                "formal": {"status": status,
                           "asserts": {"A_ACK": status} if status in (
                               "PASS", "FAIL", "UNPROVEN") else {},
                           "duration_s": 1.0, "reason": ""},
                "artifacts": [], "artifact_hashes": {},
                "evidence_hash": "deadbeef"}

    def test_pass_fail_unproven_ledgered(self):
        for status in ("PASS", "FAIL", "UNPROVEN"):
            L = EvidenceLedger()
            to_ledger(L, "R-1", self._ev(status), "formal/A")
            self.assertEqual(L.records[0].verdict, status)
            self.assertAlmostEqual(L.audit_completeness(), 1.0)

    def test_proven_refuted_normalize(self):
        for formal, ledger_v in (("PROVEN", "PASS"), ("REFUTED", "FAIL")):
            L = EvidenceLedger()
            to_ledger(L, "R-1", self._ev(formal), "formal/A")
            self.assertEqual(L.records[0].verdict, ledger_v)

    def test_sim_covered_ledgered(self):
        ev = self._ev("SIM_COVERED")
        ev["formal"]["sim_ref"] = "SIM_FRM_WB_DMA.json#irq-lifecycle"
        L = EvidenceLedger()
        to_ledger(L, "R-IRQ", ev, "formal/A_IRQ")
        self.assertEqual(L.records[0].verdict, "SIM_COVERED")
        self.assertAlmostEqual(L.audit_completeness(), 1.0)

    def test_unavailable_becomes_not_executed(self):
        L = EvidenceLedger()
        to_ledger(L, "R-1", self._ev("UNAVAILABLE"), "formal/A")
        self.assertEqual(L.records[0].verdict, "NOT_EXECUTED")
        self.assertAlmostEqual(L.audit_completeness(), 1.0)

    def test_evidence_schema_keys(self):
        r = FormalRun(status="PASS", asserts={"A_ACK": "PASS"},
                      run_id="r1", rtl_commit="abc", target="wb_dma")
        ev = normalize_evidence(r)
        for k in ("tool", "tool_version", "target_device", "rtl_commit",
                  "run_id", "formal", "artifacts", "artifact_hashes",
                  "evidence_hash"):
            self.assertIn(k, ev)
        self.assertTrue(ev["evidence_hash"])


class TestProveWbProp(unittest.TestCase):
    def test_rejects_non_assertion(self):
        self.assertIsNone(prove_wb_prop("just some text"))

    def _run(self, status):
        return FormalRun(status=status,
                         asserts={"A_GEN": status} if status in (
                             "PASS", "FAIL") else {},
                         run_id="t", target="wb_dma")

    def test_maps_pass_fail_unproven(self):
        prop = "A_GEN: assert(x == $past(y));"
        with mock.patch("formal_adapter.os.path.isfile",
                        return_value=True):
            with mock.patch("formal_adapter.run_formal",
                            return_value=self._run("PASS")) as m:
                self.assertTrue(prove_wb_prop(prop))
                self.assertIn("prop.sby", m.call_args[0][0])
            with mock.patch("formal_adapter.run_formal",
                            return_value=self._run("FAIL")):
                self.assertFalse(prove_wb_prop(prop))
            with mock.patch("formal_adapter.run_formal",
                            return_value=self._run("UNPROVEN")):
                self.assertIsNone(prove_wb_prop(prop))


if __name__ == "__main__":
    unittest.main(verbosity=2)
