# P0 Gate Re-Review v4 — fix campaign on every open failure (2026-09-29)

> v1–v3 stand frozen. This review dispositions each failure from the v3
> open list after targeted fixes + re-measurement. Rule unchanged: misses
> diagnose layers, never authorize unjustified spend.

## Failure-by-failure disposition

| # | Failure | Fix attempted | Measured outcome | Status |
|---|---|---|---|---|
| F1 | T4 wrong MC answer | Scenario completed twice (waveform, single-clock fact) | D→A→A across versions; C never selected. Genuine 8B judgment gap | OPEN, capability wall candidate |
| F2 | R2 wrong truncation (0x80/0x81) | Line skeleton + low-bits rule + value-gate | Arithmetic slip persists twice; gate doctrine vindicated (rejects correctly) | OPEN, capability wall candidate |
| F3 | R5 3-part fix | declline skeleton + interface rule + value-gate | Live runs still fail; probe reached a correct fix once (8'd15) but unreplicated | OPEN; prescribed: sequential decl→assign (SIM-slot pattern) |
| F4 | SIM slot discipline | Sequential slots + different-transfer few-shot + slot closure | ✅ CLOSED — verdict True/equiv True/completed True (`SIM_FRM_LLM.json`) | FIXED |
| F5 | A_IRQ formal | — (toolchain boundary, proven) | ✅ DISPOSITIONED — covered by sim V3 lifecycle vector; mapping: formal NOT_EXECUTED → sim EXECUTED/PASS | FIXED as disposition |
| F6 | C-bands at scale | P0-B v2 (n=10/kind) | Priors frozen; loop-at-scale (swarm) still open | PARTIAL |
| F7 | D live review | Instrument + dry-run validated | No human run yet | OPEN, needs user |
| F8 | E image rows | Fixture mode (in-repo demo design) | ✅ lint+synth now PASS in image; sby row accepted limitation (745MB suite rejected: size + version-mismatch risk, recorded) | FIXED except sby |
| F9 | Mutant rates low | In-loop skeleton evidence | T6/R4-loop close; R2/R5 open (see F2/F3) | PARTIAL |

## Verdicts

| Gate | Verdict | Ground |
|---|---|---|
| A — system works? | **FAIL** | sim ✅✅✅, formal 2+1 proven, FPR 0.0, trace/audit ✅; open: A_IRQ-formal, R2/R5-class edits, C1 swarm |
| B — closure works? | **FAIL** | Hints + localizer live; strategy rescues (T9, skeletons, R4v1, R5-probe); in-run rescue inconsistent. Next: sequential multi-step (R5), fault-localized regen at scale |
| C — efficient? | **PASS** | Unchanged, still measured |
| D — review scalable? | **FAIL** | Awaits one human run |
| E — reproducible? | **FAIL** | Fixture rows green cross-env; sby-image + live-benchmark portability open |

**Decision: P0 GATE = NO-GO (fourth consecutive, narrowest).** 1/5 passing.

## New authorized note (evidence-backed, first time)

F1/F2/F3 share a signature previous failures lacked: the harness is proven
correct around them (probes show valid gates rejecting genuinely wrong
values; prompts carry the needed constraints), yet the 8B baseline repeats
the same slips. This is the first result set where *candidate quality
itself* is the diagnosed layer — the exact failure class the frozen
roadmap says larger models fix (vs. context/engine/data failures, which
they don't). A loadable-larger-model experiment is therefore authorized
*as an experiment with abort criteria* (must move F1/F2/F3 within one
bake-off round, else dropped) — not as open-ended spend. If no larger
model loads on this machine, the fallback sequence is: R5-sequential,
T4 reason-then-letter grading, C1 mutant swarm.

Sign-off: PENDING (named human required per `policy.HUMAN_SIGNOFF_ACTIONS`).
