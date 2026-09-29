# P0 Gate Re-Review v3 — deltas since v2 (2026-09-29)

> `P0GATE_REVIEW.md` (v1) and `P0GATE_REVIEW_V2.md` stand frozen. This file
> records only what the fix campaign changed, with the same rule: misses
> diagnose layers, never authorize training/GPU spend.

## Fix campaign outcomes (all measured)

| Prescribed fix | Result |
|---|---|
| A_IRQ via sim | ✅ DONE — irq-lifecycle vector (`SIM_FRM_FPR.json`): enable→transfer→IRQ1→clear→IRQ0→status, FRM ≡ RTL exactly. (Formal stays NOT_EXECUTED with measured cause.) |
| FPR golden-vs-golden | ✅ DONE — 20-seed fuzz campaign: **0 mismatches (FPR 0.0)**; lint FPR 0 (2 known-benign warnings only) |
| T9 robustness | ✅ DONE — root cause was an under-specified prompt (no reset-value constraint), not a capability wall; with the semantic hint T9 closes round 2 (`P0D_T9RERUN.json`) |
| P0-B v2 at scale | ✅ DONE — n=10/kind × 4 kinds × 2 models (80 calls): llama 0.675 vs deepseek 0.40, baseline CONFIRMED (no flip); priors now v2-measured (`P0B_V2_BASELINE.json`) |
| Fault-hinted closure | ✅ SHIPPED — `diagnose()` feeds lint excerpts into closure prompts (unit-proven); live rescue count: strategy-level rescues (T9 via hint, T2/T6/T7 via skeletons), in-run rescue still 0.0 |
| Temperature plumbing | ✅ FIXED — BoN now has real diversity; n=1 drops closeable tasks, n=3 holds |

## Verdict deltas vs v2

| Gate | v2 | v3 | Delta |
|---|---|---|---|
| A — system works? | FAIL | **FAIL** | FPR measured 0.0; T9 closes; sim vectors 3/3. Open: A_IRQ formal, C-bands at loop scale |
| B — closure works? | FAIL | **FAIL** | Hints live + strategy rescues measured; in-run rescue still 0.0. Next: fault-localized regen (BluesFL-style), not more rounds |
| C — efficient? | PASS | **PASS** | Unchanged (v2 + skeleton numbers stand) |
| D — review scalable? | FAIL | **FAIL** | Instrument ready; no live human measurements yet |
| E — reproducible? | FAIL | **FAIL** | Unchanged (portability snapshot stands) |

**Decision: P0 GATE = NO-GO (third consecutive, narrowest).** Tally 1/5
with A measurably closer (3 of 4 v2 holes closed: FPR✓, T9✓, scale-priors✓;
A_IRQ-formal remains). The spine holds: audit 1.0 on every loop, formal,
and sim run; zero silent passes; every bake-off attempt recorded win-or-lose.

Standing authorization (unchanged): no training, no GPU. Next: live human
review (flips D same-day), fault-localized regen (B), sby-in-image +
benchmark portability (E), loop-at-scale C-bands (A).

Sign-off: PENDING (named human required per `policy.HUMAN_SIGNOFF_ACTIONS`).
