"""Hermetic tests for the P3 T4/R2 pipelines. No model, no LMStudio, no
network: every LLM call is a stub. These verify the deterministic stages and
the selection/ranking logic, which is where a false acceptance could hide."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

from p2_bench import r2_cases  # noqa: E402
from r2_pipeline import (numeric_constraint, parse_target_width, rank,  # noqa: E402
                         stage_localize)
from t4_pipeline import (fact_consistency, parse_letter,  # noqa: E402
                         select_answer)

GOLD = "C"


def stub(texts):
    it = iter(texts)

    def fn(prompt, n=256, temp=0.7):
        try:
            t = next(it)
        except StopIteration:
            t = "Answer:A"
        return t, {"prompt_tokens": 10, "completion_tokens": 10}, 0.1
    return fn


class TestT4Selection(unittest.TestCase):
    def test_parse_letter(self):
        self.assertEqual(parse_letter("C"), "C")
        self.assertEqual(parse_letter("  b.\n"), "B")
        self.assertIsNone(parse_letter("no letter here"))
        self.assertIsNone(parse_letter(""))

    def test_majority_of_passing(self):
        cands = [{"letter": "C", "verifier_ok": True},
                 {"letter": "C", "verifier_ok": True},
                 {"letter": "A", "verifier_ok": True},
                 {"letter": "B", "verifier_ok": False}]
        r = select_answer(cands, GOLD)
        self.assertEqual(r["answer"], "C")
        self.assertTrue(r["correct"])
        self.assertFalse(r["abstained"])

    def test_abstain_when_none_pass(self):
        cands = [{"letter": "A", "verifier_ok": False},
                 {"letter": "B", "verifier_ok": False}]
        r = select_answer(cands, GOLD)
        self.assertTrue(r["abstained"])
        self.assertIsNone(r["answer"])
        self.assertFalse(r["correct"])

    def test_no_false_acceptance_on_wrong_majority(self):
        """A wrong but verifier-passing majority must be reported as a MISS,
        never as correct. This is the structural no-false-accept guard."""
        cands = [{"letter": "A", "verifier_ok": True} for _ in range(5)]
        r = select_answer(cands, GOLD)
        self.assertEqual(r["answer"], "A")
        self.assertFalse(r["correct"])

    def test_fact_consistency(self):
        c = fact_consistency("reset synchronizer flops in single clock domain",
                             "the design uses a single clock domain")
        self.assertFalse(c["degenerate"])
        self.assertGreater(c["jaccard"], 0.0)
        d = fact_consistency("alpha beta gamma", "delta epsilon zeta")
        self.assertTrue(d["degenerate"])
        e = fact_consistency("", "anything")
        self.assertTrue(e["degenerate"])


class TestR2DeterministicStages(unittest.TestCase):
    def test_constraint_matches_frozen_expect_for_all_20(self):
        for case in r2_cases():
            con = numeric_constraint(case)
            self.assertTrue(con["ok"], case["id"])
            self.assertTrue(con["agrees_with_frozen_task"], case["id"])
            self.assertEqual(con["expect"], case["expect_value"])
            self.assertTrue(con["truncates"], case["id"])
            self.assertEqual(len(con["expect_bits"]), case["width"])

    def test_width_parsing(self):
        case = r2_cases()[0]
        self.assertEqual(parse_target_width(case), case["width"])

    def test_localize_finds_width_diagnostic(self):
        for case in r2_cases():
            loc = stage_localize(case)
            self.assertTrue(loc["has_width_diag"], case["id"])

    def test_rank_abstains_when_nothing_passes(self):
        task = r2_cases()[0]
        bad = [{"i": 0, "text": "assign q = 9'b100000000;", "passes": False}]
        r = rank(bad, task)
        self.assertTrue(r["abstained"])
        self.assertIsNone(r["answer"])

    def test_rank_prefers_fewest_edits(self):
        task = r2_cases()[0]
        w = task["width"]
        v = task["expect_value"]
        good = f"assign q = {w}'b{v:0{w}b};"
        noisy = f"// fix\n{w}'d{v}\n{good}"
        cands = [{"i": 0, "text": noisy, "passes": True},
                 {"i": 1, "text": good, "passes": True}]
        r = rank(cands, task)
        self.assertEqual(r["line"], good)
        self.assertFalse(r["abstained"])
        self.assertEqual(r["sim"], "not-run")

    def test_sim_gate_blocks_winner_on_fail(self):
        task = r2_cases()[0]
        w, v = task["width"], task["expect_value"]
        good = f"assign q = {w}'b{v:0{w}b};"
        r = rank([{"i": 0, "text": good, "passes": True}], task,
                 sim_fn=lambda t: False)
        self.assertTrue(r["abstained"])
        self.assertEqual(r["sim"], "fail")

    def test_sim_gate_passes(self):
        task = r2_cases()[0]
        w, v = task["width"], task["expect_value"]
        good = f"assign q = {w}'b{v:0{w}b};"
        r = rank([{"i": 0, "text": good, "passes": True}], task,
                 sim_fn=lambda t: True)
        self.assertFalse(r["abstained"])
        self.assertEqual(r["sim"], "pass")

    def test_sim_error_is_not_pass(self):
        task = r2_cases()[0]
        w, v = task["width"], task["expect_value"]
        good = f"assign q = {w}'b{v:0{w}b};"
        r = rank([{"i": 0, "text": good, "passes": True}], task,
                 sim_fn=lambda t: (_ for _ in ()).throw(RuntimeError("x")))
        self.assertTrue(r["abstained"])
        self.assertTrue(r["sim"].startswith("error"))

    def test_pipeline_runs_hermetically_with_stub(self):
        import r2_pipeline
        case = r2_cases()[0]
        w, v = case["width"], case["expect_value"]
        good = f"assign q = {w}'b{v:0{w}b};"
        r = r2_pipeline.run_once(stub([good] * 8), case)
        self.assertFalse(r["stage_rank"]["abstained"])
        self.assertEqual(r["stage_rank"]["n_passing"], 5)


if __name__ == "__main__":
    unittest.main()