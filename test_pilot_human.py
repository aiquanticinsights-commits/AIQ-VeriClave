"""Unit tests for the interactive human-arm runner (no humans needed)."""
import json
import os
import re
import tempfile
import unittest

import pilot_human
from pilot_human import (BANNED_TERMS, PHASES, PilotSession, PhaseError,
                         QUESTION_BANK, ask_number, ask_yes_no, attest_gate,
                         run_checker_module, seal_record)


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


def _scripted_answers(*words):
    it = iter(words)
    echoed = []

    def input_fn(prompt):
        return next(it)

    def print_fn(msg):
        echoed.append(msg)

    return input_fn, print_fn, echoed


class TestAttestGate(unittest.TestCase):
    """Regression tests for the 2026-10-14 abort: the old Q2 wording
    ('have you used no AI assistance?') admitted two readings of 'no'.
    The gate requires uniform yes=clean and echoes the recorded meaning."""

    def test_q2_wording_is_affirmative(self):
        q2 = QUESTION_BANK["attest_no_ai"]
        self.assertIn("Q2", q2)
        self.assertIn("did you", q2.lower())
        self.assertNotRegex(q2.lower(), r"\bused no\b")

    def test_all_yes_is_clean_with_echo(self):
        input_fn, print_fn, echoed = _scripted_answers("yes", "yes", "yes")
        r = attest_gate(input_fn, print_fn)
        self.assertTrue(r["clean"])
        self.assertIsNone(r["abort_reason"])
        self.assertEqual(r["answers"],
                         {"attest_no_peek": True, "attest_no_ai": True,
                          "attest_spec_only": True})
        self.assertTrue(any("clean on Q1" in m for m in echoed), echoed)

    def test_each_no_aborts_naming_the_question(self):
        for i, key in enumerate(("attest_no_peek", "attest_no_ai",
                                 "attest_spec_only")):
            words = ["yes", "yes", "yes"]
            words[i] = "no"
            input_fn, print_fn, echoed = _scripted_answers(*words)
            r = attest_gate(input_fn, print_fn)
            self.assertFalse(r["clean"], key)
            self.assertIn(f"{key}=no", r["abort_reason"], key)
            self.assertTrue(any("ABORT" in m for m in echoed), key)

    def test_runbook_has_attestation_procedure(self):
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, "HUMAN_ARM_RUNBOOK.md"),
                  encoding="utf-8") as f:
            text = f.read()
        self.assertIn("## Attestation procedure", text)
        self.assertIn("yes = clean", text)


class TestMainRunner(unittest.TestCase):
    def _checker(self, body):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "chk.py")
        open(p, "w", encoding="utf-8").write(body)
        return p

    def _run(self, words, outdir):
        it = iter(words)

        def input_fn(prompt):
            try:
                return next(it)
            except StopIteration:
                return "DONE"

        echoed = []
        code = pilot_human.main(input_fn=input_fn, print_fn=echoed.append,
                                clock=FakeClock(), outdir=outdir)
        return code, echoed

    def test_clean_session_seals_two_tasks(self):
        chk = self._checker('RESULT = {"defects_found": 2, "mutants_total": 2, '
                            '"false_alarms": 0, "iterations": 1, '
                            '"artifacts": ["tb.sv"]}\n')
        words = ["SS", "yes", "yes", "yes",
                 "DONE", chk, "30", "SS", "ok",
                 "DONE", chk, "20", "SS", "ok",
                 "5", "clean"]
        d = tempfile.mkdtemp()
        code, echoed = self._run(words, d)
        self.assertEqual(code, 0)
        files = [f for f in os.listdir(d) if f.startswith("P7_PILOT_HUMAN_")]
        self.assertEqual(len(files), 1)
        rec = json.load(open(os.path.join(d, files[0]), encoding="utf-8"))
        self.assertFalse(rec.get("aborted", False))
        self.assertTrue(rec["complete"])
        self.assertEqual(rec["engineer"], "SS")
        self.assertEqual(set(rec["tasks"]), set(pilot_human.TASKS))
        self.assertEqual(rec["tasks"]["round-robin-arbiter"]["defects_found"], 2)
        self.assertEqual(rec["satisfaction"], 5.0)
        self.assertEqual(set(rec["phases_seconds"]),
                         set(pilot_human.PHASES) - {"seal"})

    def test_abort_blocks_all_task_data(self):
        d = tempfile.mkdtemp()
        code, echoed = self._run(["SS", "yes", "no", "yes"], d)
        self.assertEqual(code, 1)
        files = [f for f in os.listdir(d) if f.startswith("P7_PILOT_ABORTED_")]
        self.assertEqual(len(files), 1)
        rec = json.load(open(os.path.join(d, files[0]), encoding="utf-8"))
        self.assertTrue(rec["aborted"])
        self.assertEqual(rec["tasks"], {})
        self.assertIn("attest_no_ai=no", rec["abort_reason"])
        self.assertTrue(any("ABORT" in m for m in echoed))

    def test_incomplete_session_not_submittable(self):
        bad = os.path.join(tempfile.mkdtemp(), "missing.py")
        words = ["AA", "yes", "yes", "yes",
                 "DONE", bad, "no", "0", "AA", "x",
                 "DONE", "not-a-file", "no", "0", "AA", "x",
                 "5", "note"]
        d = tempfile.mkdtemp()
        code, echoed = self._run(words, d)
        self.assertEqual(code, 3)
        files = os.listdir(d)
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].startswith("P7_PILOT_INCOMPLETE_"), files)
        rec = json.load(open(os.path.join(d, files[0]), encoding="utf-8"))
        self.assertFalse(rec["complete"])
        self.assertNotEqual(rec.get("incomplete_reasons"), [])
        for task in pilot_human.TASKS:
            self.assertIsNone(rec["tasks"][task]["defects_found"])
        self.assertTrue(any("NOT valid pilot evidence" in m for m in echoed))


if __name__ == "__main__":
    unittest.main(verbosity=2)
