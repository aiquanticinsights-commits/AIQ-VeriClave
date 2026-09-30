# P0 Gate Re-Review v5 — Vivado validation + repair v2 (2026-09-30)

> v1–v4 stand frozen. This review folds in the Failure-Fixes program and
> the Vivado validation runs. Same rule: misses diagnose layers, never
> authorize unjustified spend.

## New evidence since v4

| Item | Result |
|---|---|
| Failure-Fixes demo (`GATES_ABDE.json`) | 8/8: 4 correct versions PROVE + 4 seeded bugs FAIL as negative controls (sby) |
| Real-block formal (`FORMAL_REALBLOCKS.json`) | wb_watchdog programmed ack+pulse PROVEN; wb_safety reset values PROVEN; 50M-cycle timeout-entry ABSTRACT per policy |
| Vivado validation (`VIVADO_GATES.json`) | 4/4 synth+route, DRC clean, internal WNS +4.5..+8.9ns @100MHz, ledger audit 1.0 |
| Repair modes v2 | line/declline skeletons, value-gate doctrine (8'd15 accepted as == 15), interface-preservation rule; latest: A=4/6, B=4/6 (R5/B closes on corrected gates in probe; R2 arithmetic slip persists; R4 flips with seed) |
| SIM slots | CLOSED via sequential+few-shot+closure (verdict/equiv/completed True) |
| Suite | 254 tests green (WSL + Docker + CI) |

## Verdicts

| Gate | Verdict | Ground |
|---|---|---|
| A — system works? | **FAIL** | syntax ✅; sim ✅✅✅ (vectors, fuzz 0/20, lifecycle); formal 5 properties + T1 in-loop proven, A_IRQ sim-covered; mutation: T6/T9 close, R2/R5 open; trace ✅; evidence ✅; FPR ✅; C1 swarm + loop-at-scale open |
| B — closure works? | **FAIL** | Hints + localizer + value-gates live; R4v1 in-run rescue stands; repair arms tied 4/6 (variance dominates single runs); in-run rescue inconsistent |
| C — efficient? | **PASS** | Unchanged, still measured (plus Vivado synth wall-times now recorded) |
| D — review scalable? | **FAIL** | Instrument proven live (dry-run); no human measurements yet |
| E — reproducible? | **FAIL** | Vivado synth+timing per gate ✅ new; fixture rows green cross-env; open: sby-in-image, live-benchmark portability |

**Decision: P0 GATE = NO-GO (fifth consecutive, narrowest).** 1/5 passing.

## What would flip each gate (concrete, no hand-waving)

- **A**: C1 mutant swarm at scale (BugGen-style seeder + kill loop — the one
  unbuilt harness piece) + R2/R5-class edit robustness (larger-model
  experiment per v4 authorization, or R5-sequential which is implemented
  but unmeasured live).
- **B**: a second measured in-run rescue on a fresh failing task (the
  mechanism is live; the count is 1).
- **D**: one 6-item human review (~5 min) — command ready since v3.
- **E**: sby-in-image decision (accepted limitation: 745MB suite rejected
  on size + version risk) + live-benchmark Docker↔WSL run.

The Failure-Fixes checklist (report's boxes) is independently green:
synth PASS ×4, formal 8/8 with negative controls, Vivado timing measured.
That program is done; what remains open above is P0-scale and human evidence.

Sign-off: PENDING (named human required per `policy.HUMAN_SIGNOFF_ACTIONS`).
