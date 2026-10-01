"""P2 M1 spec tests: R2 20-case table validity (hermetic, no LLM/tools)."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

from p2_bench import _R2_SPECS, r2_cases  # noqa: E402
from repair import PROMPT_LINE, task_prompt, value_gate  # noqa: E402


class TestR2Table(unittest.TestCase):
    def test_twenty_cases(self):
        self.assertEqual(len(_R2_SPECS), 20)
        self.assertEqual(len(r2_cases()), 20)

    def test_all_genuine_truncation_bugs(self):
        for w, bits, val in _R2_SPECS:
            self.assertGreater(bits, w)
            self.assertGreaterEqual(val, 1 << w)  # truncation changes value
            expect = val % (1 << w)
            bad = f"{bits}'b{val:0{bits}b}"
            # corrected line (right-sized literal, same value) passes gate
            good = f"assign q = {w}'d{expect};"
            self.assertTrue(value_gate(good, expect, bad),
                            (w, bits, val))
            # buggy line fails gate
            self.assertFalse(value_gate(f"assign q = {bad};", expect, bad),
                             (w, bits, val))

    def test_prompt_template_identical_to_frozen_r2(self):
        case = r2_cases()[0]
        self.assertEqual(task_prompt(case),
                         PROMPT_LINE.format(bug=case["bug"],
                                            buggy=case["buggy"]))

    def test_widths_cover_four_bands(self):
        widths = sorted({c["width"] for c in r2_cases()})
        self.assertEqual(widths, [4, 8, 12, 16])


if __name__ == "__main__":
    unittest.main()
