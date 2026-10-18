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


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M")


def _ask_text(key: str, input_fn, print_fn, default: str = "") -> str:
    prompt = QUESTION_BANK.get(key, key.replace("_", " ") + ":")
    raw = input_fn(prompt + " ").strip()
    return raw or default


def _wait_done(input_fn, print_fn) -> None:
    prompt = QUESTION_BANK.get("phase_done", "Type DONE when finished:")
    while input_fn(prompt + " ").strip().upper() != "DONE":
        print_fn("Type DONE to end this phase.")


def _repo_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, timeout=10)
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def main(input_fn=input, print_fn=print, clock=time.monotonic,
         outdir: str | None = None) -> int:
    """Drive one full human-arm session from start to sealed record.

    Returns 0 on a sealed session, 1 on an attestation abort (sealed abort
    record), 2 if the record could not be sealed. All prompts come from
    QUESTION_BANK; the runner never authors checks or anticipates results.
    """
    outdir = outdir or os.getcwd()
    session = PilotSession(clock=clock)
    started = _now()
    print_fn("\n=== AIQ-VeriClave human-arm session (no AI assistance) ===")
    print_fn("Work only from the blinded starter pack, runbook, and "
             "walkthrough. Never open assisted-arm outputs.\n")

    session.begin_phase()
    initials = _ask_text("initials", input_fn, print_fn, default="xx")
    commit = _repo_commit()
    session.end_phase(expect="setup")

    session.begin_phase()
    gate = attest_gate(input_fn, print_fn)
    session.end_phase(expect="attest")
    if not gate["clean"]:
        record = {"engineer": initials, "repo_commit": commit,
                  "started": started, "finished": _now(), "aborted": True,
                  "abort_reason": gate["abort_reason"], "attestation": gate,
                  "tasks": {}, "phases_seconds": session.times,
                  "log": session.log, "runner": "pilot_human"}
        try:
            path, digest = seal_record(record, outdir)
        except OSError as exc:
            print_fn(f"Could not seal abort record: {exc}")
            return 2
        print_fn(f"\nSession aborted. Sealed abort record:\n  {path}\n"
                 f"  sha256 {digest}")
        return 1

    results: dict[str, dict] = {}
    total = len(TASKS)
    for i, task in enumerate(TASKS, start=1):
        session.begin_phase()
        print_fn(f"\n[task {i}/{total}] {task} — author phase (4h cap)")
        _wait_done(input_fn, print_fn)
        author_s = session.end_phase(expect=f"task-{i}-author")

        session.begin_phase()
        print_fn(f"[task {i}/{total}] {task} — measure phase")
        checker = ""
        data = None
        while True:
            checker = _ask_text("checker_path", input_fn, print_fn)
            if not checker:
                print_fn("A checker path is required to measure.")
                continue
            try:
                data = run_checker_module(checker)
            except (FileNotFoundError, ValueError, RuntimeError) as exc:
                print_fn(f"Checker run failed: {exc}")
                if not ask_yes_no("Retry this task's measurement?",
                                  input_fn, print_fn):
                    break
                continue
            break
        measure_s = session.end_phase(expect=f"task-{i}-measure")
        results[task] = {
            "authoring_seconds": round(author_s, 1),
            "measure_seconds": round(measure_s, 1),
            "checker": checker,
            "defects_found": None if data is None else data["defects_found"],
            "mutants_total": None if data is None else data["mutants_total"],
            "false_alarms": None if data is None else data["false_alarms"],
            "iterations": None if data is None else data["iterations"],
            "artifacts": [] if data is None else list(data.get("artifacts", [])),
        }

        session.begin_phase()
        results[task]["review_minutes"] = ask_number(
            QUESTION_BANK.get("review_minutes", "Review minutes:"),
            input_fn, print_fn)
        results[task]["reviewer"] = _ask_text("reviewer", input_fn, print_fn)
        results[task]["notes"] = _ask_text("notes", input_fn, print_fn)
        session.end_phase(expect=f"task-{i}-review")

    session.begin_phase()
    satisfaction = ask_number(
        QUESTION_BANK.get("satisfaction", "Satisfaction (1-5):"),
        input_fn, print_fn)
    satisfaction_note = _ask_text("notes", input_fn, print_fn)
    session.end_phase(expect="satisfaction")

    session.begin_phase()
    record = {"engineer": initials, "repo_commit": commit, "started": started,
              "finished": _now(), "satisfaction": satisfaction,
              "satisfaction_note": satisfaction_note, "tasks": results,
              "phases_seconds": session.times, "log": session.log,
              "runner": "pilot_human"}
    try:
        path, digest = seal_record(record, outdir)
    except OSError as exc:
        print_fn(f"Could not seal record: {exc}")
        return 2
    print_fn(f"\nSession sealed:\n  {path}\n  sha256 {digest}")
    session.end_phase(expect="seal")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
