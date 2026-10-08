"""Hermetic tests for the R-1 held-out split. No Verilator, no models, no
network: disjointness, structure, recorded validation, and pure-python
re-validation (value_gate + frozen grader)."""
import glob
import json
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

from repair import task_prompt, value_gate  # noqa: E402
from p102_t4_reason_probe import PROMPT as FROZEN_T4, grade_reasoned  # noqa: E402


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def grams(text, n=8):
    w = re.findall(r"[a-z0-9]+", text.lower())
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


class TestHeldout(unittest.TestCase):
    def test_counts_and_ids(self):
        d = load("P3_HELDOUT.json")
        self.assertEqual(len(d["r2"]["cases"]), 16)
        self.assertEqual(len(d["t4"]["probes"]), 8)
        ids = [c["id"] for c in d["r2"]["cases"]]
        ids += [p["id"] for p in d["t4"]["probes"]]
        self.assertEqual(len(set(ids)), 24)
        self.assertTrue(all(i.startswith("HELD-R2-") for i in ids[:16]))
        self.assertTrue(all(i.startswith("HELD-T4-") for i in ids[16:]))

    def test_modules_and_prompts_unique(self):
        d = load("P3_HELDOUT.json")
        mods = re.findall(r"module (\w+)", "".join(
            c["frame"] for c in d["r2"]["cases"]))
        self.assertEqual(len(set(mods)), 16)
        self.assertTrue(all(m.startswith("heldr") for m in mods))
        prompts = [task_prompt(c) for c in d["r2"]["cases"]]
        prompts += [p["prompt"] for p in d["t4"]["probes"]]
        self.assertEqual(len(set(prompts)), 24)

    def test_zero_overlap_with_training_eligible_evidence(self):
        """Held-out case CONTENT (prompts, buggy lines) must appear in NO
        other JSON — the split is disjoint by construction. Bare ID or
        module-name mentions (e.g. status commentary) are not duplication
        and must not trip the test."""
        d = load("P3_HELDOUT.json")
        held_prompts = {task_prompt(c) for c in d["r2"]["cases"]}
        held_prompts |= {p["prompt"] for p in d["t4"]["probes"]}
        held_prompts |= {c["buggy"] for c in d["r2"]["cases"]}
        for path in glob.glob(os.path.join(HERE, "*.json")):
            if os.path.basename(path) in ("P3_HELDOUT.json",):
                continue
            with open(path, encoding="utf-8") as f:
                blob = f.read()
            for hp in held_prompts:
                self.assertNotIn(hp, blob, os.path.basename(path))

    def test_t4_content_disjoint_from_frozen_probe(self):
        """Template ('Think step by step...Answer: X') is shared by design;
        the failure/evidence content must share no 8-word run with the
        frozen prompt — nor with any sibling probe."""
        frozen_content = FROZEN_T4.split("Think step by step")[0]
        frozen_g = grams(frozen_content)
        bodies = [p["prompt"].split("Think step by step")[0]
                  for p in load("P3_HELDOUT.json")["t4"]["probes"]]
        for b in bodies:
            self.assertTrue(grams(b).isdisjoint(frozen_g), b[:60])
        for i in range(len(bodies)):
            for j in range(i + 1, len(bodies)):
                self.assertTrue(grams(bodies[i]).isdisjoint(grams(bodies[j])),
                                (i, j))

    def test_r2_value_truth_revalidated(self):
        """Pure-python re-validation (no lint): good line passes the value
        gate, buggy line fails it — for all 16 cases."""
        for c in load("P3_HELDOUT.json")["r2"]["cases"]:
            good = f"assign q = {c['width']}'b{c['expect_value']:0{c['width']}b};"
            self.assertTrue(value_gate(good, c["expect_value"], c["bad"]),
                            c["id"])
            self.assertFalse(value_gate(f"assign q = {c['bad']};",
                                        c["expect_value"], c["bad"]), c["id"])
            # Recorded authoring validation (incl. lint wall) agrees.
            self.assertTrue(all(c["validation"]["good_verdicts"].values()),
                            c["id"])
            self.assertFalse(all(c["validation"]["buggy_verdicts"].values()),
                             c["id"])

    def test_t4_structure_and_grader_sanity(self):
        for p in load("P3_HELDOUT.json")["t4"]["probes"]:
            opts = re.findall(r"^([A-D])\.\s", p["prompt"], re.M)
            self.assertEqual(sorted(opts), ["A", "B", "C", "D"], p["id"])
            self.assertIn(p["gold"], "ABCD")
            self.assertIn("Answer: X", p["prompt"])
            for letter in "ABCD":
                ok, _ = grade_reasoned(f"Answer: {letter}", p["gold"])
                self.assertEqual(ok, letter == p["gold"], (p["id"], letter))

    def test_never_train_eligible(self):
        d = load("P3_HELDOUT.json")
        self.assertIn("never train-eligible", d["rules"])
        self.assertIn("p3-heldout-frozen", d["status"])


if __name__ == "__main__":
    unittest.main()
