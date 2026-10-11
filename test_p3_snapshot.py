"""Tests for the P3 closure snapshot: every item pinned to live evidence.
The snapshot is a stop-point record; these tests fail loudly if reality
drifts from it (new commits are fine — the snapshot references history)."""
import json
import os
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def git(*args):
    return subprocess.run(["git", "-C", HERE, *args], capture_output=True,
                          text=True, check=True).stdout.strip()


class TestClosureSnapshot(unittest.TestCase):
    def test_final_commit_in_history(self):
        s = load("P3_CLOSURE_SNAPSHOT.json")
        self.assertEqual(s["final_commit"], "9518ed6")
        self.assertIn("9518ed6", git("log", "--oneline", "--all"))

    def test_verdict_and_direction(self):
        s = load("P3_CLOSURE_SNAPSHOT.json")
        g = load("P3_FINAL_DECISION_GATE.json")
        self.assertEqual(s["p3_verdict"], "CLOSED")
        self.assertEqual(s["system_direction"], "VALIDATED")
        self.assertIn("human_approval", g)
        self.assertIn("TRAINING NOT AUTHORIZED", g["decision"])

    def test_d1_and_economics_current(self):
        s = load("P3_CLOSURE_SNAPSHOT.json")
        v2 = load("P3_D_READINESS_V2.json")
        self.assertEqual(
            v2["measurements"]["d1_scale"]["positive_trajectories"], 266)
        self.assertEqual(v2["grades"]["d1_scale"], "FAIL")
        self.assertEqual(v2["grades"]["d10_economics"], "FAIL")
        self.assertIn("266/1000", s["d1_scale"])
        self.assertIn("NOT AUTHORIZED", s["training"])

    def test_non_authorizations_cover_everything(self):
        s = load("P3_CLOSURE_SNAPSHOT.json")
        blob = json.dumps(s["non_authorizations"]).lower()
        for token in ("r-4", "rtl", "benchmark", "bar", "plain-regime",
                      "training", "gpu", "held-out"):
            self.assertIn(token, blob, token)

    def test_frozen_refs_exist(self):
        s = load("P3_CLOSURE_SNAPSHOT.json")
        tags = git("tag", "--list", "p3-*").split()
        for t in s["frozen_evidence_references"]:
            self.assertIn(t, tags, t)
        self.assertGreaterEqual(len(s["frozen_evidence_references"]), 20)

    def test_reopen_conditions_gate_d1(self):
        s = load("P3_CLOSURE_SNAPSHOT.json")
        blob = json.dumps(s["d1_reopen_conditions"]).lower()
        self.assertIn("re-authorization", blob)
        self.assertIn("p4", blob)
        self.assertIn("ready", blob)


if __name__ == "__main__":
    unittest.main()
