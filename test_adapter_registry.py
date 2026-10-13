"""Unit tests for the adapter maturity registry (no infra)."""
import unittest

from adapter_registry import LEVELS, REGISTRY, level_of, qualified


class TestRegistry(unittest.TestCase):
    def test_levels_valid(self):
        for e in REGISTRY:
            self.assertIn(e.level, LEVELS, e.tool)
            self.assertTrue(e.evidence, e.tool)

    def test_open_toolchain_l4(self):
        for tool in ("verilator", "yosys", "symbiyosys"):
            self.assertTrue(qualified(tool, minimum="L4"), tool)

    def test_commercial_parsers_l1_only(self):
        for tool in ("vcs", "questa", "xcelium"):
            self.assertEqual(level_of(tool), "L1")
            self.assertFalse(qualified(tool, minimum="L4"))

    def test_vivado_qualified_functions_only(self):
        self.assertTrue(qualified("vivado-xsim", "block-run", "L4"))
        entry = [e for e in REGISTRY if e.tool == "vivado-xsim"][0]
        self.assertIn("QUALIFIED FUNCTIONS ONLY", entry.limits)

    def test_uvm_templates_l1(self):
        self.assertEqual(level_of("uvm-gen"), "L1")

    def test_unknown_is_l0(self):
        self.assertEqual(level_of("imaginary-sim"), "L0")
        self.assertFalse(qualified("imaginary-sim"))

    def test_no_blanket_claims(self):
        # every entry states limits or empty-string explicitly (no silent scope)
        for e in REGISTRY:
            self.assertIsInstance(e.limits, str)


if __name__ == "__main__":
    unittest.main(verbosity=2)
