"""Unit tests for the review dashboard rollup (pure fixtures)."""
import unittest

from review_dashboard import render, rollup

RUN = {"tasks": 25, "closed": 20, "escalated_to_human": 5,
       "audit_completeness": 1.0}
REVIEW = {"reviewer": "qa",
          "items": [
              {"task": "a", "disposition": "accept", "seconds": 12.0},
              {"task": "b", "disposition": "accept", "seconds": 18.0},
              {"task": "c", "disposition": "reject", "seconds": 30.0},
              {"task": "d", "disposition": "override", "seconds": 40.0},
              {"task": "e", "disposition": "skip", "seconds": 2.0},
          ]}


class TestRollup(unittest.TestCase):
    def test_machine_side(self):
        d = rollup(RUN)
        self.assertEqual((d["tasks_processed"], d["auto_accepted"],
                          d["exceptions"]), (25, 20, 5))
        self.assertAlmostEqual(d["human_review_rate"], 0.2)
        self.assertIsNone(d["reviewer"])
        self.assertIsNone(d["median_decision_time_s"])

    def test_human_side(self):
        d = rollup(RUN, REVIEW)
        self.assertEqual(d["median_decision_time_s"], 24.0)
        self.assertAlmostEqual(d["reject_rate"], 0.25)
        self.assertAlmostEqual(d["override_rate"], 0.25)
        self.assertEqual(d["reviewer"], "qa")
        self.assertEqual(d["evidence_opened_per_task"], 0.16)

    def test_empty_safe(self):
        d = rollup({"tasks": 0, "closed": 0, "escalated_to_human": 0})
        self.assertIsNone(d["human_review_rate"])
        d2 = rollup(RUN, {"items": []})
        self.assertIsNone(d2["median_decision_time_s"])


class TestRender(unittest.TestCase):
    def test_unknown_renders_question(self):
        text = render(rollup(RUN))
        self.assertIn("?", text)
        self.assertIn("Reject rate", text)
        self.assertNotIn("None", text)

    def test_numbers_render(self):
        text = render(rollup(RUN, REVIEW))
        self.assertIn("20.0%", text)  # human review rate 5/25
        self.assertIn("25.0%", text)  # reject 1/4
        self.assertIn("qa", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
