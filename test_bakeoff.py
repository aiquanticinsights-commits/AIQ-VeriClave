"""Unit tests for the P0-B bake-off harness (deterministic, no models).

All lint calls are injected fakes — real Verilator runs happen only in the
live bake-off on the Windows dev machine (Verilator via WSL).
"""
import unittest

from bakeoff import (SLATE, TASKS, extract_fence, grade_mc, grade_req_ids,
                     grade_sva, grade_width_fix, select_winner, summarize)


def fake_clean(_verilog, wall=False):
    return True, ""


def fake_width_warn(_verilog, wall=False):
    return True, "%Warning-WIDTH: literal too wide"


def fake_error(_verilog, wall=False):
    return False, "%Error: syntax error"


class TestExtract(unittest.TestCase):
    def test_fence_preferred(self):
        t = "noise\n```systemverilog\nassert p;\n```\ntail"
        self.assertEqual(extract_fence(t), "assert p;")

    def test_bare_text_fallback(self):
        self.assertEqual(extract_fence("  assert p;  "), "assert p;")


class TestGraders(unittest.TestCase):
    def test_mc_first_letter_wins(self):
        self.assertTrue(grade_mc("Analysis...\nB", "B"))
        self.assertFalse(grade_mc("A because ... B mentioned", "B"))

    def test_req_ids_need_three_distinct(self):
        self.assertTrue(grade_req_ids("REQ-001 a\nREQ-002 b\nREQ-003 c"))
        self.assertFalse(grade_req_ids("REQ-001 a\nREQ-001 b\nREQ-002 c"))

    def test_sva_needs_assert_and_clean_lint(self):
        good = "```systemverilog\nproperty p; @(posedge clk) a |-> ##[0:2] b; endproperty\nassert property(p);\n```"
        self.assertTrue(grade_sva(good, "input wire clk", lint=fake_clean))
        self.assertFalse(grade_sva(good, "input wire clk", lint=fake_error))
        self.assertFalse(grade_sva("```\nassign x = 1;\n```", "input wire clk",
                                   lint=fake_clean))

    def test_width_fix_gates(self):
        fixed = "```verilog\nmodule m(input wire [3:0] a, output wire [3:0] y);\nassign y = 4'b1111;\nendmodule\n```"
        self.assertTrue(grade_width_fix(fixed, lint=fake_clean))
        self.assertFalse(grade_width_fix(fixed, lint=fake_width_warn))
        buggy = fixed.replace("4'b1111", "4'b11111")
        self.assertFalse(grade_width_fix(buggy, lint=fake_clean))

    def test_task_set_covers_kinds(self):
        kinds = {t["kind"] for t in TASKS}
        self.assertEqual(kinds, {"sva-validity", "localization", "coverage",
                                 "mutant-kill"})
        self.assertEqual(len(TASKS), 6)


class TestSelection(unittest.TestCase):
    def _s(self, model, rate, lat, tok):
        return {"model": model, "loaded": True, "skip_reason": "",
                "pass_rate": rate, "by_kind": {}, "avg_latency_s": lat,
                "total_tokens": tok, "tasks": []}

    def test_correctness_first(self):
        ss = [self._s("a", 0.5, 1.0, 10), self._s("b", 0.83, 99.0, 999)]
        self.assertEqual(select_winner(ss), "b")

    def test_latency_breaks_ties(self):
        ss = [self._s("a", 0.8, 50.0, 10), self._s("b", 0.8, 5.0, 9999)]
        self.assertEqual(select_winner(ss), "b")

    def test_skipped_never_win(self):
        ss = [self._s("a", 0.0, -1.0, 0),
              {"model": "gone", "loaded": False, "skip_reason": "no RAM",
               "pass_rate": 0.0, "by_kind": {}, "avg_latency_s": -1.0,
               "total_tokens": 0, "tasks": []}]
        self.assertEqual(select_winner(ss), "a")

    def test_nobody_loaded_raises(self):
        with self.assertRaises(RuntimeError):
            select_winner([{"model": "x", "loaded": False, "skip_reason": "r",
                            "pass_rate": 0.0, "by_kind": {},
                            "avg_latency_s": -1.0, "total_tokens": 0,
                            "tasks": []}])

    def test_summarize_shape(self):
        res = {"loaded": True, "skip_reason": "",
               "tasks": [{"task": "T1", "kind": "sva-validity", "pass": True,
                          "latency_s": 2.0, "prompt_tokens": 10,
                          "completion_tokens": 5, "output_chars": 40}]}
        s = summarize("m", res)
        self.assertEqual(s["pass_rate"], 1.0)
        self.assertEqual(s["by_kind"]["sva-validity"]["pass_rate"], 1.0)

    def test_slate_names_match_router_registry(self):
        from router import BAKEOFF_CANDIDATES
        for _, name in SLATE:
            self.assertIn(name, BAKEOFF_CANDIDATES)


if __name__ == "__main__":
    unittest.main(verbosity=2)
