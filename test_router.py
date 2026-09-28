"""Unit tests for the AIQ-VeriClave router (deterministic, no infra)."""
import unittest

from router import (CAPABILITY, Candidate, Task, bon_width, cheapest,
                    estimate_call_cost, judge_filter, majority_vote,
                    mock_tokens, route, run_task, score_generator)


class TestEfficiencyRouting(unittest.TestCase):
    def test_bon_width_bands(self):
        self.assertEqual(bon_width(Task("T", "mutant-kill", 1)), 3)
        self.assertEqual(bon_width(Task("T", "mutant-kill", 2)), 3)
        self.assertEqual(bon_width(Task("T", "mutant-kill", 3)), 5)
        self.assertEqual(bon_width(Task("T", "mutant-kill", 4)), 5)
        self.assertEqual(bon_width(Task("T", "mutant-kill", 5)), 8)

    def test_cheapest_is_qwen_class(self):
        self.assertEqual(cheapest(Task("T", "coverage", 5)), "qwen3-coder-next")

    def test_cascade_round_one_single(self):
        seen = []

        def gen(g, t, r):
            if r == 1:
                seen.append(g)
            return "o"

        def ver(g, t, o):
            return {"syntax": True, "equiv": True, "proof": True}

        r = run_task(Task("T", "mutant-kill", 2), gen, ver, k=3)
        self.assertEqual(seen, ["qwen3-coder-next"])
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
        self.assertEqual(short, ["qwen3-coder-next"])

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
        # qwen3-coder-next is cheapest (cost 1.0): must rank first on easy.
        self.assertEqual(route(easy, k=5)[0], "qwen3-coder-next")
        # still competitive on hard (capability-led, RouteMoA priority)
        self.assertIn("qwen3-coder-next", route(hard, k=3))

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


if __name__ == "__main__":
    unittest.main(verbosity=2)