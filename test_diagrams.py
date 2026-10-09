"""Tests for the DIAGRAMS.md alignment cleanup: no hard-coded training
commitments, future work labeled as future, background diagrams labeled."""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def diagrams():
    with open(os.path.join(HERE, "DIAGRAMS.md"), encoding="utf-8") as f:
        return f.read()


def section(text, title):
    m = re.search(r"^### " + re.escape(title) + r"\b(.*?)(?=^### |\Z)",
                  text, re.M | re.S)
    assert m, title
    return m.group(1)


class TestDiagramLabels(unittest.TestCase):
    def test_d22_model_agnostic_and_gated(self):
        body = section(diagrams(), "D22")
        self.assertNotIn("Qwen3-Coder-Next", body)
        self.assertIn("readiness", body.lower())
        self.assertIn("only if justified", body)

    def test_d19_no_false_adoption_claim(self):
        body = section(diagrams(), "D19")
        self.assertNotIn("adopted in rewards.py", body)

    def test_background_diagrams_labeled(self):
        text = diagrams()
        for title, label in (("D01", "BACKGROUND ONLY"),
                             ("D02", "BACKGROUND ONLY"),
                             ("D03", "REFERENCE ONLY")):
            self.assertIn(label, section(text, title), title)


if __name__ == "__main__":
    unittest.main()
