"""Entry-point and contract tests for the assisted-arm runner (P7)."""
import json
import os
import tempfile
import unittest

import pilot_assist


class TestAssistedArm(unittest.TestCase):
    def test_main_entry_point_exists(self):
        self.assertTrue(callable(getattr(pilot_assist, "main", None)))

    def test_main_writes_passing_report(self):
        d = tempfile.mkdtemp()
        code = pilot_assist.main(outdir=d)
        self.assertEqual(code, 0)
        path = os.path.join(d, "P7_PILOT_ASSISTED.json")
        self.assertTrue(os.path.isfile(path))
        with open(path, encoding="utf-8") as f:
            rep = json.load(f)
        self.assertEqual(rep["arm"], "assisted")
        self.assertEqual(set(rep["tasks"]), set(pilot_assist.TASKS))
        self.assertTrue(all(r["verdict"] == "PASS"
                            for r in rep["tasks"].values()))
        self.assertIn("PENDING", rep["human_arm"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
