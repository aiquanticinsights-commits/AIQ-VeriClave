"""Interactive human-arm runner (P7 pilot) — lab assistant, never a participant.

What this runner does: timers, attestation, sandboxed execution of YOUR
checker module, record-keeping, sealing. What it never does: author checks,
propose code changes, anticipate results, or consult restricted materials.
All user-facing questions come from QUESTION_BANK below (fixed strings,
reviewable, neutrality-tested in test_pilot_human.py).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time

TASKS = ("round-robin-arbiter", "interrupt-controller")

# Fixed, content-neutral question bank (process wording only; the denylist
# below is the enforced counterpart, tested in test_pilot_human.py).
QUESTION_BANK = {
    "attest_no_peek": "Q1: This session, have you worked only from the allowed materials (spec sheets, runbook, walkthrough)? (yes/no)",
    "attest_no_ai": "Q2: This session, did you author everything yourself with no AI assistance? (yes/no)",
    "attest_spec_only": "Q3: Are you working from the spec sheets only? (yes/no)",
    "initials": "Your initials (used in the output filename):",
    "checker_path": "Path to your checker module file for this task:",
    "phase_done": "Type DONE when finished (timer stops):",
    "review_minutes": "Review minutes, as a number:",
    "reviewer": "Reviewer initials (your own are fine):",
    "iterations": "Debug cycles completed, as a whole number:",
    "satisfaction": "Satisfaction 1-5, as a whole number:",
    "satisfaction_note": "One honest line on the experience:",
    "pause_note": "Paused — type RESUME to continue the clock:",
}

# Terms that must never appear in user-facing prompts (expected-outcome or
# assisted-artifact leakage). Enforced by test_pilot_human.py.
BANNED_TERMS = (
    "P7_PILOT_ASSISTED", "P5_EXECUTION", "expected", "should find",
    "should kill", "verdict", "answer is", "correct ranking",
    "oracle", "p5_execute", "pilot_assist",
)

PHASES = ("setup", "attest", "task-1-author", "task-1-measure",
          "task-1-review", "task-2-author", "task-2-measure",
          "task-2-review", "satisfaction", "seal")


class PhaseError(Exception):
    pass


class PilotSession:
    """Forward-only phased session with pause-aware timing."""

    def __init__(self, clock=time.monotonic) -> None:
        self._clock = clock
        self.phase_idx = 0
        self.log: list[dict] = []
        self._phase_start: float | None = None
        self._paused_total = 0.0
        self._pause_start: float | None = None
        self.times: dict[str, float] = {}

    @property
    def phase(self) -> str:
        return PHASES[self.phase_idx]

    def begin_phase(self) -> None:
        if self._phase_start is not None:
            raise PhaseError("phase already open; end it first")
        self._phase_start = self._clock()
        self._paused_total = 0.0
        self._pause_start = None
        self.log.append({"event": "begin", "phase": self.phase})

    def pause(self) -> None:
        if self._phase_start is None or self._pause_start is not None:
            raise PhaseError("nothing pausable right now")
        self._pause_start = self._clock()
        self.log.append({"event": "pause", "phase": self.phase})

    def resume(self) -> None:
        if self._pause_start is None:
            raise PhaseError("not paused")
        self._paused_total += self._clock() - self._pause_start
        self._pause_start = None
        self.log.append({"event": "resume", "phase": self.phase})

    def end_phase(self, expect: str = "") -> float:
        """Close current phase; `expect` guards against skipping ahead."""
        if self._phase_start is None:
            raise PhaseError("no open phase")
        if expect and expect != self.phase:
            raise PhaseError(f"expected phase {expect}, currently {self.phase}")
        if self._pause_start is not None:
            self.resume()
        elapsed = self._clock() - self._phase_start - self._paused_total
        self.times[self.phase] = round(elapsed, 1)
        self.log.append({"event": "end", "phase": self.phase,
                         "seconds": round(elapsed, 1)})
        self._phase_start = None
        if self.phase_idx + 1 < len(PHASES):
            self.phase_idx += 1
        return elapsed


def ask_yes_no(prompt: str, input_fn=input, print_fn=print) -> bool:
    while True:
        ans = input_fn(prompt + " ").strip().lower()
        if ans in ("yes", "y"):
            return True
        if ans in ("no", "n"):
            return False
        print_fn("Please answer yes or no.")


def ask_number(prompt: str, input_fn=input, print_fn=print,
             lo: float = 0.0) -> float:
    while True:
        raw = input_fn(prompt + " ").strip()
        try:
            val = float(raw)
        except ValueError:
            print_fn("Please enter a number.")
            continue
        if val < lo:
            print_fn(f"Please enter a number >= {lo}.")
            continue
        return val


ATTEST_KEYS = ("attest_no_peek", "attest_no_ai", "attest_spec_only")


def attest_gate(input_fn=input, print_fn=print) -> dict:
    """Scripted attestation gate: all three answers must be yes (uniform
    yes=clean mapping across Q1/Q2/Q3). Echoes the recorded meaning back
    so ambiguity is caught at answer time, not post-hoc. Returns
    {"clean": bool, "answers": {...}, "abort_reason": str|None}.
    No tasks may start unless clean is True."""
    answers = {}
    for key in ATTEST_KEYS:
        answers[key] = ask_yes_no(QUESTION_BANK[key], input_fn, print_fn)
    bad = [k for k, v in answers.items() if not v]
    if not bad:
        print_fn("Recorded: clean on Q1 (allowed materials only), Q2 (no "
                 "AI authoring), Q3 (spec sheets only). Proceeding.")
        return {"clean": True, "answers": answers, "abort_reason": None}
    reason = ("attestation not clean: "
              + ", ".join(f"{k}=no" for k in bad)
              + " — no tasks started, no data collected (protocol A1)")
    print_fn("ABORT. " + reason)
    return {"clean": False, "answers": answers, "abort_reason": reason}


def run_checker_module(path: str, timeout_s: int = 600) -> dict:
    """Execute the HUMAN's checker file in a subprocess; return its JSON.

    Contract: the file prints one JSON object to stdout with keys
    defects_found, mutants_total, false_alarms, iterations, artifacts (list).
    The runner never inspects checker logic — only this output contract.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"checker file not found: {path}")
    prog = ("import json, runpy, sys; "
            "ns = runpy.run_path(sys.argv[1]); "
            "print(json.dumps(ns.get('RESULT', {})))")
    out = subprocess.run([sys.executable, "-c", prog, path],
                         capture_output=True, text=True, timeout=timeout_s)
    if out.returncode != 0:
        raise RuntimeError(f"checker exited {out.returncode}: {out.stderr[-1000:]}")
    lines = [ln for ln in out.stdout.splitlines() if ln.strip().startswith("{")]
    if not lines:
        raise ValueError("checker printed no JSON RESULT object")
    data = json.loads(lines[-1])
    for k in ("defects_found", "mutants_total", "false_alarms", "iterations"):
        if k not in data:
            raise ValueError(f"checker RESULT missing key '{k}'")
    return data


def seal_record(record: dict, outdir: str) -> tuple[str, str]:
    """Write sealed JSON + return (path, sha256). Post-seal it is read-only
    to this runner: reruns create new files, never amend."""
    initials = record.get("engineer", "xx").strip().lower() or "xx"
    stamp = record.get("finished", "noseal")
    safe_stamp = "".join(c if (c.isalnum() or c in "-_") else "-" for c in stamp)
    path = os.path.join(outdir, f"P7_PILOT_HUMAN_{initials}-{safe_stamp}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    digest = hashlib.sha256(open(path, "rb").read()).hexdigest()
    try:
        os.chmod(path, 0o444)
    except OSError:
        pass  # best effort; hash in ledger is the real seal
    return path, digest
