# Changelog — AIQ-VeriClave

All notable changes, newest first. Versioning: `v0.x.y` pre-1.0; minor = gate
or trackcompletion, patch = fixes. Every entry links evidence, never prose claims.

## [v0.9.0] — 2026-10-14 — P5 freeze ratified + independent re-run green
- P5 freeze assembled and RATIFIED (Satish Sura): protocol, held-out families,
  model/config, bars, env pinned (`P5_FREEZE_v1.json`).
- P5 execution round 1: 4/4 held-out families PASS (10/10 mutants killed, FA 0,
  reproducible, freeze intact); 3 real defects fixed en route (`P5_EXECUTION.json`).
- Independent re-run byte-identical: local clean process AND Linux CI
  (`p5-rerun.yml`, green 2026-10-14) → REPRODUCED (`P5_RERUN.json`).
- CI verdict gate: non-REPRODUCED now fails the job (was silent).
- P4-03..P4-14 complete: frozen benchmark, held-out manifest, intent schema,
  typed generation, diagnostics, closure tripwires, traceability, adapter
  registry, PR template, pilot protocol, repro envelope, P5 draft.

## [v0.8.0] — 2026-09-30 — P0 GO
- Gates A–E PASS (C1 = 95.12%, acceptance 6/6, 2 closure rescues, 20% review @
  18.7 s median, E1 9/9, E2 7/7). Human ACCEPT (`P0_SIGNOFF_V8.md`).

## [v0.7.0] — 2026-09-29 — Fault-localized closure
## [v0.6.0] — 2026-09-29 — Sim/FRM wiring
## [v0.5.0] — 2026-09-29 — Formal adapter
## [v0.4.0] — 2026-09-29 — Constrained generation

(Earlier entries: titles from release history; details in `PROGRAM_LEDGER.md`.)
