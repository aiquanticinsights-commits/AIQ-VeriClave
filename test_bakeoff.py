"""Unit tests for the P0-B bake-off harness (deterministic, no models).

Lint calls are injected fakes except TestLiveLint, which runs the real
Verilator locally (native on Linux CI, via WSL on Windows) and skips when
no Verilator is reachable.
"""
import shutil
import unittest
import unittest.mock

from bakeoff import (SLATE, TASKS, TASKS_V2, default_lint, extract_fence,
                     grade_mc, grade_req_ids, grade_sva, grade_width,
                     grade_width_fix, select_winner, summarize)


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


class TestServerReady(unittest.TestCase):
    def test_ready_true(self):
        from bakeoff import server_ready
        import urllib.request

        class Resp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        with unittest.mock.patch.object(urllib.request, "urlopen",
                                        return_value=Resp()):
            self.assertTrue(server_ready())

    def test_ready_false(self):
        from bakeoff import require_server, server_ready
        import urllib.request
        with unittest.mock.patch.object(
                urllib.request, "urlopen",
                side_effect=ConnectionError("down")):
            self.assertFalse(server_ready())
            self.assertFalse(require_server())


class TestV2Bank(unittest.TestCase):
    def test_shape(self):
        self.assertEqual(len(TASKS_V2), 40)
        kinds = [t["kind"] for t in TASKS_V2]
        for k in ("mutant-kill", "sva-validity", "localization", "coverage"):
            self.assertEqual(kinds.count(k), 10)
        self.assertEqual(len({t["id"] for t in TASKS_V2}), 40)
        for t in TASKS_V2:
            self.assertIn("grade", t)
            self.assertTrue(callable(t["grade"]))
            self.assertIn("prompt", t)

    def test_mcq_answers_in_options(self):
        for t in TASKS_V2:
            if t["kind"] == "localization":
                self.assertIn(t["expected"], ("A", "B", "C", "D"))
                self.assertIn(t["expected"], t["prompt"])

    def test_width_control(self):
        ctrls = [t for t in TASKS_V2
                 if t.get("bad") is not None and t.get("bad") == t.get("good")]
        self.assertEqual(len(ctrls), 1)  # exactly one golden control
        good = ("```verilog\nmodule w9(input wire [2:0] a, output wire [2:0] k);\n"
                "assign k = 3'b000;\nendmodule\n```")
        self.assertTrue(ctrls[0]["grade"](good, ))

    def test_grade_width_gates(self):
        from bakeoff import grade_width as gw
        good = ("```verilog\nmodule w0(input wire [3:0] a, output wire [3:0] y);\n"
                "assign y = 4'b1111;\nendmodule\n```")
        self.assertTrue(gw(good, "4'b11111", "4'b1111",
                           lint=lambda v, wall=False: (True, "")))
        self.assertFalse(gw(good.replace("4'b1111", "4'b11111"),
                            "4'b11111", "4'b1111",
                            lint=lambda v, wall=False: (True, "")))


def _have_verilator():
    import os
    if os.name == "nt":
        return shutil.which("wsl") is not None
    return shutil.which("verilator") is not None


@unittest.skipUnless(_have_verilator(), "needs reachable Verilator")
class TestLiveLint(unittest.TestCase):
    def test_clean_module_passes(self):
        ok, _ = default_lint("module t(input wire a, output wire y);\n"
                             "assign y = a;\nendmodule\n")
        self.assertTrue(ok)

    def test_syntax_error_fails(self):
        ok, log = default_lint("module t(input wire a;\nendmodule\n")
        self.assertFalse(ok)
        self.assertIn("%Error", log)

    def test_warnings_only_still_pass(self):
        # Regression (P0-D skeleton v1): the synthetic
        # "%Error: Exiting due to N warning(s)" line must not fail an
        # otherwise-clean artifact; DECLFILENAME is killed by module-named
        # temp files, UNUSEDSIGNAL is warning-only here.
        ok, _ = default_lint("module t(input wire [3:0] a, output wire [3:0] y);\n"
                             "assign y = a;\nendmodule\n",
                             wall=True)
        self.assertTrue(ok)

    def test_width_bug_is_hard_error(self):
        # Over-wide literals are %Error, not %Warning: buggy fails loudly,
        # fixed passes — exactly the mutant-kill gate grade_width_fix needs.
        ok, log = default_lint("module m(input wire [3:0] a, output wire [3:0] y);\n"
                               "assign y = 4'b11111;\nendmodule\n",
                               wall=True)
        self.assertFalse(ok)
        self.assertIn("%Error", log)
        ok2, _ = default_lint("module m(input wire [3:0] a, output wire [3:0] y);\n"
                              "assign y = 4'b1111;\nendmodule\n",
                              wall=True)
        self.assertTrue(ok2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
