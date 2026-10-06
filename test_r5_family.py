"""Hermetic tests for the frozen R5 bench. No Verilator, no models:
structure, recorded validation, pure-python value re-validation, and
disjointness from training-eligible evidence."""
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

from repair import task_prompt, value_gate  # noqa: E402


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


class TestR5Bench(unittest.TestCase):
    def test_counts_and_ids(self):
        d = load("P3_R5_FAMILY.json")
        self.assertEqual(d["n"], 20)
        self.assertEqual(len(d["cases"]), 20)
        ids = [c["id"] for c in d["cases"]]
        self.assertEqual(ids, [f"R5H-{i:02d}" for i in range(20)])

    def test_shape_mirrors_frozen_r5_double(self):
        d = load("P3_R5_FAMILY.json")
        mods = set()
        for c in d["cases"]:
            self.assertEqual(c["verify_mode"], "declline")
            self.assertIn("{decl}", c["frame"])
            self.assertIn("{line}", c["frame"])
            self.assertIn("c", c["signal"])
            self.assertEqual(c["decl_must"][:2],
                             ["wire", f"[{c['width'] - 1}:0]"])
            self.assertIn("input", c["decl_must_absent"])
            mods.add(c["frame"].split("(")[0])
        # Distinct modules per case (r5h00..r5h19), none the frozen r5.
        self.assertEqual(len(mods), 20)
        self.assertTrue(all("r5h" in m for m in mods))

    def test_recorded_validation_agrees(self):
        for c in load("P3_R5_FAMILY.json")["cases"]:
            self.assertTrue(all(c["validation"]["good_verdicts"].values()),
                            c["id"])
            self.assertFalse(all(
                c["validation"]["buggy_verdicts"].values()), c["id"])

    def test_value_truth_revalidated(self):
        """Pure-python: good ASSIGN passes the gate, buggy fails."""
        import re
        for c in load("P3_R5_FAMILY.json")["cases"]:
            m = re.search(r"^ASSIGN:\s*(assign .*;)\s*$", c["good_text"],
                          re.M)
            self.assertIsNotNone(m, c["id"])
            self.assertTrue(value_gate(m.group(1), c["expect_value"],
                                       c["bad"]), c["id"])
            bad_line = next(
                l for l in c["buggy"].splitlines() if l.strip().startswith(
                    "assign "))
            self.assertFalse(value_gate(bad_line, c["expect_value"],
                                        c["bad"]), c["id"])

    def test_disjoint_from_training_evidence(self):
        d = load("P3_R5_FAMILY.json")
        held = {task_prompt(c) for c in d["cases"]}
        held |= {c["buggy"] for c in d["cases"]}
        # Same-family trajectory records necessarily contain r5h cases;
        # disjointness is required against every OTHER benchmark's evidence.
        # Scan git-tracked JSON only: untracked working files (partials such
        # as R5_PARTIAL.json) are not evidence.
        same_family = ("P3_R5_FAMILY.json", "R5_TRAJECTORIES.json")
        import subprocess
        tracked = subprocess.run(
            ["git", "-C", HERE, "ls-files", "*.json"],
            capture_output=True, text=True, check=True).stdout.split()
        for name in tracked:
            if name in same_family:
                continue
            path = os.path.join(HERE, name)
            with open(path, encoding="utf-8") as f:
                blob = f.read()
            self.assertNotIn("r5h", blob, os.path.basename(path))
            for hp in held:
                self.assertNotIn(hp, blob, os.path.basename(path))

    def test_frozen_status_and_temperature(self):
        d = load("P3_R5_FAMILY.json")
        self.assertIn("p3-r5-bench-frozen", d["status"])
        self.assertEqual(d["temperature"], 0.7)


if __name__ == "__main__":
    unittest.main()
