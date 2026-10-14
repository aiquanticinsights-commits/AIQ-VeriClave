# Human-Arm Runbook (P7 pilot, human baseline — PENDING)

> This runbook is the complete procedure for the human-only arm. It is
> executed by a human verification engineer, not by automation. No simulated
> humans, anywhere, ever.

## Prerequisites
- Read `PILOT_PROTOCOL.md` (design, measures, acceptance) and this file.
- Checkout the exact commit recorded in the assisted run's environment
  (`P7_PILOT_ASSISTED.json` has no commit pin — record yours below).
- Use ONLY the frozen tasks: `round-robin-arbiter`, `interrupt-controller`
  (definitions in `pilot_assist.py:TASKS`). Same mutants, same bars.

## Procedure (per task, capped at 4 hours each)
1. Record start time. Work unassisted: no AIQ-VeriClave pipeline, no LLM
   help beyond what the protocol allows (none). Editor + simulator + docs.
2. Author verification artifacts (testbench/checkers/assertions) for the
   requirement; log authoring time separately from debug/review time.
3. Run against golden + all seeded mutants listed in `p5_execute.FAMILIES`;
   record kills, false alarms, iterations (each debug cycle = 1 iteration).
4. Log review time (self-review + any peer review, with reviewer initials).
5. Fill one row per task in the table below; attach evidence files.

## Timesheet format (append rows, never edit)

| Task | Authoring (min) | Debug iters | Review (min) | Defects | False alarms | Satisfaction (1–5) | Notes |
|---|---|---|---|---|---|---|---|
| round-robin-arbiter | | | | /2 | | | |
| interrupt-controller | | | | /3 | | | |

## Submission
- Save filled timesheet + evidence as `P7_PILOT_HUMAN_<initials>.json`/`.md`.
- Open a PR titled `[pilot] human-arm results <initials>`; a maintainer runs
  the blinded comparison (graders see artifacts + evidence only).
- E4 is decided ONLY on that comparison per protocol acceptance — never on
  the assisted arm alone.

## Hard rules
- Same tasks, same mutants, same bars as the assisted arm. Any deviation =
  new protocol version + ledger row, not a quiet edit.
- Proprietary RTL stays local; only aggregate metrics leave the bench.
- Report wall-clock honestly, including stuck time. Negative results are findings.
