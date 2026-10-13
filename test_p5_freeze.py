"""Unit tests for P5 freeze consistency (no infra)."""
import json
import unittest

BASE = r'C:\Projects\ChipDesign\AIQ-VeriClave'


def load(name):
    with open(f'{BASE}\\{name}', encoding='utf-8') as f:
        return json.load(f)


class TestFreeze(unittest.TestCase):
    def test_freeze_status(self):
        d = load('P5_FREEZE_v1.json')
        self.assertEqual(d["status"], "prepared-pending-signoff")
        self.assertTrue(d["repo_commit"])
        self.assertEqual(len(d["repo_commit"]), 40)

    def test_referenced_artifacts_exist(self):
        import os
        for f in ("P5_QUALIFICATION_PROTOCOL.md", "P4_HELDOUT_v1.json",
                  "P4_BENCH_v1.json", "P4_EXIT_REVIEW.md"):
            self.assertTrue(os.path.exists(f"{BASE}\\{f}"), f)

    def test_families_match_manifest(self):
        freeze = load('P5_FREEZE_v1.json')
        manifest = load('P4_HELDOUT_v1.json')
        manifest_names = sorted(f["name"] for f in manifest["heldout_families"])
        self.assertEqual(sorted(freeze["families"]["set"]), manifest_names)
        self.assertEqual(manifest["status"], "frozen")

    def test_bars_match_bench(self):
        freeze = load('P5_FREEZE_v1.json')
        self.assertIn("P4_BENCH_v1.json", freeze["acceptance"]["source"])
        self.assertIn("FA=0", freeze["acceptance"]["bars"])

    def test_signoff_still_pending(self):
        d = load('P5_FREEZE_v1.json')
        self.assertIn("PENDING", d["human_signoff"])

    def test_model_config_complete(self):
        mc = load('P5_FREEZE_v1.json')["model_config"]
        for k in ("generators", "BoN", "router", "judge", "closure", "reward"):
            self.assertTrue(mc.get(k), k)


if __name__ == "__main__":
    unittest.main(verbosity=2)
