"""Unit tests for the repair-closure ablation (fakes only, no models)."""
import unittest

from repair import (REPAIR_TASKS, closure_prompt, extract_decl, literal_values,
                    run_task, task_prompt, value_gate, verify)

GOOD_R1 = ("```verilog\nmodule r1(input wire [3:0] a, output wire [3:0] y);\n"
           "wire [3:0] b;\nassign y = a & b;\nendmodule\n```")


def fake_clean(_v, wall=False):
    return True, ""


def fake_broken(_v, wall=False):
    return False, "%Error-UNDECLARED: x.sv:2:1: Undeclared identifier 'b'"


class TestVerify(unittest.TestCase):
    def test_good_passes(self):
        t = REPAIR_TASKS[0]
        v, _ = verify(t, GOOD_R1, lint_fn=fake_clean)
        self.assertTrue(all(v.values()))

    def test_gates_catch_wrong_fix(self):
        t = REPAIR_TASKS[0]
        bad = GOOD_R1.replace("[3:0] b", "[7:0] b")
        v, _ = verify(t, bad, lint_fn=fake_clean)
        self.assertFalse(v["fix"])
        self.assertTrue(v["syntax"])

    def test_no_module_fails(self):
        t = REPAIR_TASKS[0]
        v, _ = verify(t, "just prose", lint_fn=fake_clean)
        self.assertFalse(any(v.values()))

    def test_tasks_have_gates(self):
        for t in REPAIR_TASKS:
            self.assertIn("must_contain", t)
            self.assertIn("buggy", t)

    def test_line_mode(self):
        t = next(x for x in REPAIR_TASKS if x["id"] == "R2-width")
        self.assertIn("ONLY the corrected assign line", task_prompt(t))
        v, _ = verify(t, "assign q = 8'b00000001;", lint_fn=fake_clean)
        self.assertTrue(all(v.values()))
        v2, _ = verify(t, "assign q = 9'b100000001;", lint_fn=fake_clean)
        self.assertFalse(any(v2.values()))
        v3, _ = verify(t, "free prose", lint_fn=fake_clean)
        self.assertFalse(any(v3.values()))

    def test_declline_mode(self):
        t = next(x for x in REPAIR_TASKS if x["id"] == "R5-double")
        self.assertIn("EXACTLY two lines", task_prompt(t))
        good = "DECL: wire [3:0] c;\nASSIGN: assign y = a + c + 4'b1111;"
        v, _ = verify(t, good, lint_fn=fake_clean)
        self.assertTrue(all(v.values()))
        bad_iface = ("DECL: input wire [3:0] c;\n"
                     "ASSIGN: assign y = a + c + 4'b1111;")
        v2, _ = verify(t, bad_iface, lint_fn=fake_clean)
        self.assertFalse(any(v2.values()))
        self.assertIsNone(extract_decl("no wires here"))
        self.assertEqual(extract_decl("`wire [3:0] c;`"), "wire [3:0] c;")

    def test_free_tasks_ask_full_module(self):
        t = next(x for x in REPAIR_TASKS if x["id"] == "R1-undeclared")
        self.assertIn("full module", task_prompt(t))


class TestValueGate(unittest.TestCase):
    def test_literals(self):
        self.assertEqual(literal_values("assign y = 4'b1111;"), [(4, 15)])
        self.assertEqual(literal_values("x = 8'd15 + 1;"),
                         [(8, 15), (None, 1)])
        self.assertEqual(literal_values("no numbers here"), [])

    def test_value_truth(self):
        self.assertTrue(value_gate("assign y = a + c + 8'd15;",
                                   15, "4'b11111"))
        self.assertTrue(value_gate("assign q = 8'b00000001;",
                                   1, "9'b100000001"))
        self.assertFalse(value_gate("assign q = 8'b10000000;",
                                    1, "9'b100000001"))  # wrong value
        self.assertFalse(value_gate("assign q = 9'b100000001;",
                                    1, "9'b100000001"))  # bug present
        # Equivalent forms accepted: value truth, not text identity.
        self.assertTrue(value_gate("assign q = 16'h1;",
                                   1, "9'b100000001"))
        self.assertTrue(value_gate("assign q = 4'b0001;",
                                   1, "9'b100000001"))


class TestPrompts(unittest.TestCase):
    def test_arm_a_has_no_tool_output(self):
        p = closure_prompt(REPAIR_TASKS[0], "failed checks: syntax", "A",
                           "%Error-X")
        self.assertNotIn("Tool output", p)
        self.assertIn("failed checks: syntax", p)

    def test_arm_b_carries_suspects(self):
        p = closure_prompt(REPAIR_TASKS[0], "failed checks: syntax", "B",
                           "%Error-UNDECLARED: x.sv:2:1: Undeclared 'b'")
        self.assertIn("Tool output", p)
        self.assertIn("rank 1 first", p)
        self.assertIn("x.sv:2", p)

    def test_arm_b_empty_log_like_a(self):
        p = closure_prompt(REPAIR_TASKS[0], "failed checks: syntax", "B", "")
        self.assertNotIn("Tool output", p)


class TestLoop(unittest.TestCase):
    def _q(self, texts):
        def q(model, prompt, max_tokens):
            i = len(self.calls)
            self.calls.append(prompt)
            return texts[min(i, len(texts) - 1)], {}, 0.1
        self.calls = []
        return q

    def test_good_closes(self):
        r = run_task(REPAIR_TASKS[0], "A",
                     query_fn=self._q([GOOD_R1]), lint_fn=fake_clean)
        self.assertTrue(r["closed"])
        self.assertEqual(r["arm"], "A")

    def test_bad_escalates(self):
        r = run_task(REPAIR_TASKS[0], "B",
                     query_fn=self._q(["garbage"]), lint_fn=fake_clean)
        self.assertFalse(r["closed"])
        self.assertTrue(r["escalated_to_human"])
        self.assertEqual(r["rounds"], 3)

    def test_closure_recovers_with_hint(self):
        r = run_task(REPAIR_TASKS[0], "B",
                     query_fn=self._q(["garbage", GOOD_R1]),
                     lint_fn=fake_clean)
        self.assertTrue(r["closed"])
        self.assertGreaterEqual(r["rounds"], 2)

    def test_arm_b_prompts_carry_diagnostics(self):
        run_task(REPAIR_TASKS[0], "B",
                 query_fn=self._q(["garbage"]), lint_fn=fake_broken)
        # round-1 output has no module -> no lint detail; check names only
        self.assertTrue(any("failed checks" in p for p in self.calls[1:]))

    def test_no_fourth_round_ever(self):
        # Hard closure-controller invariant (frozen §11, our 3-round form):
        # all-FAIL forever -> exactly MAX_ROUNDS generations, escalation,
        # and NO fourth round under any circumstance.
        from repair import MAX_ROUNDS
        calls = []

        def q(model, prompt, max_tokens):
            calls.append(prompt)
            return "garbage", {}, 0.1

        r = run_task(REPAIR_TASKS[0], "B", query_fn=q,
                     lint_fn=lambda v, wall=False: (False, "e"))
        self.assertEqual(r["rounds"], MAX_ROUNDS)
        self.assertEqual(len(calls), MAX_ROUNDS)  # width=1: 1 call/round
        self.assertTrue(r["escalated_to_human"])
        self.assertFalse(r["closed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
