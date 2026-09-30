"""Unit tests for the SBY-container verifier (pure evaluation only)."""
import unittest

from scripts.verify_sby_container import evaluate


def _doc(**kw):
    d = {"environment": "docker-sby-smoke", "status": "PASS",
         "os": "ubuntu:24.04", "python": "Python 3.12.3",
         "yosys": "Yosys 0.69", "sby": "SBY v0.69",
         "solver": "boolector 3.2.4", "git_commit": "abc123",
         "image_digest": "sha256:00", "test": "counter_sby_smoke",
         "formal_result": "PASS",
         "artifacts": ["counter.sv", "counter.sby", "out/logfile.txt"],
         "rtl_sha16": "9f93df1b1c029fce"}
    d.update(kw)
    return d


class TestEvaluate(unittest.TestCase):
    def test_all_pass(self):
        v = evaluate(_doc(), "sha256:00", "abc123")
        self.assertTrue(v["pass"])
        self.assertTrue(all(v["checks"].values()))

    def test_failed_proof_fails(self):
        v = evaluate(_doc(status="FAIL", formal_result="FAIL"), "i", "c")
        self.assertFalse(v["pass"])
        self.assertFalse(v["checks"]["proof_proven"])

    def test_missing_versions_fail(self):
        v = evaluate(_doc(yosys="", sby=""), "i", "c")
        self.assertFalse(v["checks"]["sby_launches"])
        self.assertFalse(v["checks"]["versions_recorded"])

    def test_missing_provenance_fails(self):
        v = evaluate(_doc(git_commit="", image_digest=""), "i", "c")
        self.assertFalse(v["checks"]["provenance_recorded"])

    def test_few_artifacts_fail(self):
        v = evaluate(_doc(artifacts=["a.sv"]), "i", "c")
        self.assertFalse(v["checks"]["artifacts_collected"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
