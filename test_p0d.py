"""Unit tests for the P0-D loop (fake backends — no models, no Verilator)."""
import unittest

from evidence import EvidenceLedger
from p0d import (ABLATION_SUBSET, ABLATION_WIDTHS, SUITE, closure_prompt,
                 failure_log, ledger_for, run_one, summarize, verify_output)


def good_output(task):
    tid = task["id"]
    if tid in ("T1-sva-ack", "T2-sva-irq", "T7-sva-cyc"):
        return "```systemverilog\nassert property (@(posedge clk) 1'b1);\n```"
    if tid in ("T3-localize-bus", "T8-localize-irq"):
        return "B"
    if tid == "T4-classify-reset":
        return "C"
    if tid == "T5-req-ids":
        return "REQ-001 a\nREQ-002 b\nREQ-003 c"
    if tid == "T6-width-fix":
        return ("```verilog\nmodule m(input wire [3:0] a, output wire [3:0] y);"
                "\nassign y = 4'b1111;\nendmodule\n```")
    if tid == "T9-status-fix":
        return ("```verilog\nmodule s(input wire clk, output reg [2:0] status);"
                "\nalways @(posedge clk) status <= 3'b000;\nendmodule\n```")
    return "nope"


def fake_clean(_verilog, wall=False):
    return True, ""


class TestSuite(unittest.TestCase):
    def test_suite_shape(self):
        self.assertEqual(len(SUITE), 9)
        self.assertEqual({t["kind"] for t in SUITE},
                         {"sva-validity", "localization", "coverage",
                          "mutant-kill"})
        for tid in ABLATION_SUBSET:
            self.assertIn(tid, {t["id"] for t in SUITE})
        self.assertEqual(ABLATION_WIDTHS, (1, 3, 5))


class TestVerify(unittest.TestCase):
    def test_good_outputs_pass(self):
        for t in SUITE:
            with self.subTest(t=t["id"]):
                v = verify_output(t, good_output(t), lint_fn=fake_clean)
                self.assertTrue(all(v.values()), t["id"])

    def test_garbage_fails_graded_checks(self):
        for t in SUITE:
            with self.subTest(t=t["id"]):
                v = verify_output(t, "hello world no content here",
                                  lint_fn=fake_clean)
                self.assertFalse(all(v.values()), t["id"])

    def test_unknown_task_rejected(self):
        with self.assertRaises(ValueError):
            verify_output({"id": "TX"}, "x")

    def test_closure_prompt_names_failure(self):
        t = SUITE[0]
        p = closure_prompt(t, "failed checks: syntax")
        self.assertIn("failed checks: syntax", p)
        self.assertIn(t["prompt"], p)

    def test_failure_log(self):
        self.assertEqual(failure_log({"a": True, "b": False}),
                         "failed checks: b")


class TestLoop(unittest.TestCase):
    def _query(self, text):
        def q(model, prompt, max_tokens):
            return text, {"prompt_tokens": 1, "completion_tokens": 1}, 0.1
        return q

    def test_all_good_closes_fast(self):
        r = run_one(SUITE[2], 3, query_fn=self._query("B"))
        self.assertEqual(r["winner"], "llama-3.1-8b")
        self.assertFalse(r["escalated_to_human"])
        self.assertLessEqual(r["rounds"], 3)

    def test_all_bad_escalates_at_boundary(self):
        r = run_one(SUITE[0], 3, query_fn=self._query("garbage"))
        self.assertIsNone(r["winner"])
        self.assertEqual(r["rounds"], 3)
        self.assertTrue(r["escalated_to_human"])

    def test_closure_recovers(self):
        calls = []

        def q(model, prompt, max_tokens):
            calls.append(prompt)
            if len(calls) <= 2:
                return "garbage", {}, 0.1
            return "B", {}, 0.1

        r = run_one(SUITE[2], 1, query_fn=q)
        self.assertEqual(r["winner"], "llama-3.1-8b")
        self.assertGreaterEqual(r["rounds"], 2)
        self.assertTrue(any("FAILED" in p for p in calls[1:]))

    def test_ledger_records_both_outcomes(self):
        ok = run_one(SUITE[2], 1, query_fn=self._query("B"))
        bad = run_one(SUITE[0], 1, query_fn=self._query("garbage"))
        ledger = ledger_for([ok, bad], "test-run")
        self.assertTrue(ledger.verify_chain())
        self.assertAlmostEqual(ledger.audit_completeness(), 1.0)
        verdicts = {r.verdict for r in ledger.records}
        self.assertIn("PASS", verdicts)
        self.assertIn("NOT_EXECUTED", verdicts)

    def test_summarize_math(self):
        rows = [{"winner": "m", "rounds": 2, "history": [],
                 "total_latency_s": 10.0, "total_tokens": 100,
                 "est_cost_usd": 0.001},
                {"winner": None, "rounds": 3, "history": [],
                 "total_latency_s": 20.0, "total_tokens": 200,
                 "est_cost_usd": 0.002}]
        for r in rows:
            r["escalated_to_human"] = r["winner"] is None
        s = summarize(rows)
        self.assertEqual(s["tasks"], 2)
        self.assertEqual(s["closed"], 1)
        self.assertEqual(s["system_accuracy"], 0.5)
        self.assertEqual(s["max_closure_iterations"], 3)
        self.assertEqual(s["escalated_to_human"], 1)
        self.assertEqual(s["total_latency_s"], 30.0)
        self.assertEqual(s["total_tokens"], 300)
        self.assertAlmostEqual(s["total_cost_usd"], 0.003)
        self.assertAlmostEqual(s["avg_cost_per_task_usd"], 0.0015)

    def test_run_one_instruments_efficiency(self):
        def q(model, prompt, max_tokens):
            return "B", {"prompt_tokens": 100, "completion_tokens": 50}, 2.5

        r = run_one(SUITE[2], 1, query_fn=q)
        self.assertEqual(r["winner"], "llama-3.1-8b")
        # 2 rounds x 1 candidate x (100+50 tokens, 2.5s)
        self.assertEqual(r["total_tokens"], 300)
        self.assertEqual(r["total_latency_s"], 5.0)
        self.assertGreater(r["est_cost_usd"], 0.0)

    def test_run_one_counts_misses(self):
        def q(model, prompt, max_tokens):
            return "garbage", {}, 1.0

        r = run_one(SUITE[0], 1, query_fn=q)
        self.assertIsNone(r["winner"])
        self.assertEqual(r["total_latency_s"], 3.0)  # 3 rounds counted
        self.assertEqual(r["total_tokens"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
