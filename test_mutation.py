"""Unit tests for campaign runner + classifier (injected fakes only)."""
import json
import os
import tempfile
import unittest
import unittest.mock

import run_mutants
from classify import C1_TARGET, classify, gate_a_accepts
from run_mutants import campaign


def _cat(n=3, path="x.v"):
    # CTRL_STMT_DELETE applies to any valid line index (deletes the line),
    # so hermetic tests never depend on source content.
    return [{"id": "M%03d" % (i + 1), "file": "x.v", "path": path,
             "line": (i % 5) + 1, "op": "CTRL_STMT_DELETE", "detail": ""}
            for i in range(n)]


SRC5 = ("module x(input wire clk);\n"
        "reg a;\n"
        "always @(posedge clk) a <= 1'b0;\n"
        "wire y = a;\n"
        "endmodule\n")


class TestClassify(unittest.TestCase):
    def test_score_math(self):
        res = {"M001": {"status": "KILLED"}, "M002": {"status": "KILLED"},
               "M003": {"status": "SURVIVED"}, "M004": {"status": "INVALID"},
               "M005": {"status": "INFRA_FAILURE"}}
        rep = classify(res, _cat(5))
        self.assertEqual((rep["killed"], rep["survived"]), (2, 1))
        self.assertAlmostEqual(rep["score"], 2 / 3, places=4)
        self.assertFalse(rep["c1_met"])

    def test_equivalent_only_by_disposition(self):
        res = {"M001": {"status": "SURVIVED"}}
        rep = classify(res, _cat(1))
        self.assertEqual(rep["survived"], 1)
        rep = classify(res, _cat(1), {"M001": "comment-only change"})
        self.assertEqual(rep["equivalent"], 1)
        self.assertEqual(rep["survived"], 0)

    def test_c1_met(self):
        res = {f"M{i:03d}": {"status": "KILLED"} for i in range(1, 20)}
        res["M020"] = {"status": "SURVIVED"}
        rep = classify(res, _cat(20))
        self.assertTrue(rep["score"] >= C1_TARGET)
        self.assertTrue(rep["c1_met"])

    def test_empty(self):
        rep = classify({}, [])
        self.assertEqual(rep["score"], 0.0)
        self.assertFalse(rep["c1_met"])


class TestGateA(unittest.TestCase):
    def _ev(self, **kw):
        d = {"regression_pass": True, "formals_proven": True, "c1": 0.96,
             "unproven": [{"reason": "r", "alternative": "a",
                           "disposition": "d"}],
             "silent_drops": 0, "audit_complete": 1.0}
        d.update(kw)
        return d

    def test_accept(self):
        ok, reasons = gate_a_accepts(self._ev())
        self.assertTrue(ok)
        self.assertEqual(len(reasons), 6)

    def test_each_clause_blocks(self):
        for k, v in (("regression_pass", False), ("formals_proven", False),
                     ("c1", 0.5), ("audit_complete", 0.5),
                     ("silent_drops", 2)):
            ok, _ = gate_a_accepts(self._ev(**{k: v}))
            self.assertFalse(ok, k)

    def test_undispositioned_gap_blocks(self):
        ev = self._ev()
        ev["unproven"] = [{"reason": "r"}]
        ok, _ = gate_a_accepts(ev)
        self.assertFalse(ok)


class TestCampaign(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        patcher = unittest.mock.patch.object(
            run_mutants, "partial_path",
            return_value=os.path.join(self.tmp, "partial.json"))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.src = os.path.join(self.tmp, "x.v")
        with open(self.src, "w", encoding="utf-8") as f:
            f.write(SRC5)

    def test_killed_by_syntax(self):
        def lint(path):
            return False, "%Error: boom"

        def sim(stim):
            raise AssertionError("sim must not run after syntax kill")

        res = campaign(_cat(2, self.src), workdir=self.tmp, lint_fn=lint, sim_fn=sim)
        self.assertTrue(all(r["status"] == "KILLED" for r in res.values()))
        self.assertTrue(all(r["by"] == "syntax" for r in res.values()))

    def test_sim_kill_and_survive(self):
        def lint(path):
            return True, ""

        calls = []

        def sim(stim):
            calls.append(stim)
            if len(calls) == 1:
                return {"match": False, "first_diverge": 0,
                        "frm": "a", "rtl": "b"}
            return {"match": True, "first_diverge": -1, "frm": "", "rtl": ""}

        res = campaign(_cat(2, self.src), workdir=self.tmp, lint_fn=lint, sim_fn=sim)
        statuses = sorted(r["status"] for r in res.values())
        self.assertEqual(statuses, ["KILLED", "SURVIVED"])

    def test_invalid_no_file(self):
        res = campaign(_cat(1), workdir=self.tmp)
        # real apply path, sources point nowhere -> INVALID, never raises
        self.assertEqual(res["M001"]["status"], "INVALID")

    def test_build_diagnostics_kill_not_infra(self):
        # A build that fails WITH tool diagnostics is a caught mutant
        # (KILLED-build); only tool absence/crash is INFRA.
        import sim_frm
        from run_mutants import sim_kill

        def boom(stim, rtl_path="", workdir=""):
            raise RuntimeError("verilator build failed:\n%Error: boom")

        with unittest.mock.patch.object(sim_frm, "co_sim", side_effect=boom):
            killed, detail = sim_kill("m.v", self.tmp)
        self.assertTrue(killed)
        self.assertIn("build-gate", detail)

    def test_tool_crash_stays_infra(self):
        import sim_frm
        from run_mutants import sim_kill

        def crash(stim, rtl_path="", workdir=""):
            raise RuntimeError("timeout with no diagnostics")

        with unittest.mock.patch.object(sim_frm, "co_sim", side_effect=crash):
            killed, detail = sim_kill("m.v", self.tmp)
        self.assertFalse(killed)
        self.assertTrue(detail.startswith("INFRA:"))
        def lint(path):
            return True, ""

        def sim(stim):
            return {"match": True, "first_diverge": -1, "frm": "", "rtl": ""}

        r1 = campaign(_cat(2, self.src), workdir=self.tmp, lint_fn=lint, sim_fn=sim)
        r2 = campaign(_cat(2, self.src), workdir=self.tmp, lint_fn=lint, sim_fn=sim,
                      resume=True)
        self.assertEqual(r2["M001"], r1["M001"])
        self.assertIn("M002", r2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
