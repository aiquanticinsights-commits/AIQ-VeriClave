"""Unit tests for evidence-schema check (fixture JSONs in temp dirs)."""
import json
import os
import tempfile
import unittest

from check_evidence import check_one


class TestSchema(unittest.TestCase):
    def test_ok(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "x.json")
        json.dump({"a": 1}, open(p, "w"))
        self.assertEqual(check_one(p, ("a",)), (True, "ok"))

    def test_missing_key(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "x.json")
        json.dump({"a": 1}, open(p, "w"))
        ok, msg = check_one(p, ("a", "b"))
        self.assertFalse(ok)
        self.assertIn("b", msg)

    def test_absent_skipped(self):
        ok, msg = check_one(os.path.join(tempfile.mkdtemp(), "no.json"),
                            ("a",))
        self.assertTrue(ok)
        self.assertIn("skipped", msg)

    def test_invalid_json(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "x.json")
        open(p, "w").write("{broken")
        ok, _ = check_one(p, ())
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
