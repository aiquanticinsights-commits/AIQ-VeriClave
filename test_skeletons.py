"""Unit tests for constrained generation (pure — no models, no Verilator)."""
import unittest

from skeletons import (SKELETONS, WIDTH_FRAMES, assemble, clean_slot,
                       constrained_prompt, extract_assign_line, parse_int_slot,
                       parse_slots)


class TestSlots(unittest.TestCase):
    def test_parse_all_labels(self):
        t = ("ANTECEDENT: s_wb_stb\nLOW: 1\nHIGH: 2\n"
             "CONSEQUENT: s_wb_ack")
        s = parse_slots(t, ("ANTECEDENT", "LOW", "HIGH", "CONSEQUENT"))
        self.assertEqual(s["LOW"], "1")

    def test_missing_label_rejected(self):
        self.assertIsNone(parse_slots("ANTECEDENT: x", ("ANTECEDENT", "LOW")))

    def test_underscore_labels(self):
        s = parse_slots("PAST_EXPR: a\nNOW_EXPR: b",
                        ("PAST_EXPR", "NOW_EXPR"))
        self.assertEqual(s, {"PAST_EXPR": "a", "NOW_EXPR": "b"})

    def test_smuggling_rejected(self):
        self.assertIsNone(clean_slot("a; assert property(p)"))
        self.assertIsNone(clean_slot("`define X"))
        self.assertIsNone(clean_slot("always @(posedge clk)"))
        self.assertIsNone(clean_slot("x" * 65))
        self.assertEqual(clean_slot("s_wb_stb & ~s_wb_ack"), "s_wb_stb & ~s_wb_ack")

    def test_sampled_value_functions_allowed(self):
        # Measured P0-D skeleton v1: rejecting $rose/$fell rejects correct SVA.
        self.assertEqual(clean_slot("$fell(s_wb_stb)"), "$fell(s_wb_stb)")
        self.assertEqual(clean_slot("$rose(s_wb_ack)"), "$rose(s_wb_ack)")

    def test_system_tasks_still_banned(self):
        self.assertIsNone(clean_slot("$display(x)"))
        self.assertIsNone(clean_slot("$finish"))
        self.assertIsNone(clean_slot("$readmemb(f)"))

    def test_int_slots(self):
        self.assertEqual(parse_int_slot("2"), "2")
        self.assertIsNone(parse_int_slot("-1"))
        self.assertIsNone(parse_int_slot("abc"))


class TestAssembleSVA(unittest.TestCase):
    def test_t1_past_form_ok(self):
        t = "PAST_EXPR: s_wb_cyc && s_wb_stb\nNOW_EXPR: s_wb_ack"
        a = assemble("T1-sva-ack", t)
        self.assertIn("$past(s_wb_cyc && s_wb_stb)", a)
        self.assertIn("assert(s_wb_ack", a)

    def test_t1_mention_gate(self):
        # Slots must mention the requirement's signals (traceability gate).
        t = "PAST_EXPR: foo\nNOW_EXPR: s_wb_ack"
        self.assertIsNone(assemble("T1-sva-ack", t))
        t2 = "PAST_EXPR: s_wb_stb\nNOW_EXPR: bar"
        self.assertIsNone(assemble("T1-sva-ack", t2))

    def test_t2_simple_ok(self):
        a = assemble("T2-sva-irq", "ANTECEDENT: irq\nCONSEQUENT: irq_en")
        self.assertIn("|-> irq_en", a)
        self.assertNotIn("##[", a)

    def test_free_text_rejected(self):
        self.assertIsNone(assemble("T1-sva-ack", "the assertion should hold"))

    def test_unknown_task_none(self):
        self.assertIsNone(assemble("T3-localize-bus", "B"))


class TestAssembleWidth(unittest.TestCase):
    def test_t6_line_ok(self):
        a = assemble("T6-width-fix", "assign y = 4'b1111;")
        self.assertIn("4'b1111", a)
        self.assertNotIn("4'b11111", a)

    def test_t6_buggy_rejected(self):
        self.assertIsNone(assemble("T6-width-fix", "assign y = 4'b11111;"))

    def test_t6_bare_expr_promoted(self):
        a = assemble("T6-width-fix", "4'b1111")
        self.assertIn("assign y = 4'b1111;", a)

    def test_t9_expr_ok(self):
        a = assemble("T9-status-fix", "3'b000")
        self.assertIn("status <= 3'b000;", a)

    def test_t9_buggy_rejected(self):
        self.assertIsNone(assemble("T9-status-fix", "4'b1000"))

    def test_t9_full_module_harvested(self):
        t = ("```verilog\nmodule s(input wire clk, output reg [2:0] status);\n"
             "always @(posedge clk) status <= 3'b000;\nendmodule\n```")
        a = assemble("T9-status-fix", t)
        self.assertIn("3'b000", a)

    def test_extract_assign(self):
        self.assertEqual(extract_assign_line("noise\nassign y = 4'b1111;\ntail"),
                         "assign y = 4'b1111;")
        self.assertIsNone(extract_assign_line("no statements here"))

    def test_backticked_assign_accepted(self):
        # Measured: models wrap the line in markdown inline code.
        self.assertEqual(extract_assign_line("`assign y = 4'b1111;`"),
                         "assign y = 4'b1111;")
        a = assemble("T6-width-fix", "here:\n`assign y = 4'b1111;`\ndone")
        self.assertIn("4'b1111", a)


class TestPrompts(unittest.TestCase):
    def test_skeleton_tasks_covered(self):
        for tid in ("T1-sva-ack", "T2-sva-irq", "T7-sva-cyc",
                    "T6-width-fix", "T9-status-fix"):
            p = constrained_prompt(tid, "FALLBACK")
            self.assertNotEqual(p, "FALLBACK")

    def test_non_skeleton_falls_back(self):
        self.assertEqual(constrained_prompt("T3-localize-bus", "FALLBACK"),
                         "FALLBACK")

    def test_specs_complete(self):
        for tid in ("T1-sva-ack", "T2-sva-irq", "T7-sva-cyc"):
            self.assertIn(tid, SKELETONS)
        for tid in ("T6-width-fix", "T9-status-fix"):
            self.assertIn(tid, WIDTH_FRAMES)


if __name__ == "__main__":
    unittest.main(verbosity=2)
