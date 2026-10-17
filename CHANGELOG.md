# Changelog — AIQ-VeriClave

All notable changes, newest first. Versioning: `v0.x.y` pre-1.0; minor = gate
or trackcompletion, patch = fixes. Every entry links evidence, never prose claims.

## [v0.9.1] — 2026-10-17 — P6 packaging + P7 pilot infrastructure
- P6 packaging: valid `pyproject.toml` (PEP 621 `[project.scripts]`, ruff
  per-file-ignores section), `setup.py`, `MANIFEST.in`, multi-stage production
  `Dockerfile`, `release.yml` (5-job pipeline: build→test-pypi→docker→release→publish).
  `python -m build` + `twine check` both PASS.
- P7 pilot assisted arm: 2 held-out tasks PASS (5/5 mutants, FA 0) (`P7_PILOT_ASSISTED.json`).
- Interactive human-arm runner (`pilot_human.py`): phased timers, attestation gate,
  sandboxed exec, sealed output; 16 tests incl. neutrality enforcement (caught 3
  real prompt leaks pre-commit); protocol amendment A1.
- Human-arm session honestly ABORTED at attestation (Q2 failed: AI assistance used);
  no E4 data collected; restart requires clean session.
- Simple sign-off system (`simple_signoff.py`): 7 automated gates, plain-English
  Agree/Disagree CLI, ledger auto-record; CI workflow `signoff.yml` (workflow_dispatch).
- Contributor issues #6 (R2 wall), #7 (held-out family #5), #8 (T4 ablation).
- Portability hardening: repo-relative paths in p5 chain + 5 test modules;
  `p5-rerun.yml` green on ubuntu-latest (second-machine E3 evidence).

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
