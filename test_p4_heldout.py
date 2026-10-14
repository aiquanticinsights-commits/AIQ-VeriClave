"""Unit tests for the frozen held-out family manifest (no infra)."""
import json
import os
import unittest

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'P4_HELDOUT_v1.json')


def load():
    with open(PATH, encoding='utf-8') as f:
        return json.load(f)


class TestHeldoutFrozen(unittest.TestCase):
    def test_frozen(self):
        d = load()
        self.assertEqual(d["status"], "frozen")
        self.assertEqual(d["freeze"]["version"], "P4_HELDOUT_v1")
        self.assertTrue(d["freeze"]["date"])
        self.assertIn("immutable", d["freeze"]["rule"].lower())

    def test_dev_and_heldout_disjoint(self):
        d = load()
        dev = {f["name"] for f in d["development_families"]}
        held = {f["name"] for f in d["heldout_families"]}
        self.assertTrue(dev and held)
        self.assertEqual(dev & held, set())

    def test_heldout_families_complete(self):
        d = load()
        self.assertGreaterEqual(len(d["heldout_families"]), 3)
        for f in d["heldout_families"]:
            for k in ("name", "why_new", "acceptance"):
                self.assertTrue(f.get(k), f"{f.get('name')}.{k}")

    def test_contamination_rules_cover_vectors(self):
        rules = " ".join(load()["contamination_rules"]).lower()
        for vec in ("training", "prompt", "threshold", "mutation", "judge", "held-out"):
            self.assertIn(vec, rules)

    def test_acceptance_bars_present(self):
        for f in load()["heldout_families"]:
            acc = f["acceptance"]
            self.assertIn("FA=0", acc)
            self.assertIn("C1-C5", acc)

    def test_dev_families_grounded(self):
        for f in load()["development_families"]:
            self.assertTrue(f.get("sources"), f["name"])
            self.assertTrue(f.get("rationale"), f["name"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
