"""Hermetic tests for the P3 T4/R2 pipelines. No model, no LMStudio, no
network: every LLM call is a stub. These verify the deterministic stages and
the selection/ranking logic, which is where a false acceptance could hide."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

import t4_pipeline  # noqa: E402
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

    def test_majority_of_valid(self):
        cands = [{"letter": "C", "structurally_valid": True},
                 {"letter": "C", "structurally_valid": True},
                 {"letter": "A", "structurally_valid": True},
                 {"letter": "B", "structurally_valid": False}]
        r = select_answer(cands, GOLD)
        self.assertEqual(r["answer"], "C")
        self.assertTrue(r["correct"])
        self.assertFalse(r["abstained"])

    def test_abstain_when_none_valid(self):
        cands = [{"letter": "A", "structurally_valid": False},
                 {"letter": "B", "structurally_valid": False}]
        r = select_answer(cands, GOLD)
        self.assertTrue(r["abstained"])
        self.assertIsNone(r["answer"])
        self.assertFalse(r["correct"])

    def test_no_false_acceptance_on_wrong_majority(self):
        """A wrong but valid majority must be reported as a MISS, never as
        correct. This is the structural no-false-accept guard."""
        cands = [{"letter": "A", "structurally_valid": True}
                 for _ in range(5)]
        r = select_answer(cands, GOLD)
        self.assertEqual(r["answer"], "A")
        self.assertFalse(r["correct"])

    def test_select_answer_is_gold_independent(self):
        """Gold must not steer selection — only score it. A selection that
        changed with gold would be grading its own homework."""
        cands = [{"letter": "A", "structurally_valid": True},
                 {"letter": "C", "structurally_valid": True}]
        for g in ("A", "B", "C", "D"):
            r = select_answer(cands, g)
            self.assertEqual(r["answer"], "A")
            self.assertEqual(r["correct"], g == "A")

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


class TestGoldLeakRegression(unittest.TestCase):
    """Regression tests for the defect that voided the first P3-C run:
    stage-5 reused grade_reasoned(text, 'C') as if it were a verifier, so
    the gold label leaked into selection and only C could ever win."""

    def test_structural_check_is_gold_free(self):
        for letter in ("A", "B", "D"):
            self.assertTrue(t4_pipeline.structurally_valid(letter))
        self.assertFalse(t4_pipeline.structurally_valid(None))
        self.assertFalse(t4_pipeline.structurally_valid("Z"))

    def test_wrong_letter_survives_structural_check(self):
        """The exact voided-run signature: an all-'A' candidate set must be
        structurally VALID (and then scored wrong), never 'invalid'."""
        cands = [{"letter": "A", "structurally_valid": True} for _ in range(5)]
        r = select_answer(cands, GOLD)
        self.assertEqual(r["answer"], "A")
        self.assertFalse(r["correct"])
        self.assertFalse(r["abstained"])

    def test_generate_candidates_does_not_use_gold(self):
        """Full path with a stub model: every emitted letter must come back
        structurally valid, whatever it is. If gold leaked, non-C letters
        would be marked invalid."""
        fn = stub(["A"] * 5)
        cands = t4_pipeline.generate_candidates(fn, "reasons here")
        self.assertEqual(len(cands), 5)
        self.assertTrue(all(c["structurally_valid"] for c in cands))
        self.assertTrue(all(c["letter"] == "A" for c in cands))
        self.assertNotIn("verifier_ok", cands[0])

    def test_run_once_selection_unaffected_by_gold_value(self):
        """Same stub outputs, different gold: the SELECTION must not move."""
        outs = ["B"] * 12
        a = t4_pipeline.run_once(stub(outs), gold="C")
        b = t4_pipeline.run_once(stub(outs), gold="B")
        self.assertEqual(a["stage_selection"]["answer"],
                         b["stage_selection"]["answer"])
        self.assertEqual(a["stage_selection"]["answer"], "B")
        self.assertFalse(a["stage_selection"]["correct"])
        self.assertTrue(b["stage_selection"]["correct"])

    def test_frozen_grader_confirms_scoring(self):
        """Scoring must agree with the frozen grader, used only post-hoc."""
        fn = stub(["C"] * 12)
        r = t4_pipeline.run_once(fn, gold="C")
        sel = r["stage_selection"]
        self.assertTrue(sel["correct"])
        self.assertTrue(sel["graded_by_frozen_grader"])
        self.assertTrue(sel["scoring_agrees"])


class TestA1Amendment(unittest.TestCase):
    """Amendment A1 changes the per-call timeout and NOTHING else. These
    tests pin the frozen parts so a future edit cannot silently move them."""

    def test_remeasure_uses_frozen_prompt_temp_tokens(self):
        import p3a_t4_remeasure as r
        from p102_t4_reason_probe import (MAX_TOKENS, PROMPT, TEMPERATURE)
        self.assertEqual(r.T4_PROMPT, PROMPT)
        self.assertEqual(r.T4_TEMP, TEMPERATURE)
        self.assertEqual(r.T4_TOKENS, MAX_TOKENS)
        self.assertEqual(r.N, 20)
        self.assertEqual(r.GOLD, "C")
        self.assertEqual(r.MODEL_ID, "qwen2.5-coder-14b-instruct")

    def test_timeout_is_recorded_and_bounded(self):
        import p3a_t4_remeasure as r
        self.assertEqual(r.TIMEOUT_S, 3600)

    def test_timeouts_never_scored(self):
        import p3a_t4_remeasure as r
        import inspect
        src = inspect.getsource(r.main)
        # Accuracy exists only when nothing timed out.
        self.assertIn("if not timed_out else None", src)

    def test_amendment_recorded_in_spec(self):
        import json
        with open(os.path.join(HERE, "P3_A_SPEC.json"),
                  encoding="utf-8") as f:
            spec = json.load(f)
        a1 = next(a for a in spec["amendments"] if a["id"] == "A1")
        self.assertIn("3600", a1["what_changes"])
        self.assertTrue(a1["what_does_not_change"])
        # Bars byte-identical to the frozen tag.
        self.assertEqual(spec["bars"]["t4_accuracy_min"], 0.9)
        self.assertEqual(spec["bars"]["r2_closes_min"], 4)


class TestFrozenSpec(unittest.TestCase):
    SPEC = os.path.join(HERE, "P3_PIPELINE_BENCH.json")

    def test_spec_present_and_frozen(self):
        import json
        with open(self.SPEC, encoding="utf-8") as f:
            spec = json.load(f)
        self.assertEqual(spec["status"].split()[0], "FROZEN")
        self.assertTrue(spec["integrity"]["bars_frozen_before_execution"])
        self.assertTrue(spec["integrity"]["no_post_hoc_relaxation"])
        self.assertTrue(spec["integrity"]["no_training"])

    def test_spec_bars_match_frozen_p2_anchors(self):
        import json
        with open(self.SPEC, encoding="utf-8") as f:
            spec = json.load(f)
        # T4 >= 0.90 and R2 >= 4 closes are the frozen P2 bars, carried
        # forward unchanged. A drift here would be a silent bar change.
        self.assertEqual(spec["verdict_rules"]["m2_t4"]["bar_accuracy"], 0.9)
        self.assertEqual(spec["verdict_rules"]["m1_r2"]["bar_closes"], 4)
        self.assertEqual(
            spec["verdict_rules"]["m1_r2"]["bar_false_acceptances"], 0)
        self.assertEqual(spec["baseline_anchor"]["t4_accuracy"]
                         ["llama-3.1-8b"], 0.7)
        self.assertEqual(spec["baseline_anchor"]["r2_closes"]
                         ["llama-3.1-8b"], 0)

    def test_frozen_evidence_present(self):
        for f in ("P2_M2_LLAMA.json", "P2_M2_DEEPSEEK.json",
                  "P2_M3_VERDICT.json", "P2_BENCH.json"):
            self.assertTrue(os.path.exists(os.path.join(HERE, f)), f)


if __name__ == "__main__":
    unittest.main()