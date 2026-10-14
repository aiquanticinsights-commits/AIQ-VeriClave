"""Unit tests for the interactive human-arm runner (no humans needed)."""
import json
import os
import re
import tempfile
import unittest

import pilot_human
from pilot_human import (BANNED_TERMS, PHASES, PilotSession, PhaseError,
                         QUESTION_BANK, ask_number, ask_yes_no, run_checker_module,
                         seal_record)


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


class TestPhases(unittest.TestCase):
    def test_forward_only_order(self):
        s = PilotSession(clock=FakeClock())
        self.assertEqual(s.phase, "setup")
        s.begin_phase()
        with self.assertRaises(PhaseError):
            s.begin_phase()
        s.end_phase(expect="setup")
        self.assertEqual(s.phase, "attest")

    def test_wrong_expect_rejected(self):
        s = PilotSession(clock=FakeClock())
        s.begin_phase()
        with self.assertRaises(PhaseError):
            s.end_phase(expect="seal")

    def test_end_without_begin_rejected(self):
        with self.assertRaises(PhaseError):
            PilotSession(clock=FakeClock()).end_phase()

    def test_pause_resume_accounting(self):
        c = FakeClock()
        s = PilotSession(clock=c)
        s.begin_phase()
        c.advance(60)
        s.pause()
        c.advance(600)
        s.resume()
        c.advance(60)
        elapsed = s.end_phase()
        self.assertAlmostEqual(elapsed, 120.0)

    def test_pause_rules(self):
        s = PilotSession(clock=FakeClock())
        with self.assertRaises(PhaseError):
            s.pause()
        s.begin_phase()
        s.pause()
        with self.assertRaises(PhaseError):
            s.pause()
        s.resume()
        with self.assertRaises(PhaseError):
            s.resume()

    def test_all_phases_reachable(self):
        s = PilotSession(clock=FakeClock())
        for p in PHASES:
            s.begin_phase()
            s.end_phase(expect=p)
        self.assertEqual(s.phase, "seal")


class TestNeutrality(unittest.TestCase):
    def test_bank_has_no_banned_terms(self):
        for key, q in QUESTION_BANK.items():
            for term in BANNED_TERMS:
                self.assertNotIn(term.lower(), q.lower(), f"{key} leaks '{term}'")

    def test_bank_covers_needed_inputs(self):
        text = " ".join(QUESTION_BANK.values()).lower()
        self.assertIn("q1", text)
        self.assertIn("q2", text)
        self.assertIn("q3", text)
        for need in ("initials", "checker", "review", "satisfaction"):
            self.assertTrue(
                any(need in q.lower() for q in QUESTION_BANK.values()), need)

    def test_module_imports_nothing_answer_bearing(self):
        src = open(pilot_human.__file__, encoding="utf-8").read()
        # strip the BANNED_TERMS block itself (the denylist must name terms)
        body = re.sub(r"BANNED_TERMS = \(.*?\)", "", src, flags=re.S)
        for mod in ("p5_execute", "pilot_assist", "eval_harness", "router",
                    "import evidence", "from evidence", "oracle"):
            occurrences = [ln for ln in body.splitlines() if mod in ln]
            self.assertEqual(occurrences, [], mod)


class TestSandboxExec(unittest.TestCase):
    def _checker(self, body):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "chk.py")
        open(p, "w", encoding="utf-8").write(body)
        return p

    def test_result_contract(self):
        p = self._checker('RESULT = {"defects_found": 2, "mutants_total": 2, '
                          '"false_alarms": 0, "iterations": 3, "artifacts": ["a"]}\n')
        data = run_checker_module(p, timeout_s=60)
        self.assertEqual((data["defects_found"], data["false_alarms"]), (2, 0))

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            run_checker_module(r"C:\nonexistent\chk_xyz.py")

    def test_missing_key_rejected(self):
        p = self._checker('RESULT = {"defects_found": 1}\n')
        with self.assertRaises(ValueError):
            run_checker_module(p, timeout_s=60)

    def test_crash_reported_not_hidden(self):
        p = self._checker('raise RuntimeError("boom")\n')
        with self.assertRaises(RuntimeError):
            run_checker_module(p, timeout_s=60)


class TestSeal(unittest.TestCase):
    def test_seal_hash_matches_file(self):
        import hashlib
        with tempfile.TemporaryDirectory() as d:
            rec = {"engineer": "SS", "finished": "2026-10-14T10-00",
                   "tasks": {}}
            path, digest = seal_record(rec, d)
            self.assertTrue(path.endswith("P7_PILOT_HUMAN_ss-2026-10-14T10-00.json"))
            raw = open(path, "rb").read()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
            self.assertEqual(json.loads(raw)["engineer"], "SS")


class TestAskHelpers(unittest.TestCase):
    def test_yes_no(self):
        self.assertTrue(ask_yes_no("q", input_fn=lambda p: "yes", print_fn=lambda x: None))
        self.assertFalse(ask_yes_no("q", input_fn=lambda p: "n", print_fn=lambda x: None))
        answers = iter(["maybe", "y"])
        self.assertTrue(ask_yes_no("q", input_fn=lambda p: next(answers), print_fn=lambda x: None))

    def test_number(self):
        self.assertEqual(ask_number("q", input_fn=lambda p: "4.5", print_fn=lambda x: None), 4.5)
        answers = iter(["abc", "-1", "3"])
        self.assertEqual(ask_number("q", input_fn=lambda p: next(answers), print_fn=lambda x: None), 3.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
