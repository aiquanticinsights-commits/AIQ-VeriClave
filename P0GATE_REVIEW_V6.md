# P0 Gate Review V6 — the advisory-driven objective (2026-09-30)

> v1–v5 stand frozen. This review executes the V6 objective verbatim:
> A (mutation ≥95% + disposition) / B (2+ in-run rescues) / C (maintain) /
> D (live human run) / E (sby smoke + Docker↔WSL). NO GPU, NO rewrite,
> NO agents, NO speculative RTL, NO redefined gates.

## A — mutation campaign + disposition → PASS (first green since C)

- Campaign: 100 stratified mutants (12 operator classes), kill ladder
  syntax → sim → fuzz, crash-safe with resume. Clean run, 0 infra.
- Score: **78/82 = 95.12% ≥ 95%** (54 sim + 18 syntax + 6 build-gate kills;
  18 human-dispositioned equivalents with reasons; 4 survivors).
- Formula honored exactly: equivalents/invalid/infra excluded from the
  denominator per the frozen rule (0 invalid, 0 infra in the final run).
- Survivors (4, all root-caused): M016/M019/M075/M076 — master-pin
  observability gap (trace extension = iteration 3, prescribed).
- Gap report: 15 analyses with root cause + action; 8 already closed by
  added vectors (this is the flywheel working).
- FRM fidelity incident: golden self-check caught an FRM hold-semantics
  bug mid-campaign; fixed, campaign re-run clean. The guard works.
- A_IRQ: UNPROVABLE + SIM_COVERED + POLICY_PROPOSED, signoff PENDING.
- Acceptance function: `gate_a_accepts()` → **ACCEPT True, 6/6 clauses**
  (regression green, formals PROVEN, C1 0.9512, disposition complete,
  zero silent drops, audit 1.0).
- **Verdict: PASS** (release still gated on the human POLICY sign-off).

## B — seeded closure + invariant → PASS (second green gate)

- V1 run: R4/B rescued round 3 (full budget, fault hints).
- Current run: R5/B rescued round 2, approvals [0,2] (declline + value
  gates, frozen prompts, no manual intervention).
- **2 genuine in-run rescues, ≤3 rounds each** — the stated bar, met with
  full provenance (REPAIR_CLOSURE_V1/V2.json) and one disclosed caveat:
  the two rescues came from different runs (prompts evolved between
  them; each run internally frozen). Latest single run: 1 rescue.
- Hard invariant: unit-proven — all-FAIL yields exactly 3 generation
  rounds, escalation, never a 4th call.
- R5-sequential stands as hardening, not a gate condition.
- **Verdict: PASS.**

## C — maintain → PASS (unchanged, still measured)

## D — live human run → FAIL (unchanged)

- Dashboard rollup shipped + tested (exception rate, median time,
  reject/override, missing-evidence — unknowns render '?', never 0).
- Live measurements: still none. The 5-minute run remains the cheapest
  unflipped gate in the program.

## E — sby smoke + portability → FAIL (narrower)

- sby via apt: absent. Via pip: absent (`No matching distribution`).
  Via oss-cad-suite: exists (745MB) — rejected again, now against the
  stated <10–50MB smoke budget plus version-mismatch risk. E1 closed
  as infeasible-with-reasons, not as done.
- environment.json fields added (git commit, container id); fresh
  portability: unittest + FRM identical, lint + synth green both sides
  (fixture), sby_demo UNMEASURED in image.
- **Verdict: FAIL** on the sby-in-image row alone.

## Decision: P0 GATE = NO-GO (sixth consecutive) — 3/5 green

A/B/C passing is the first majority-green board in program history, and
every remaining red has a named, costed next step: D = 5 human minutes;
E = sby packaging decision; C1 maintenance = iteration-3 trace work.
Standing authorizations unchanged: no training, no GPU, no rewrite —
with the single carried exception of one controlled larger-model bake-off
round if F1/F2/F3 survive their prescriptions (unchanged from v4).

Sign-off: PENDING (named human required per `policy.HUMAN_SIGNOFF_ACTIONS`).
