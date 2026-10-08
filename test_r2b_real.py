"""Hermetic tests for the R-2b real-design R2 family (batch 1). No
Verilator, no models: structure, recorded validation, pure-python
value_gate re-validation, and disjointness from training-eligible
evidence."""
import glob
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

from repair import task_prompt, value_gate  # noqa: E402

WIDTH_CLEAN = {"wb_hslink.v", "wb_shared_bus.v", "wb_sram.v", "wb_uart.v",
               "jtag_tap.v", "hslink_phy_selectio.v"}


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


class TestR2bReal(unittest.TestCase):
    def test_counts_and_ids(self):
        d = load("P3_R2B_REAL.json")
        self.assertEqual(d["n"], 11)
        self.assertEqual(len(d["cases"]), 11)
        ids = [c["id"] for c in d["cases"]]
        self.assertEqual(ids, [f"R2B-R-{i:02d}" for i in range(11)])

    def test_sources_are_width_clean_blocks(self):
        d = load("P3_R2B_REAL.json")
        files = {c["source_file"] for c in d["cases"]}
        self.assertTrue(files <= WIDTH_CLEAN, files)
        self.assertGreaterEqual(len(files), 5)
        for c in d["cases"]:
            self.assertTrue(c["source_line"], c["id"])

    def test_recorded_validation_agrees(self):
        for c in load("P3_R2B_REAL.json")["cases"]:
            self.assertTrue(all(c["validation"]["good_verdicts"].values()),
                            c["id"])
            self.assertFalse(all(
                c["validation"]["buggy_verdicts"].values()), c["id"])

    def test_value_truth_revalidated(self):
        """Pure-python re-validation: good line passes, buggy fails."""
        for c in load("P3_R2B_REAL.json")["cases"]:
            self.assertTrue(value_gate(c["good_line"], c["expect_value"],
                                       c["bad"]), c["id"])
            self.assertFalse(value_gate(c["buggy_line"], c["expect_value"],
                                        c["bad"]), c["id"])

    def test_disjoint_from_training_evidence(self):
        import fnmatch
        # Scale-run outputs (R4_CYCLE_*.json, R4_TRAJECTORIES.json,
        # R4_PARTIAL.json checkpoint) run these same cases by design.
        # Disjointness = no other benchmark's evidence duplicates the
        # case CONTENT (prompts, good/buggy lines). Bare ID mentions
        # (e.g. status commentary) are not duplication and must not trip
        # the test.
        d = load("P3_R2B_REAL.json")
        contents = set()
        for c in d["cases"]:
            contents.add(task_prompt(c))
            contents.add(c["good_line"])
            contents.add(c["buggy_line"])
        for path in glob.glob(os.path.join(HERE, "*.json")):
            base = os.path.basename(path)
            if base == "P3_R2B_REAL.json":
                continue
            if fnmatch.fnmatch(base, "R4_CYCLE_*.json"):
                continue
            if base in ("R4_TRAJECTORIES.json", "R4_PARTIAL.json"):
                continue
            with open(path, encoding="utf-8") as f:
                blob = f.read()
            for hp in contents:
                self.assertNotIn(hp, blob, base)

    def test_frozen_status(self):
        d = load("P3_R2B_REAL.json")
        self.assertIn("p3-r2b-real-frozen", d["status"])
        self.assertIn("FROZEN", d["status"])


if __name__ == "__main__":
    unittest.main()
