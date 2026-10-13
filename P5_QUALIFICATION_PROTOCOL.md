# P5 Independent Qualification Protocol (P4-14 draft — not yet frozen)

> Entry requires the P4 exit gate (core ≥E2, critical E3 where frozen). This
> draft freezes nothing; freezing happens once, in a signed P5-freeze review.

## Frozen-before-execution list
1. Qualification protocol version (this document at a tagged commit).
2. Held-out design families (`P4_HELDOUT_v1.json` or its v2 successor — frozen, disjoint from all training/prompts/thresholds/mutation templates/judge tuning).
3. Model + configuration (IDs, quantizations, temperatures, seeds, BoN widths, router version).
4. Acceptance criteria (C1–C5 bars + FA=0 + cost band, copied from `P4_BENCH_v1.json`, never restated).
5. Environment pins (Linux 64-bit canonical; tool versions via `repro.envelope()`; Docker image digest where used).

## Execution rules
- Independent executor (not the model/system authors) runs the frozen protocol.
- No benchmark leakage: qualification RTL unseen by every authoring-stage artifact.
- Reproduce twice (two runners); disagreements become findings, not averages.
- Record ALL failures; false-positive rate and human-review burden quantified as first-class metrics.
- Limitations documented in the verdict, including capability walls carried from P2/P3.

## Verdict shape
Per capability: PASS/FAIL vs frozen bars + maturity label (target E3) +
evidence pointers + reviewer sign-off. A FAIL closes as a finding (P2-M3
pattern), never as a scope cut.

## Explicit non-goals for P5
No training, no threshold edits mid-run, no family swaps, no metric redefinitions.
Any of those restarts P5 as a new version, with a ledger row explaining why.
