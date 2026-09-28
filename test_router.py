"""Unit tests for the AIQ-VeriClave router (deterministic, no infra)."""
import unittest

from router import (BAKEOFF_CANDIDATES, BASELINE_GENERATOR, CAPABILITY, Candidate,
                    Task, bon_width, cheapest, estimate_call_cost, judge_filter,
                    majority_vote, mock_tokens, route, run_task, score_generator)


class TestEfficiencyRouting(unittest.TestCase):
    def test_bon_width_bands(self):
        self.assertEqual(bon_width(Task("T", "mutant-kill", 1)), 3)
        self.assertEqual(bon_width(Task("T", "mutant-kill", 2)), 3)
        self.assertEqual(bon_width(Task("T", "mutant-kill", 3)), 5)
        self.assertEqual(bon_width(Task("T", "mutant-kill", 4)), 5)
        self.assertEqual(bon_width(Task("T", "mutant-kill", 5)), 8)

    def test_cheapest_is_selected_baseline(self):
        # Model-agnostic P0: the bake-off winner alias is cheapest (local LMStudio).
        self.assertEqual(cheapest(Task("T", "coverage", 5)), BASELINE_GENERATOR)
        self.assertEqual(BASELINE_GENERATOR, "selected-open-llm")

    def test_bakeoff_slate_covers_local_trio(self):
        for m in ("gpt-oss-20b", "deepseek-coder-6.7b", "llama-3.1-8b"):
            self.assertIn(m, BAKEOFF_CANDIDATES)
            self.assertIn(m, CAPABILITY)

    def test_cascade_round_one_single(self):
        seen = []

        def gen(g, t, r):
            if r == 1:
                seen.append(g)
            return "o"

        def ver(g, t, o):
            return {"syntax": True, "equiv": True, "proof": True}

        r = run_task(Task("T", "mutant-kill", 2), gen, ver, k=3)
        self.assertEqual(seen, [BASELINE_GENERATOR])
        self.assertTrue(r["cascaded"])

    def test_no_cascade_fans_out_round_one(self):
        seen = []

        def gen(g, t, r):
            if r == 1:
                seen.append(g)
            return "o"

        def ver(g, t, o):
            return {"syntax": True, "equiv": True, "proof": True}

        run_task(Task("T", "mutant-kill", 2), gen, ver, k=3, cascade=False)
        self.assertEqual(len(seen), 3)

    def test_cost_ceiling_keeps_cheapest(self):
        t = Task("T", "coverage", 5)
        short = route(t, k=5, max_cost_usd=0.0)
        self.assertEqual(short, [BASELINE_GENERATOR])

    def test_estimate_cost_scales_with_difficulty(self):
        c1 = estimate_call_cost("qwen3-coder-next", 1)
        c5 = estimate_call_cost("qwen3-coder-next", 5)
        self.assertGreater(c5, c1)
        self.assertGreater(c5, 0)

    def test_mock_tokens_shape(self):
        it, ot = mock_tokens(5)
        self.assertGreater(it, ot)
        self.assertGreater(it, 1500)


class TestRouter(unittest.TestCase):
    def test_route_returns_k_unique_ranked(self):
        t = Task("T1", "mutant-kill", 3)
        short = route(t, k=3)
        self.assertEqual(len(short), 3)
        self.assertEqual(len(set(short)), 3)
        scores = [score_generator(g, t) for g in short]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_easy_tasks_prefer_cheap(self):
        easy, hard = Task("E", "coverage", 1), Task("H", "coverage", 5)
        # selected-open-llm is cheapest (cost 1.0, local): must rank first on easy.
        self.assertEqual(route(easy, k=5)[0], BASELINE_GENERATOR)
        # still competitive on hard (capability-led, RouteMoA priority)
        self.assertIn(BASELINE_GENERATOR, route(hard, k=3))

    def test_judge_discards_unproven(self):
        good = Candidate("T", "a", "o", {"syntax": True, "equiv": True})
        bad = Candidate("T", "b", "o", {"syntax": False, "equiv": True})
        self.assertEqual(judge_filter([good, bad]), [good])
        self.assertEqual(judge_filter([bad]), [])

    def test_majority_vote_picks_most_approvals(self):
        c1 = Candidate("T", "a", "o", {"syntax": True})
        c2 = Candidate("T", "b", "o", {"syntax": True, "equiv": True, "proof": True})
        self.assertEqual(majority_vote([c1, c2]).generator, "b")
        self.assertIsNone(majority_vote([]))

    def test_run_task_respects_min_rounds(self):
        calls = []

        def gen(g, t, r):
            calls.append(r)
            return "o"

        def ver(g, t, o):
            return {"syntax": True, "equiv": True, "proof": True}

        r = run_task(Task("T", "mutant-kill", 2), gen, ver, k=2)
        self.assertGreaterEqual(r["rounds"], 2)  # TUMIX discipline
        self.assertLessEqual(r["rounds"], 3)
        self.assertIsNotNone(r["winner"])

    def test_run_task_no_winner_when_all_fail(self):
        r = run_task(Task("T", "mutant-kill", 2),
                     lambda g, t, r: "o",
                     lambda g, t, o: {"syntax": False},
                     k=2, min_rounds=1, max_rounds=1)
        self.assertIsNone(r["winner"])

    def test_closure_boundary_escalates_to_human(self):
        # Frozen §41: no automatic fourth round — failure escalates.
        r = run_task(Task("T", "mutant-kill", 5),
                     lambda g, t, r: "o",
                     lambda g, t, o: {"syntax": False},
                     k=3, min_rounds=2, max_rounds=3)
        self.assertIsNone(r["winner"])
        self.assertEqual(r["rounds"], 3)
        self.assertTrue(r["escalated_to_human"])

    def test_winner_never_escalates(self):
        r = run_task(Task("T", "mutant-kill", 2),
                     lambda g, t, r: "o",
                     lambda g, t, o: {"syntax": True, "equiv": True, "proof": True},
                     k=2)
        self.assertIsNotNone(r["winner"])
        self.assertFalse(r["escalated_to_human"])


if __name__ == "__main__":
    unittest.main(verbosity=2)