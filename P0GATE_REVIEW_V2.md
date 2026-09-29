# P0 Gate Re-Review — Gates A–E, second verdict (2026-09-29)

> Supersedes nothing: `P0GATE_REVIEW.md` (v1, NO-GO) stands as frozen evidence.
> This file re-measures after prescriptions 1–5. Same rule: misses diagnose
> layers, never authorize training/GPU spend. No REVIEW_*.json exists yet
> (live human review pending) — Gate D is verdictable on that fact alone,
> and is.

## What changed since v1

| Prescription | Outcome (measured) |
|---|---|
| Elitist closure | T2/T7 backfire class gone; weak plurality escalates instead of closing |
| Constrained generation | 3/5 rescued (T2/T6/T7); T1 via formal next row |
| Formal adapter | A_ACK + A_CYC PROVEN (sby, BMC-20, ~1s); T1 PROVEN in-loop round 2 |
| Efficiency instrumentation | First real Gate-C data (below) |
| Sim/FRM wiring | FRM ≡ RTL exactly, 18/18 events, 2 vectors |
| Portability probe | unittest + FRM traces identical WSL↔Docker |
| Review dashboard | Instrument shipped (`review.py`); no live measurements yet |

## Gate A — does the system work? → STILL FAIL (narrowed)

| Check | v1 | v2 (now) |
|---|---|---|
| Syntax/lint | ✅ | ✅ (unchanged) |
| Simulation/FRM | NOT_EXECUTED | ✅ PASS — FRM ≡ RTL 18/18 events (`SIM_FRM_WB_DMA.json`); live co-sim test in suite |
| Formal | NOT_EXECUTED | ✅ PASS (bounded) — A_ACK + A_CYC proven; T1 property proven in-loop (`FORMAL_WB_DMA.json`, `P0D_T1FORMAL.json`) |
| Formal IRQ | NOT_EXECUTED | NOT_EXECUTED with measured cause (no hierarchical refs in toolchain; `hier.sby` probe) |
| Mutation-kill | 0/2 escalate | 1/2 close (T6 ✅ via skeleton; T9 genuine model error, correctly rejected) |
| Traceability | ✅ req-ids | ✅ + slot mention-gates + requirement_ids in formal evidence |
| Evidence/audit | 1.0 | 1.0 everywhere (loop, formal, sim, bake-off) |
| Golden-vs-golden FPR | unmeasured | unmeasured |
| C1/C2 ≥95% at scale | unproven | unproven (n=1–2 samples/kind; bands need P0-B v2 scale) |

Three of six v1 holes closed with machine evidence. FAIL stands on: A_IRQ
formal, T9-class edits, FPR unmeasured, C-bands at scale unproven.

## Gate B — does closure work? → STILL FAIL (mechanics pass, rescue rate 0)

- Elitism verified: 0 destroyed winners across v2 + skeleton + T1 runs
  (was: T2/T7 destroyed in v1).
- Strategy-level rescue works: 3/5 skeleton + T1-via-formal closed tasks
  that free-form could not (4 tasks total across runs).
- In-run rescue rate still 0.0: no task failing at round 1 was ever rescued
  by rounds 2–3 regen (v2 closure_success 0.0; skeleton 0.0 — all closes
  were first-pass at round 2).
- first_pass_rate 0.556, avg iterations 2.44 (v2).

The loop preserves and selects but does not yet repair mid-run. Next layer:
repair-oriented closure (fault-localized regen hints), not more rounds.

## Gate C — is the system efficient? → PASS (first green gate)

Measured (nominal local pricing + wall clock, misses counted):

| Run | Wall | Tokens | Cost (nominal) |
|---|---|---|---|
| P0-D v2 (9 tasks) | 2822s (~5 min/task) | 13,798 | $0.0017 ($0.00018/task) |
| Skeleton 5-task | 392s (~78s/task) | 5,623 | $0.0004 ($0.00008/task) |
| T1 formal | 90.7s | 1,288 | formal proofs ~seconds each |

Nominal cost is ~3 orders of magnitude under the $0.50/task band; the true
budget is wall-clock on local CPU (~1–5 min/task). PASS with the wall-clock
caveat recorded, not assumed away.

## Gate D — is human review scalable? → FAIL (unchanged, correctly)

- Instrument shipped and tested: `review.py` (exception-first,
  `--exceptions-only`, per-item timing, reject/override reasons) + 8 unit
  tests + committed input reports with `tasks_detail`.
- Live measurements: NONE — no REVIEW_*.json exists. Fields remain None by
  design, never fabricated. The gate flips the day a named human runs the
  6-item review, not before.

## Gate E — is the result reproducible? → FAIL (narrowed)

- ✅ unittest 206 green on WSL, Docker, and CI alike.
- ✅ FRM fixed-vector traces bit-identical WSL↔Docker (sha 22b84d4eb8e9dc32).
- ✅ Same WSL2 kernel both sides; version-drift only (python/tools).
- ❌ lint/synth/sby_demo UNMEASURED inside the image (no sibling RTL, no
  sby) — recorded findings.
- ❌ Live benchmark (LMStudio + models) single-env only.

## Decision: P0 GATE = NO-GO (second consecutive, narrower)

Tally: 1 PASS (C), 4 FAIL (A, B, D, E) — versus 0/5 at v1, with every fail
carrying strictly less unknown than before. The spine holds throughout:
audit 1.0 on every run, zero silent passes, every gap dispositioned.

Authorized next (no training, no GPU):
1. Repair-oriented closure (fault-hinted regen) — attacks Gate B rescue 0.
2. Live human review (6 items, ~5 min) — flips Gate D the same day.
3. sby into the Docker image + sibling-RTL fixture — clears Gate E rows.
4. A_IRQ via sim-backed irq coverage + T9-class edit robustness — clears
   Gate A residues; then P0-B v2 at n≥20/kind for the C-bands.

Sign-off: PENDING (named human required per `policy.HUMAN_SIGNOFF_ACTIONS`).
