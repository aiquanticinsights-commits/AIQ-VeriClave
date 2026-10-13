"""Unit tests for requirement-to-evidence traceability (no infra)."""
import unittest

from trace import TERMINAL_STATES, Traceability


class TestTrace(unittest.TestCase):
    def test_full_chain(self):
        t = Traceability()
        t.register("REQ-001")
        t.attach("REQ-001", intent_id="I-1", artifact_id="A-1",
                 execution_id="E-1", evidence_id="H-1")
        t.close("REQ-001", "PASS")
        c = t.completeness()
        self.assertEqual((c["total"], c["closed"], c["completeness"]), (1, 1, 1.0))
        self.assertEqual(c["missing"], [])

    def test_missing_flagged(self):
        t = Traceability()
        t.register("REQ-001")
        t.register("REQ-002")
        t.close("REQ-001", "FAIL")
        c = t.completeness()
        self.assertEqual(c["completeness"], 0.5)
        self.assertEqual(c["missing"], ["REQ-002"])

    def test_all_terminal_states_accepted(self):
        t = Traceability()
        for i, s in enumerate(TERMINAL_STATES):
            t.register(f"R{i}")
            t.close(f"R{i}", s)
        self.assertEqual(t.completeness()["completeness"], 1.0)

    def test_bad_disposition_rejected(self):
        t = Traceability()
        t.register("R")
        with self.assertRaises(ValueError):
            t.close("R", "PROBABLY_FINE")

    def test_no_duplicates_no_silent_creation(self):
        t = Traceability()
        t.register("R")
        with self.assertRaises(ValueError):
            t.register("R")
        with self.assertRaises(KeyError):
            t.attach("GHOST", intent_id="I")
        with self.assertRaises(ValueError):
            t.attach("R", nonexistent_field="x")

    def test_empty_is_complete(self):
        self.assertEqual(Traceability().completeness()["completeness"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
