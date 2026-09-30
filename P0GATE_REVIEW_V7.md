# P0 Gate Re-Review V7 — live human review flips D (2026-09-30)

> v1–v6 stand frozen. This review consumes the first live human-review
> record (`REVIEW_p0d-20260929-142344.json`, reviewer SSB, 5 items) and the
> two engineering changes it forced. Same rule throughout.

## The review (verbatim grounds, reviewer-supplied)

| Task | Machine | Human | Time | Ground |
|---|---|---|---|---|
| T9-status-fix | escalated | accept | 4.7s | (no artifact to judge; escalation agreed) |
| T1-sva-ack | closed (formally proven) | **reject** | 37.6s | proven artifact ≠ proven requirement: equating ack to past request never establishes the required Wishbone ACK timing |
| T2-sva-irq | closed (lint-clean) | **override** | 32.7s | antecedent `$rose(irq) && !irq` self-contradictory (0→1 vs ==0 same cycle) → vacuous property |
| T6-width-fix | closed | skip | 7.9s | unreviewed (recorded, not hidden) |
| T7-sva-cyc | closed | accept | 4.7s | — |

Dashboard: 20% human review rate, 18.7s median decision, 25% reject,
25% override, evidence opened on 4/4 decided items, 1 unreviewed.

## What the two catches prove (and cost the machine)

- **T1**: the deepest possible verification outcome — a *machine-proven*
  artifact rejected because proof-of-artifact is not proof-of-requirement.
  No deterministic rule can close this gap (intent lives with the author);
  it is the standing justification for mandatory human sign-off, now with
  a measured instance instead of a slogan.
- **T2**: a genuine verifier hole — lint-clean vacuous properties sailed
  through Judge. Generalized deterministically the same day:
  `skeletons.find_vacuity()` (same-antecedent `$rose(X)&&!X` /
  `$fell(X)&&X`), wired into P0-D judging for T2/T7 (3-key bar), with a
  regression test built from the reviewer's exact artifact. Consequent-side
  vacuity remains open (documented in code).

## Verdicts

| Gate | Verdict | Ground |
|---|---|---|
| A — system works? | **PASS** | Unchanged from v6 (C1 95.12%, acceptance fn green) |
| B — closure works? | **PASS** | Unchanged from v6 (2 in-run rescues + invariant) |
| C — efficient? | **PASS** | Unchanged, still measured |
| D — review scalable? | **PASS** | First live data: 20% review rate, 18.7s median, 0 missing-evidence surprises (T9's empty artifact counted, not hidden) |
| E — reproducible? | **FAIL** | Unchanged: sby-in-image infeasible within budget, live-benchmark portability open |

**Decision: P0 GATE = NO-GO (seventh consecutive) — 4/5 green.** The
remaining red is exactly one infrastructure row (sby packaging) plus one
benchmark run. No training, no GPU, no rewrite authorized or needed.

Sign-off: PENDING (named human required per `policy.HUMAN_SIGNOFF_ACTIONS`).
