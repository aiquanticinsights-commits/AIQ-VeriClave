"""Unit tests for the P0-D loop (fake backends — no models, no Verilator)."""
import unittest

from evidence import EvidenceLedger
from p0d import (ABLATION_SUBSET, ABLATION_WIDTHS, SUITE, base_prompt,
                 closure_prompt, failure_log, is_skeleton_task, ledger_for,
                 run_one, summarize, verify_output)


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

    def test_closure_prompt_carries_tool_detail(self):
        t = SUITE[0]
        p = closure_prompt(t, "failed checks: syntax",
                           "%Error-UNSUPPORTED: ## range")
        self.assertIn("%Error-UNSUPPORTED: ## range", p)

    def test_diagnose_extracts_tool_lines(self):
        def fake(mod, wall=False):
            return False, "%Error-UNSUPPORTED: ## range\nnoise line"
        from p0d import diagnose
        d = diagnose({"id": "T1-sva-ack"}, "module m;\nendmodule\n",
                     lint_fn=fake)
        self.assertIn("%Error-UNSUPPORTED", d)
        self.assertNotIn("noise line", d)

    def test_diagnose_quiet_cases(self):
        from p0d import diagnose
        self.assertEqual(diagnose({"id": "T1"}, "no module here",
                                  lint_fn=fake_clean), "")
        self.assertEqual(diagnose({"id": "T1"}, "module m;\nendmodule\n",
                                  lint_fn=fake_clean), "")

    def test_closure_receives_fault_hint(self):
        # The fault-hinted closure contract: round-2+ prompts carry the
        # previous candidate's tool diagnostics, not just check names.
        seen = []

        def q(model, prompt, max_tokens):
            seen.append(prompt)
            return ("ANTECEDENT: irq\nCONSEQUENT: irq_en", {}, 0.1)

        def fake(mod, wall=False):
            return False, "%Error-FAKE: something broke"

        t = next(x for x in SUITE if x["id"] == "T2-sva-irq")
        r = run_one(t, 1, query_fn=q, lint_fn=fake, constrained=True)
        self.assertTrue(r["escalated_to_human"])  # lint always fails here
        self.assertTrue(any("Tool output" in p for p in seen[1:]))
        self.assertTrue(any("%Error-FAKE" in p for p in seen[1:]))

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
        self.assertEqual(r["artifact"], "B")

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

    def test_elitism_preserves_round1_winner(self):
        # T2/T7 backfire regression: good round 1, garbage regen after.
        # Incumbent must survive; carrying costs zero extra calls.
        calls = []

        def q(model, prompt, max_tokens):
            calls.append(prompt)
            if len(calls) <= 2:
                return "C", {}, 0.1  # SUITE[3]=T4: ranked True, approvals 2
            return "garbage", {}, 0.1

        r = run_one(SUITE[3], 2, query_fn=q)
        self.assertEqual(r["winner"], "llama-3.1-8b")
        self.assertTrue(r["closed"])
        self.assertFalse(r["escalated_to_human"])
        self.assertEqual(r["rounds"], 2)
        self.assertEqual(len(calls), 4)  # width x rounds; incumbent is free

    def test_weak_plurality_escalates(self):
        # Approvals never reach 2: full budget runs, then escalation —
        # weak closes are recorded as gaps, never as passes.
        def q(model, prompt, max_tokens):
            return "A", {}, 0.1  # T3 expects B: ranked False, approvals 1

        r = run_one(SUITE[2], 2, query_fn=q)
        self.assertEqual(r["rounds"], 3)
        self.assertFalse(r["closed"])
        self.assertTrue(r["escalated_to_human"])


