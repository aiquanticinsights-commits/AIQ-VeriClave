"""Unit tests for the exception-review dashboard (no humans involved).

Interaction and timing are injected (scripted answers, stepped clock), so
the measurement math is tested deterministically. Real measurements come
only from live interactive runs (REVIEW_*.json).
"""
import json
import os
import sys
import tempfile
import unittest
import unittest.mock

from review import NAMES, VALID, describe, order_review, run_review, summarize


def scripted(answers):
    it = iter(answers)

    def fn(prompt=""):
        try:
            return next(it)
        except StopIteration:
            raise AssertionError("ran out of scripted answers")
    return fn


def stepped_clock(step=5.0):
    t = [0.0]

    def clock():
        t[0] += step
        return t[0]
    return clock


TASKS = [
    {"task": "T1", "kind": "sva", "rounds": 2, "approvals": 1,
     "escalated_to_human": False, "artifact": "assert...",
     "history": [{"round": 1, "approvals": 0, "verdicts": {}},
                 {"round": 2, "approvals": 1, "verdicts": {"formal": True}}]},
    {"task": "T9", "kind": "mut", "rounds": 3, "approvals": 0,
     "escalated_to_human": True, "artifact": "",
     "history": [{"round": 3, "approvals": 0, "verdicts": {}}]},
    {"task": "T3", "kind": "loc", "rounds": 2, "approvals": 2,
     "escalated_to_human": False, "artifact": "B"},
]


class TestOrder(unittest.TestCase):
    def test_escalations_first(self):
        self.assertEqual([t["task"] for t in order_review(TASKS)],
                         ["T9", "T1", "T3"])

    def test_exceptions_only_drops_clean(self):
        self.assertEqual([t["task"] for t in order_review(TASKS, True)],
                         ["T9", "T1"])

    def test_describe_names_task(self):
        self.assertIn("T9", describe(TASKS[1]))


class TestRun(unittest.TestCase):
    def test_accept_reject_override_skip(self):
        rec = run_review(TASKS, input_fn=scripted(["a", "r", "needs work",
                                                  "o", "wrong call", "s"]),
                         clock=stepped_clock())
        got = {i["task"]: i["disposition"] for i in rec["items"]}
        self.assertEqual(got, {"T1": "accept", "T9": "reject",
                               "T3": "override"})
        self.assertEqual(rec["items"][1]["reason"], "needs work")
        self.assertTrue(all(i["seconds"] == 5.0 for i in rec["items"]))

    def test_reason_required(self):
        rec = run_review(TASKS[:1], input_fn=scripted(["r", "", "  ", "why"]),
                         clock=stepped_clock(2.0))
        self.assertEqual(rec["items"][0]["reason"], "why")

    def test_bad_choice_reprompted(self):
        rec = run_review(TASKS[:1], input_fn=scripted(["x", "bogus", "a"]),
                         clock=stepped_clock())
        self.assertEqual(rec["items"][0]["disposition"], "accept")


class TestResume(unittest.TestCase):
    def _report(self, d):
        rep = {"run_id": "r1", "tasks_detail": [
            {"task": "T1", "kind": "k", "rounds": 2, "approvals": 2,
             "escalated_to_human": False, "artifact": "a1"},
            {"task": "T2", "kind": "k", "rounds": 3, "approvals": 0,
             "escalated_to_human": True, "artifact": ""}]}
        p = os.path.join(d, "rep.json")
        json.dump(rep, open(p, "w"))
        return p

    def test_resume_skips_decided(self):
        import review
        d = tempfile.mkdtemp()
        rep = self._report(d)
        prior = {"run_id": "r1", "reviewer": "qa", "items": [
            {"task": "T1", "machine": "closed", "disposition": "accept",
             "reason": "", "seconds": 5.0, "artifact_shown": True}]}
        rp = os.path.join(d, "rev.json")
        json.dump(prior, open(rp, "w"))
        seen = []

        def fake_input(prompt=""):
            seen.append(prompt)
            return "s"  # skip the only remaining item (T2)

        with unittest.mock.patch("builtins.input", fake_input):
            with unittest.mock.patch.object(
                    sys, "argv", ["review.py", rep, "--resume", rp]):
                self.assertEqual(review.main(), 0)
        out_path = os.path.join(os.path.dirname(os.path.abspath(
            review.__file__)), "REVIEW_r1.json")
        try:
            out = json.load(open(out_path))
        finally:
            if os.path.isfile(out_path):
                os.unlink(out_path)
        by_task = {i["task"]: i["disposition"] for i in out["items"]}
        self.assertEqual(by_task, {"T2": "skip", "T1": "accept"})
        self.assertEqual(out["reviewer"], "qa")


class TestSummarize(unittest.TestCase):
    def test_math(self):
        items = [{"task": "a", "disposition": "accept", "seconds": 10.0},
                 {"task": "b", "disposition": "reject", "seconds": 20.0},
                 {"task": "c", "disposition": "override", "seconds": 30.0},
                 {"task": "d", "disposition": "skip", "seconds": 1.0}]
        s = summarize(items)
        self.assertEqual((s["tasks_presented"], s["tasks_dispositioned"],
                          s["evidence_items_reviewed"]), (4, 3, 3))
        self.assertEqual(s["engineer_review_time_per_task_s"], 20.0)
        self.assertAlmostEqual(s["human_rejection_rate"], 1 / 3, places=4)
        self.assertAlmostEqual(s["human_override_rate"], 1 / 3, places=4)
        self.assertEqual(s["unreviewed"], 1)

    def test_empty_safe(self):
        s = summarize([])
        self.assertIsNone(s["engineer_review_time_per_task_s"])
        self.assertIsNone(s["human_rejection_rate"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
