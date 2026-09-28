---
name: ai-localize
description: BluesFL-style fault localization from VCD slices only — rank suspect blocks for seeded or real failures and report Top-1 rate and cost per bug.
---

# ai-localize

## What I do
- Build dataflow blockization for the target (statements with dataflow relations stay together).
- Slice instruction-execution paths with timestamps; read only time-annotated signal values from VCD (never full dumps — full dumps inflate cost ~6x).
- Walk (block, t) states via check_signals/read_values discipline; emit ranked suspect list with confidence scores.

## When to use me
Use for WS3 runs and any "where is this failure" triage on seeded or regression failures.

## Hard rules
1. VCD slices only — refuse tasks that require whole-waveform reasoning; say so explicitly.
2. Every ranked suspect cites block + timestamp + driving signals, never a bare line number without evidence.
3. Track wall-clock/sim time and inference cost per bug; stop if running past $1/bug without convergence.
4. Localization is a report, not a patch — never edit RTL in this lane (repair belongs to ai-close review).

## Report format
Ranked suspects with scores, Top-1 hit/miss vs ground truth (seeded) or triage module (real), $/bug, blocks inspected count.

## Developer-realism module (see blueprint §10)
- Convert each failing run to drift sentences with `vcd_events.py` (`drift_report()` → "signal X drifted at cycle N") before ranking; FSDB inputs convert via `fsdb2vcd` first.

## Token discipline (see blueprint §12)
- Keep VCD slices at the prompt tail (never cached); truncate tool outputs per `compact.py` caps.
