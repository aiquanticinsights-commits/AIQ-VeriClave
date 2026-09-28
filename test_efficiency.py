"""Unit tests for token-efficiency modules (no infra)."""
import unittest

from cache_policy import (classify, contains_sensitive, order_prompt, redact,
                          stage_tools)
from compact import (Turn, compact_history, estimate_tokens, should_compact,
                     truncate)
from eval_harness import TokenLedger


class TestLedger(unittest.TestCase):
    def test_cost_math(self):
        L = TokenLedger()
        L.record("T1", "gen-r1", "qwen3-coder-next", 10000, 1000, 0.0)
        # 10000/1e6*0.20 + 1000/1e6*0.80 = 0.002 + 0.0008
        self.assertAlmostEqual(L.summary()["cost_usd"], 0.0028, places=6)

    def test_cached_cheaper_than_fresh(self):
        L1, L2 = TokenLedger(), TokenLedger()
        L1.record("T", "s", "qwen3-coder-next", 10000, 0, 0.0)
        L2.record("T", "s", "qwen3-coder-next", 10000, 0, 0.9)
        self.assertGreater(L1.summary()["cost_usd"], L2.summary()["cost_usd"])

    def test_cached_frac_clamped(self):
        L = TokenLedger()
        L.record("T", "s", "qwen3-coder-next", 100, 100, 99.0)
        s = L.summary()
        self.assertEqual(s["calls"], 1)
        self.assertGreaterEqual(s["cost_usd"], 0.0)

    def test_by_generator_breakdown(self):
        L = TokenLedger()
        L.record("T1", "s", "qwen3-coder-next", 1000, 100, 0.0)
        L.record("T2", "s", "glm-4.7", 1000, 100, 0.0)
        s = L.summary()
        self.assertEqual(set(s["by_generator_usd"]), {"qwen3-coder-next", "glm-4.7"})


class TestRedaction(unittest.TestCase):
    def test_spec_passes(self):
        spec = "The FIFO must assert full when count reaches depth."
        self.assertFalse(contains_sensitive(spec))
        self.assertEqual(classify("spec", spec), "cache")

    def test_rtl_fails_closed(self):
        rtl = "module fifo (input clk, input [7:0] d);\n always @(posedge clk) q <= d;\nendmodule"
        self.assertTrue(contains_sensitive(rtl))
        self.assertEqual(classify("spec", rtl), "tail")
        red = redact(rtl)
        self.assertNotIn("always @(posedge clk)", red)

    def test_vcd_markers_rejected(self):
        vcd = "#12345\nb01010101010101010101 \"\n$dumpvars"
        self.assertTrue(contains_sensitive(vcd))
        self.assertEqual(classify("frm-template", vcd), "tail")

    def test_hex_and_vectors_masked(self):
        t = "key = 9de2d3c202e66d29314"
        self.assertTrue(contains_sensitive(t))
        self.assertNotIn("9de2d3c202e66d29314", redact(t))

    def test_unknown_kind_is_tail(self):
        self.assertEqual(classify("mystery", "plain text"), "tail")

    def test_ordering_stable_first(self):
        blocks = [("vcd-slice", "#10 b01"), ("spec", "FIFO spec text"),
                  ("frm-template", "def model(x): return x")]
        ordered = order_prompt(blocks)
        kinds = [k for k, _ in ordered]
        self.assertEqual(kinds, ["spec", "frm-template", "vcd-slice"])

    def test_stage_tools_minimal(self):
        self.assertIn("read", stage_tools("localize"))
        self.assertNotIn("edit-verif", stage_tools("localize"))
        self.assertEqual(stage_tools("unknown-stage"), ("read",))


class TestCompaction(unittest.TestCase):
    def test_short_text_untouched(self):
        self.assertEqual(truncate("abc"), "abc")

    def test_truncate_marks(self):
        out = truncate("x" * 2000)
        self.assertIn("truncated", out)
        self.assertLess(len(out), 2000)
        # head and tail preserved verbatim (no rephrasing possible)
        self.assertTrue(out.startswith("x" * 10) and out.rstrip().endswith("x" * 10))

    def test_should_compact_at_budget(self):
        self.assertTrue(should_compact(100000, 100000))
        self.assertFalse(should_compact(999, 100000))

    def test_tool_outputs_evicted_first(self):
        turns = [Turn("user", "tool result " + "y" * 100, tool_output=True),
                 Turn("user", "keep me"),
                 Turn("assistant", "recent " + "z" * 10),
                 Turn("assistant", "latest"),
                 Turn("user", "now")]
        out = compact_history(turns, keep_last=2)
        texts = " ".join(t.content for t in out)
        self.assertNotIn("tool result", texts)
        self.assertIn("keep me", texts)
        self.assertIn("latest", texts)

    def test_never_recompacts(self):
        old = [Turn("system", "[COMPACTED] dropped 3 turns", compacted=True),
               Turn("user", "a"), Turn("user", "b"), Turn("user", "c")]
        out = compact_history(old, keep_last=1)
        self.assertFalse(any("[COMPACTED] dropped 3" in t.content for t in out))

    def test_estimate_tokens(self):
        self.assertEqual(estimate_tokens("abcd" * 250), 250)


if __name__ == "__main__":
    unittest.main(verbosity=2)
