"""Unit tests for the external-corpora registry (no downloads)."""
import unittest

from datasets import ALLOWED_LICENSES, ALLOWED_USES, REGISTRY


class TestRegistry(unittest.TestCase):
    def test_required_fields(self):
        for key, e in REGISTRY.items():
            self.assertEqual(key, e.key)
            for attr in ("name", "url", "license", "uses", "status", "scale",
                         "consumer", "caveats"):
                if attr == "url" and key == "own-flywheel":
                    continue  # internal core has no URL by definition
                val = getattr(e, attr)
                self.assertTrue(val, f"{key}.{attr} empty")

    def test_license_allowlist(self):
        for key, e in REGISTRY.items():
            self.assertIn(e.license, ALLOWED_LICENSES, key)

    def test_uses_allowlist(self):
        for key, e in REGISTRY.items():
            for u in e.uses:
                self.assertIn(u, ALLOWED_USES, f"{key}.{u}")

    def test_status_values(self):
        for key, e in REGISTRY.items():
            self.assertIn(e.status, {"verified-paper", "verified-repo",
                                     "internal", "unverified"}, key)

    def test_expected_corpora_present(self):
        for k in ("circuitnet-2.0", "deepcircuitx", "hlsdataset", "koios-2.0",
                  "opentitan-bugs", "own-flywheel"):
            self.assertIn(k, REGISTRY)

    def test_no_unverified_without_flag(self):
        # research-verify licenses must carry a caveat (nothing trains silently)
        for key, e in REGISTRY.items():
            if e.license == "research-verify":
                self.assertTrue(e.caveats, key)

    def test_internal_core_exists(self):
        core = [e for e in REGISTRY.values() if "flywheel-internal" in e.uses]
        self.assertTrue(core, "external corpora must not stand alone")


if __name__ == "__main__":
    unittest.main(verbosity=2)