class TestSkeletonPath(unittest.TestCase):
    def _query(self, text):
        def q(model, prompt, max_tokens):
            return text, {"prompt_tokens": 1, "completion_tokens": 1}, 0.1
        return q

    def test_is_skeleton_task(self):
        for tid in ("T1-sva-ack", "T2-sva-irq", "T7-sva-cyc",
                    "T6-width-fix", "T9-status-fix"):
            self.assertTrue(is_skeleton_task(tid))
        self.assertFalse(is_skeleton_task("T3-localize-bus"))

    def test_base_prompt(self):
        t = next(x for x in SUITE if x["id"] == "T1-sva-ack")
        self.assertIn("PAST_EXPR", base_prompt(t, True))
        self.assertEqual(base_prompt(t, False), t["prompt"])

    def test_skeleton_slots_close(self):
        t = next(x for x in SUITE if x["id"] == "T2-sva-irq")
        slots = "ANTECEDENT: irq\nCONSEQUENT: irq_en"

        def q(model, prompt, max_tokens):
            self.assertIn("ANTECEDENT", prompt)  # skeleton prompt used
            return slots, {}, 0.1

        r = run_one(t, 1, query_fn=q, lint_fn=fake_clean, constrained=True,
                    formal_fn=lambda p: True)
        self.assertTrue(r["closed"])
        self.assertFalse(r["escalated_to_human"])

    def test_formal_true_false_none(self):
        t = next(x for x in SUITE if x["id"] == "T1-sva-ack")
        self.assertEqual(t.get("judge_on"), ("formal",))
        slots = "PAST_EXPR: s_wb_cyc && s_wb_stb\nNOW_EXPR: s_wb_ack"

        def q(model, prompt, max_tokens):
            return slots, {}, 0.1

        r = run_one(t, 1, query_fn=q, lint_fn=fake_clean, constrained=True,
                    formal_fn=lambda p: True)
        self.assertTrue(r["closed"])
        r2 = run_one(t, 1, query_fn=q, lint_fn=fake_clean, constrained=True,
                     formal_fn=lambda p: False)
        self.assertFalse(r2["closed"])
        self.assertTrue(r2["escalated_to_human"])
        # None (tool down / bounded-unknown) fails CLOSED: escalates, no pass
        r3 = run_one(t, 1, query_fn=q, lint_fn=fake_clean, constrained=True,
                     formal_fn=lambda p: None)
        self.assertFalse(r3["closed"])
        self.assertTrue(r3["escalated_to_human"])

    def test_skeleton_reject_escalates(self):
        t = next(x for x in SUITE if x["id"] == "T1-sva-ack")

        def q(model, prompt, max_tokens):
            return "free prose, no slots", {}, 0.1

        r = run_one(t, 1, query_fn=q, lint_fn=fake_clean, constrained=True)
        self.assertFalse(r["closed"])
        self.assertTrue(r["escalated_to_human"])

    def test_skeleton_width_fix_closes(self):
        t = next(x for x in SUITE if x["id"] == "T6-width-fix")

        def q(model, prompt, max_tokens):
            return "assign y = 4'b1111;", {}, 0.1

        r = run_one(t, 1, query_fn=q, lint_fn=fake_clean, constrained=True)
        self.assertTrue(r["closed"])

    def test_constrained_leaves_free_tasks_alone(self):
        t = next(x for x in SUITE if x["id"] == "T3-localize-bus")

        def q(model, prompt, max_tokens):
            self.assertNotIn("ANTECEDENT", prompt)
            return "B", {}, 0.1

        r = run_one(t, 1, query_fn=q, lint_fn=fake_clean, constrained=True)
        self.assertTrue(r["closed"])

    def test_preassembled_module_not_rewrapped(self):
        # Regression (skeleton v2): assembled modules linted as-is — a
        # second module wrapper is a harness-authored syntax error.
        # (T2: non-formal skeleton task, so the lint path is exercised.)
        seen = []

        def fake(mod, wall=False):
            seen.append(mod)
            return True, ""

        mod = ("module tb_sva(input wire clk);\n"
               "assert property (@(posedge clk) 1'b1);\nendmodule\n")
        t = next(x for x in SUITE if x["id"] == "T2-sva-irq")
        v = verify_output(t, mod, lint_fn=fake, preassembled=True)
        self.assertTrue(all(v.values()))
        self.assertEqual(seen[0].count("module tb_sva"), 1)

    def test_preassembled_width_gates(self):
        t = next(x for x in SUITE if x["id"] == "T6-width-fix")
        good = ("module m(input wire [3:0] a, output wire [3:0] y);\n"
                "assign y = 4'b1111;\nendmodule\n")
        v = verify_output(t, good, lint_fn=fake_clean, preassembled=True)
        self.assertTrue(all(v.values()))
        bad = good.replace("4'b1111", "4'b11111")
        v2 = verify_output(t, bad, lint_fn=fake_clean, preassembled=True)
        self.assertFalse(v2["kill"])
        self.assertFalse(all(v2.values()))

    def test_vacuous_sva_escalates(self):
        # Reviewer SSB's T2 catch as a regression test: the exact vacuous
        # artifact must fail judging (3-key bar) and escalate, never close.
        t = next(x for x in SUITE if x["id"] == "T2-sva-irq")
        self.assertEqual(t.get("judge_on"),
                         ("syntax", "proof_shape", "vacuity"))
        vacuous = ("module tb_sva(input wire clk, input wire irq, "
                   "input wire irq_en);\nproperty p_sva_irq;\n"
                   "  @(posedge clk) $rose(irq) && !irq |-> $past(irq_en)"
                   " == 1'b1;\nendproperty\n"
                   "assert property (p_sva_irq);\nendmodule\n")

        def q(model, prompt, max_tokens):
            return ("ANTECEDENT: $rose(irq) && !irq\nCONSEQUENT: irq_en",
                    {}, 0.1)

        v = verify_output(t, vacuous, lint_fn=fake_clean, preassembled=True)
        self.assertTrue(v["syntax"])
        self.assertFalse(v["proof_shape"])
        self.assertFalse(v["vacuity"])
        r = run_one(t, 1, query_fn=q, lint_fn=fake_clean, constrained=True)
        self.assertFalse(r["closed"])
        self.assertTrue(r["escalated_to_human"])

    def test_clean_sva_still_closes(self):
        t = next(x for x in SUITE if x["id"] == "T2-sva-irq")
        clean = ("module tb_sva(input wire clk, input wire irq, "
                 "input wire irq_en);\nproperty p_sva_irq;\n"
                 "  @(posedge clk) irq |-> irq_en;\nendproperty\n"
                 "assert property (p_sva_irq);\nendmodule\n")

        def q(model, prompt, max_tokens):
            return "ANTECEDENT: irq\nCONSEQUENT: irq_en", {}, 0.1

        v = verify_output(t, clean, lint_fn=fake_clean, preassembled=True)
        self.assertTrue(all(v.values()))
        r = run_one(t, 1, query_fn=q, lint_fn=fake_clean, constrained=True)
        self.assertTrue(r["closed"])

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

    def test_query_exception_does_not_crash_loop(self):
        def q(model, prompt, max_tokens):
            raise ConnectionError("server down")

        r = run_one(SUITE[2], 1, query_fn=q)
        self.assertEqual(r["rounds"], 3)
        self.assertFalse(r["closed"])
        self.assertTrue(r["escalated_to_human"])
        self.assertEqual(r["query_errors"], 3)  # every call faulted, all counted


if __name__ == "__main__":
    unittest.main(verbosity=2)
