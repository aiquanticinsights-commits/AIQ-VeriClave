"""Unit tests for the reproducibility envelope (no external tools needed)."""
import json
import os
import tempfile
import unittest

from repro import envelope, git_sha, sha256_file, tool_version, write_envelope


class TestRepro(unittest.TestCase):
    def test_tool_missing_is_unavailable(self):
        self.assertEqual(tool_version(["definitely-not-a-tool-xyz"]), "UNAVAILABLE")

    def test_python_version_recorded(self):
        env = envelope()
        self.assertRegex(env["python"], r"^\d+\.\d+")
        self.assertIn("platform", env)
        self.assertIn("git_sha", env)

    def test_tools_dict_shape(self):
        env = envelope()
        self.assertEqual(set(env["tools"]), {"verilator", "yosys", "sby"})
        for v in env["tools"].values():
            self.assertTrue(isinstance(v, str) and v)

    def test_file_hashes(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("repro-fixture")
            path = f.name
        try:
            env = envelope(extra_files=(path,))
            self.assertEqual(len(env["files"][path]), 64)
        finally:
            os.unlink(path)

    def test_write_envelope_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "env.json")
            env = write_envelope(p)
            back = json.load(open(p, encoding="utf-8"))
            self.assertEqual(back["python"], env["python"])
            self.assertIn("tools", back)

    def test_git_sha_shape(self):
        sha = git_sha(".")
        self.assertTrue(sha == "not-a-git-tree" or sha == "git-unavailable"
                        or len(sha) == 40)


if __name__ == "__main__":
    unittest.main(verbosity=2)
