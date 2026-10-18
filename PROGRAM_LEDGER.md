# AIQ-VeriClave — Program Task Ledger (completed vs pending)

> Compiled from signed repo evidence (gate reviews, sign-offs, verdict JSONs).
> Dates are evidence dates. Anything without a cited artifact is marked as such.
> Status as of 2026-10-18: P0–P3 CLOSED, P4 exit signed, P5 qualified+reproduced,
> P6 productization in progress, P7 assisted-done/human-pending. Sections A–C below
> are historical rows (append-only); live pending state is section D at the end.

## A. Completed

### A1. Foundation: model, method, and doctrine
| # | Activity | Evidence |
|---|---|---|
| F-01 | Literature grounding: CodeV-R1, PRO-V-R1, BugGen, BluesFL, GoGoTB, CorrectBench, AssertLLM/2, Qwen3-Coder family, ensemble methods (MAV, RouteMoA, TUMIX) | Blueprint §§1–14, now consolidated into `AIQ-VeriClave_Architecture_Document_Fixed&FinalVersion1.0.md` (former blueprint file superseded) |
| F-02 | Justification record: why no CodeV-R/Qwen-Coder/VeriGen in the silicon path (verification bottleneck, audit, compute ROI, IP hygiene) | Prior review record; falsifiers now in `AIQ-VeriClave_Architecture_Document_Fixed&FinalVersion1.0.md` (former blueprint §B6) |
| F-03 | Naming + brand: AIQ-VeriClave (Hub collision-checked), rename applied repo-wide, 30/30 tests green at rename | Commit history; test suite |
| F-04 | Distribution plan: Hub/GitHub/Ollama/ModelScope tiers, Apache-2.0, phased (code+data now, weights at gates) | Prior review record |

### A2. Reference scaffold (CPU-only, tested)
| # | Activity | Evidence |
|---|---|---|
| S-01 | Ensemble router (top-k, adaptive BoN 3/5/8, cascade, $0.50 ceiling) + eval harness with token/USD/CPU ledger | `router.py`, `eval_harness.py`, `test_router.py` (36 tests OK) |
| S-02 | Canonical RL reward + group-relative advantage, no critic | `rewards.py`, `test_rewards.py` |
| S-03 | Hash-chained evidence ledger, C4 audit, named-human sign-off only | `evidence.py`, `test_platform.py` |
| S-04 | Constitutional policy (16 deterministic ops, LLM lanes A–F, small-model table, merge guards) | `policy.py` |
| S-05 | P0 profile (BoN=3, deterministic router), PHASES 0–7, ablation runner, dashboard fields | `p0.py` |
| S-06 | Vendor log adapters (Verilator/VCS/Questa/Xcelium/Vivado), VCD drift pinpointer, bounded-formal policy, UVM skeleton generator | `sim_adapters.py`, `vcd_events.py`, `formal_policy.py`, `uvm_gen.py`, `test_adoption.py` |
| S-07 | External corpora registry (CircuitNet 2.0, DeepCircuitX, HLSDataset, Koios 2.0, OpenTitan bugs + flywheel core) with license/caveat enforcement | `datasets.py`, `test_datasets.py` |
| S-08 | Token-efficiency program (ledger, redacted-prefix caching, CliffCompaction rules, §12) | `cache_policy.py`, `compact.py`, `test_efficiency.py`, blueprint §12 |
| S-09 | Compute adapter (local-cpu/free-cloud/accelerated) + CPU-aware eval report | `compute.py`, `test_compute.py` |
| S-10 | OpenCode workflow + 6 project skills (`ai-verify-harness`, `ai-mutate`, `ai-localize`, `ai-close`, `ai-ensemble`, `ai-evidence`) | `OPENCODE_WORKFLOW.md`, `skills/` |
| S-11 | 67 diagrams adopted verbatim (D01–D67 + X1/X2 appendices), integrity-checked | `DIAGRAMS.md` |
| S-12 | Architecture baseline doc (module map, loops, build order, config reference, acceptance mapping) | Consolidated into `AIQ-VeriClave_Architecture_Document_Fixed&FinalVersion1.0.md` + `ARCHITECTURE_DELTAS_V8.md` (former standalone baseline file superseded) |

### A3. P0 — signed GO (V8, 2026-09-30 → sign-off 2026-10-01)
| # | Activity | Evidence |
|---|---|---|
| P0-1 | Gates A–E all PASS (C1 = 95.12%, acceptance 6/6, 2 in-run closure rescues, 20% review rate @ 18.7 s median, E1 9/9, E2 7/7) | `P0GATE_REVIEW_V8.md`, `P0_SIGNOFF_V8.md` (human ACCEPT) |
| P0-2 | SBY smoke container (9/9, 260 MB pinned image, counter proof in-container) | `SBY_SMOKE.json` |
| P0-3 | Docker↔WSL portability benchmark (7/7 incl. mutant-agreement + negative outcomes) | `E2_PORTABILITY_REPORT.json` |
| P0-4 | Five prior NO-GOs (V1–V7) each certifying a smaller unknown | `P0GATE_REVIEW.md` … `P0GATE_REVIEW_V7.md` |
| P0-5 | Gates A/B/D/E demo set (ok+buggy pairs, SymbiYosys v0.68) | `GATES_ABDE.json`, `FORMAL_WB_DMA.json` |

### A4. P1 — complete
| # | Activity | Evidence |
|---|---|---|
| P1-1 | A_IRQ formal disposition | `P1_01_A_IRQ_DISPOSITION.json`, review: APPROVED |
| P1-2 | T4/R2/R5 capability findings | `P1_02_*`, review: APPROVED |
| P1-3 | C-band scale validation | `P1_03_*`, review: APPROVED |
| P1-4 | Portability/reproducibility (Docker/WSL, env lock-in plan) | `P1_04_*`, `PORTABILITY*.json`, `ENVIRONMENT_LOCKIN_PLAN.md`, review: APPROVED |
| P1-5 | P1 completion review: all four APPROVED, P0 GO confirmed, P1 CLOSED | `P1_COMPLETION_REVIEW.md` |

### A5. P2 — closed, training NOT authorized (2026-10-01)
| # | Activity | Evidence |
|---|---|---|
| P2-1 | Frozen benchmark (M1), alternative models evaluated (M2: llama-3.1-8b, deepseek-coder-6.7b) | `P2_BENCH.json`, `P2_M2_LLAMA.json`, `P2_M2_DEEPSEEK.json` |
| P2-2 | M3 verdict recorded honestly: T4 70%/55% vs 90% bar, R2 0–3/20 vs ≥4 — WALLS STAND, FAIL | `P2_M3_VERDICT.json`, `P2_COMPLETION_REVIEW.md` |
| P2-3 | M4 (no P0 regression) PASS, M5 (dataset baseline) PASS, M6 training decision **NO-GO** | Same review |
| P2-4 | Frozen P0/P1 evidence left unchanged | Same review |

### A6. Open-source readiness (this week — committed + pushed)
| # | Activity | Evidence |
|---|---|---|
| O-01 | Apache-2.0 LICENSE; README (vision/setup/roadmap); CONTRIBUTING; Code of Conduct; issue templates (bug/feat/verify); labels plan | Commit `25602b7` (+681 lines), pushed `5cdc892..25602b7` |
| O-02 | Repo made PUBLIC; branch protection on `main` (1 approval, no force-push/deletion) | `gh repo view` → PUBLIC; protection API verified |
| O-03 | 22 labels live; 5 mentored `good first issue`s filed (#1–#5) | Issues #1–#5 on GitHub |
| O-04 | LinkedIn narrative series (8 posts: architecture→plan→P0/P1→P2 NO-GO→P3→asks) | `LINKEDIN_SERIES.md` (untracked — see pending T-06) |

## B. Pending

### B1. P3 four-track program (scope frozen 2026-10-01/02 — execution/decision)
| # | Task | State / next action |
|---|---|---|
| P3-A | 14B local model track (Qwen2.5-Coder-14B Q4_K_M) | Partial: R2 arm 17 closes, FA=0 re-derived (`P3_A_VERDICT.json`); **pending: final verdict sign-off + T4 re-measure closure** (`P3_A_T4_REMEASURE*.json`) |
| P3-B | llama+DeepSeek ensemble track | **Verdict recorded: FAIL** (union ceiling 3/20 < bar 4 — capability, not selection problem). Pending: close out + carry R2 wall forward |
| P3-C | Structured/verifier-guided pipeline track | Partial: 8/20 closes, 0 FA, beats baseline (`P3_C_PIPELINE_VERDICT.json`); **pending: final verdict + Qwen amendment disposition** (`P3_C_QWEN_*.json`) |
| P3-D | Training-readiness data track | Corpus measured: 278 generations, overwhelmingly negative (good for failure analysis, unfit as SFT positives), **no held-out split** (`P3_D_READINESS.json`); **pending: held-out design + diversity expansion before any SFT claim** |
| P3-G | P3 decision gate (model works / system works / data ready) | Pending P3-A/C verdicts |

### B2. Capability walls (carried forward, not closed)
| # | Task | State |
|---|---|---|
| W-1 | T4 wall (≥90%) | Stands (70%/55% measured) |
| W-2 | R2 wall (≥4 closes) | Stands (best single-run: 8/20 pipeline w/ 0 FA — below bar) |
| W-3 | R5 scale/diversity/economics constraints | Partially cleared (d5+d8); R-4 scale work ongoing per log |

### B3. Productization backlog (PHASE 5–7, gated — not started)
- Learned 86M router scorer (heuristic stands until 97.9%-class hit rate)
- GRPO experiment (conditional on a measured RL-suitable residual — none established)
- GGUF/Ollama/vLLM/MCP packaging, eval cards, Hub/ModelScope rollout
- SFT/LoRA (blocked: no SFT-suitable positives + no held-out split — see P3-D)

### B4. Repository hygiene (small, do anytime)
| # | Task |
|---|---|
| T-01 | Decide fate of `LINKEDIN_SERIES.md` (commit vs keep local) — only untracked file left |
| T-02 | Full unit-suite hang: `unittest discover` stalls >300 s (likely a portability/docker-dependent module); isolate + mark slow tests skippable (fast subset: 36–52 tests OK) |
| T-03 | Re-run portability matrix after any toolchain bump (version-pinned per `requirements.txt` + SBY smoke image) |
| T-04 | File follow-up issues from P3 verdicts (R2 wall, held-out split) so walls are tracked as issues, not just JSON |
| T-05 | P0 dashboard redeploy per release (review_dashboard.py) + monthly dependency/license re-audit |

---
*Ledger rule: append-only. Completed rows are never edited — corrections land as new rows with dates. Next ledger review: at P3 decision gate.*

## C. P4 program record (appended 2026-10-13; P4–P7 plan v1.0 adopted as-is)

| # | Activity | Evidence |
|---|---|---|
| P4-DOC | Benchmarked P4–P7 plan against repo: P3-CLOSED, P0-GO, P2-NO-GO, Vivado artifacts, R-4/d1 constraints all consistent; no contradictions found | This row (benchmark step) |
| P4-01 | `CAPABILITY_RESULT_RECONCILIATION.md` created (P0/P1/P2/P3 rows, E0–E4 labels, carried constraints, supersession note) | File, this cycle |
| P4-02 | `ARCHITECTURE_STATUS.md` created (CURRENT/EXPERIMENTAL/FUTURE/EDUCATIONAL/SUPERSEDED classification, frozen interfaces, deferred list) | File, this cycle |
| P4-03 | `DEVELOPMENT_ROADMAP_P4_P7.md` created (P4-01..P4-14 tracked; P4-01/02 self-marked DONE) | File, this cycle |
| P4-04 | Doc benchmark verdict: plan ADOPTED with no content changes required | This row |

Next: P4-03 (freeze P4 benchmark protocol) → P4-04 (held-out families) per roadmap order.

| P4-05 | P4-03 executed: `P4_BENCH_v1.json` frozen (tracks P4-05..P4-09, 11-diagnostic schema, R0–R3 boundary, regression guard, CPU-only env) + `test_p4_bench.py` 7 tests green; roadmap row marked DONE | Files + suite, this cycle |
| P4-06 | P4-04 executed: `P4_HELDOUT_v1.json` frozen (3 dev families grounded in P0–P3 assets + 4 new held-out: async-fifo, round-robin-arbiter, interrupt-controller, reset-synchronizer; contamination rules; same C1–C5 bars + FA=0 blind grading) + `test_p4_heldout.py` 6 tests green; roadmap row marked DONE | Files + suite, this cycle |
| P4-07 | P4-05 executed: `intent.py` structured verification-intent schema (typed signals with widths/clocks, reset polarity/kind, temporal ops, artifact gate; fail-closed validation; JSON round-trip) + `test_intent.py` 10 tests green; roadmap row marked DONE | Files + suite, this cycle |
| P4-08 | P4-06 executed: `generate.py` typed generation interface (SVA width properties + functional placeholder, covergroups, executable Python checker stub, directed-test outline — validated intents only, invalid refused with reasons) + `test_generate.py` 10 tests green (incl. live checker exec); roadmap row marked DONE | Files + suite, this cycle |
| P4-10 | P4 exit review executed: `demo_p4_exit.py` end-to-end chain on async-fifo (intent→4 artifacts→checker-vs-FRM incl. seeded stuck-0 mutant killed→diagnostics→R0–R2 PASS→trace 1.0→ledger chain-ok→formal PROVE-recommendation with UNAVAILABLE execution honestly recorded→repro envelope) + `test_demo_exit.py` 7 tests + `P4_EXIT_REVIEW.md` (per-item verdicts, overall GO WITH CONDITIONS, human sign-off PENDING); fail-closed validation live-caught a clock-name mismatch during the review itself | Files + suite, this cycle |
| P4-11 | P5 freeze assembled (NOT ratified): `P5_FREEZE_v1.json` pins protocol + held-out families + model/config + bars + env at commit `3110428`; `test_p5_freeze.py` 6 consistency tests green (refs resolve, families match manifest, sign-off still PENDING); awaits named-human signature to ratify | Files + suite, this cycle |
| P4-12 | Signatures recorded 2026-10-13: P4 exit SIGNED by Satish Sura (`P4_EXIT_REVIEW.md`); P5 freeze RATIFIED (`P5_FREEZE_v1.json` status ratified, identity+date recorded); both sign-off tripwire tests flipped together per design (a signature without its test flip fails the suite); 175-test broad run green | Files + suite, this cycle |
| P4-13 | P5 execution round 1 (`p5_execute.py`): all 4 held-out families PASS — 10/10 seeded mutants killed, 0 golden false alarms, closure PASS, trace 1.0, ledger sound; deterministic re-run agreement; freeze intact. Debugging en route fixed 3 real defects (1-cycle FRM latency bug, missing pop-sequence oracle, weak threshold stimulus) — recorded, not hidden. Evidence: `P5_EXECUTION.json` |
| P4-14 | Independent re-run (`p5_rerun.py`, clean subprocess, no shared state): canonical JSON byte-identical to committed `P5_EXECUTION.json` across all 4 families → verdict REPRODUCED; `P5_RERUN.json` recorded; `test_p5_rerun.py` 5 tests (incl. tamper-detection). Same-machine methodological independence; second human/machine executor still the full-E3 bar |
| P4-15 | Portability hardening for CI: repo-relative paths in p5 chain + 5 test modules (no hardcoded Windows paths); `.github/workflows/p5-rerun.yml` runs the independent re-run + focused tests on ubuntu-latest, uploads `P5_RERUN.json` as artifact; verdict gate added (non-REPRODUCED fails the job) |
| P4-15 | Portability hardening for CI: repo-relative paths in p5 chain + 5 test modules (no hardcoded Windows paths); `.github/workflows/p5-rerun.yml` runs the independent re-run + focused tests on ubuntu-latest, uploads `P5_RERUN.json` | Files + CI config, this cycle |
| P4-16 | P6 packaging track opened: `INSTALL.md` (source/Docker/WSL2/offline/air-gap/troubleshooting), Dockerfile acceptance comment corrected to consolidated arch docs | Files, this cycle; Docker build itself needs a daemon (not run here) |
| P4-17 | Contributor issues #6 (R2 wall attack), #7 (held-out family #5, good-first-issue), #8 (T4 ablation) filed with frozen-scope constraints | GitHub issues, this cycle |
| P4-18 | CI second-machine evidence: `p5-rerun.yml` green on ubuntu-latest (2026-10-14, all steps incl. verdict gate); `CHANGELOG.md` created (v0.9.0 entry); release v0.9.0 cut (P5 freeze ratified + independent re-run green) | GitHub Actions + release, this cycle | Files + suite, this cycle |
| P4-09 | P4-07..P4-14 executed in one autonomous run: `diagnostics.py` (frozen 11-code schema + remedies + FailureEvent bridge, 8 tests) · `closure.py` (R0–R3 + escalation + 9 tripwire tests) · `trace.py` (7-state chains + completeness, 6 tests) · `adapter_registry.py` (evidence-backed L1–L5, 7 tests) · `.github/pull_request_template.md` (evidence checklist; CI upload pre-existing) · `PILOT_PROTOCOL.md` (preregistered human-vs-assisted design) · `repro.py` (env/tool/git/hash envelope, 6 tests) · `P5_QUALIFICATION_PROTOCOL.md` (frozen-before-execution draft); roadmap rows marked DONE | Files + suite, this cycle |
| P4-19 | P7 pilot assisted arm executed (`pilot_assist.py` on 2 held-out tasks): both PASS — 5/5 mutants, FA 0, 1 iteration each, trace/ledger clean, full measure set (`P7_PILOT_ASSISTED.json`); `HUMAN_ARM_RUNBOOK.md` published (timesheet format, blinded comparison, hard rules); `test_pilot.py` 6 tests incl. no-simulated-humans assertion. E4 NOT claimed — human arm pending | Files + suite, this cycle |
| P4-20 | Interactive human-arm runner (`pilot_human.py`: phased timers, attestation gate, sandboxed checker exec via RESULT contract, sealed output) + `test_pilot_human.py` 16 tests incl. fixed neutral question bank, forward-only phases, neutrality scan that caught 3 real prompt leaks pre-commit, and no-oracle-import enforcement; protocol amendment A1 + walkthrough runner-contract note | Files + suite, this cycle |
| P4-21 | Human-arm live session ABORTED at attestation gate: Q1 yes / Q2 NO (AI assistance used) / Q3 yes. Per protocol amendment A1, no tasks started, no times recorded, no data collected toward E4. Abort recorded here rather than laundered; clean restart requires a session with no AI authoring help. | Aborted session record, this cycle |

| 2026-10-17 14:34 | Sign-off | CI/Automated | CI Bot | AGREED | Auto-approved: all gates passed |
| P4-21 | Human-arm live session ABORTED at attestation gate: Q1 yes / Q2 NO (AI assistance used) / Q3 yes. Per protocol amendment A1, no tasks started, no times recorded, no data collected toward E4. Abort recorded here rather than laundered; clean restart requires a session with no AI authoring help. | Aborted session record, this cycle |
| P6-01 | P6 packaging hardening: `pyproject.toml` fixed (wrong `[project.entry-points]` → correct `[project.scripts]`, duplicate `vericlave-p0` removed, duplicate `[tool.pytest.ini_options]` merged, inline-table `per-file-ignores` → `[tool.ruff.per-file-ignores]` section); `setup.py` fixed (duplicate `extras_require`/`include_package_data`/entry removed); `release.yml` fixed (duplicate `release`/`test-pypi` job defs removed, deduplicated `permissions`/`tags`/`push` keys, clean 5-job pipeline: build-and-test → test-pypi → docker-build → release → publish-pypi). `python -m build` produces valid sdist+wheel; `twine check` PASSED both; 129 tests + 4 subtests green | Files + build output + twine, this cycle |
| P6-02 | `signoff.yml` fixed (duplicate `phase` input, duplicate top-level `permissions`, duplicate job `runs-on`/`permissions` removed — workflow was failing at 0s on every push, now valid); `release.yml` publish steps guarded with secret-presence `if` so they skip cleanly when secrets absent (no more failing release CI); README quickstart/layout/roadmap refreshed; `CHANGELOG.md` v0.9.1 entry added; CI green (`39042026892`) | Files + CI, this cycle |
| P6-03 | v0.9.1 tagged and released (P6 packaging + P7 pilot infrastructure). PyPI/Docker publish steps skip by design (no `TEST_PYPI_API_TOKEN`/`PYPI_API_TOKEN`/`DOCKER_*` secrets set); GitHub release created from tag with generated notes | Tag + GitHub release |
| P6-04 | Correction to P6-03: first v0.9.1 cut shipped artifacts named 0.9.0 (package version not bumped) and `release.yml` initially failed workflow validation twice — root causes fixed and recorded, not hidden: (a) duplicate `verbose` key in `with:` (GitHub rejects duplicate YAML keys that `yaml.safe_load` silently accepts), (b) `secrets` context is **not a valid named-value in `if`** → replaced with job-level `env:` holding the secret and step `if: env.X != ''`; `action-gh-release@v1`→`@v2`. Version bumped to 0.9.1 (pyproject + setup.py), rebuilt (twine PASS), release deleted and re-cut at `5d3ac86`; final artifacts `aiq_vericlave-0.9.1-{py3-none-any.whl,tar.gz}`. All workflows pass `actionlint`; Release + vericlave-p0 CI green | Tag + GitHub release + CI, this cycle |

## D. P6 productization completion + tracker reconciliation (appended 2026-10-18)

> Section D is the live pending/completion record. Rows are append-only.

| # | Activity | Evidence |
|---|---|---|
| P6-05 | Tracker reconciliation (stale→reality): `DEVELOPMENT_ROADMAP_P4_P7.md` gate section rewritten with per-criterion P6 status + real P7 state; `CAPABILITY_RESULT_RECONCILIATION.md` P3-A/P3-C corrected from "verdict pending" to the actually-signed verdicts (A PARTIAL, C PASS) + P3 closure note referencing `P3_FINAL_DECISION_GATE.json` (human-approved 2026-10-11); ledger header updated; README status + roadmap checkboxes fixed and two dead links repointed (`Arch-Docs/ARCHITECTURE.md`, `Arch-Docs/AIQ_VERICLAVE_MODEL_BLUEPRINT.md`); `PUBLIC_PRIVATE_SPLIT.md` doc path fixed; `LINKEDIN_SERIES.md` v0.9.0→v0.9.1 | Files, this cycle |
| P6-06 | P6 production deliverables authored: `SECURITY_MODEL.md` (threat model + enforced controls C1–C9 + residual risks R1–R5, grounded in code: no `shell=True`, loopback-only model boundary, fail-closed redaction, hash-chained ledger), `LOGGING.md` (three observability planes: hash-chained ledger / JSON run reports / FailureEvent stream; explicitly not a logging framework), `RECOVERY.md` (crash-safe partials + `--resume`, deterministic re-run, ledger-integrity recovery, RC1–RC4 residual risks incl. non-atomic partial writes), `PRODUCTION_READINESS.md` (consolidated gate status) | Files, this cycle |
| P6-07 | T-02 CLOSED: `sim_frm.tool_ok()` and `portability.collect()` gated live-toolchain tests on `shutil.which("wsl")` presence, then ran `wsl verilator` with up to 600 s timeouts → `unittest discover` hung >300 s. Replaced with bounded 15 s reachability probes (`_reachable`); non-functional WSL fails fast and tests skip. Verified: `python -m unittest discover -s . -p "test_*.py"` → **565 tests, OK, 79 s** (was hanging); `test_sim_frm` 25 ok, `test_portability` 8 ok | Run output, this cycle |
| P6-08 | Docker deploy genuinely verified (was vacuous): fixed fatal Dockerfile bug (runtime stage copied `/app` from `builder`, which never had it), made `sby` best-effort/non-blocking, image label v0.9.1, non-root user, contract-suite `CMD`; added `.dockerignore` entries. `docker build` succeeds; `docker run --rm aiq-vericlave:test` → **65 tests OK in-image**; toolchain confirmed (Python 3.12.3, Verilator 5.020, Yosys 0.33, sby absent→non-blocking). Also fixed `.github/workflows/release.yml` `docker-build` job which had **no build step** — added always-on image build + in-image smoke-run (push still gated on Docker Hub secrets); `actionlint` clean | Build + run output, this cycle |
| P6-09 | T-05 dependency audit: `pip-audit -r requirements.txt` and `pip-audit .` → **No known vulnerabilities found** (exit 0); dependency licenses all permissive (pyyaml MIT, pydantic MIT, cocotb BSD-3, pytest MIT) → Apache-2.0 compatible. T-01 resolved: `LINKEDIN_SERIES.md` is already tracked (no action). T-03 conditional (no toolchain bump). T-04 already filed (#6–#8). | Audit output, this cycle |
| P6-10 | **P6 gate status:** ALL entry criteria DONE except registry publish, which is **BLOCKED on owner secrets** (`TEST_PYPI_API_TOKEN`, `PYPI_API_TOKEN`, `DOCKER_USERNAME`, `DOCKER_PASSWORD`) — steps self-skip cleanly meanwhile. **P7 status:** assisted arm DONE; human arm **BLOCKED on a named human** (clean no-AI-help session required; prior session aborted at attestation per `P4-21`). E4 not claimed. Capability walls T4/R2 stand as tracked findings | `PRODUCTION_READINESS.md`, this cycle |
| P6-11 | **Human-arm runner made runnable (defect fix).** The declared console entry `vericlave-pilot-human = "pilot_human:main"` (`pyproject.toml:100`, `setup.py:69`) and the documented command `python pilot_human.py` (`PRODUCTION_READINESS.md`) both referenced a `main()` that **did not exist** — `pilot_human.py` was a component library only, so the command was a silent no-op (`hasattr(pilot_human,'main')` → False, run exit 0). Added the missing session driver `main()` orchestrating the fixed `PHASES`: setup → `attest_gate()` → per task (author → sandboxed `run_checker_module` measure → review) → satisfaction → `seal_record`; abort path (any non-yes attestation) seals an abort record with no task data (protocol A1) and exits 1. All prompts sourced from `QUESTION_BANK`; no answer-bearing imports (neutrality test still passes). Added 2 regression tests (`TestMainRunner`). Verified: `python -m unittest discover` → **567 tests OK (53 s)**; live scripted end-to-end run of `python pilot_human.py` sealed a schema-valid record (`engineer`, 2 tasks, `phases_seconds`, sha256) | Files + run output, this cycle |
| P6-12 | **Assisted-arm runner made runnable (same defect class).** Declared console entry `vericlave-pilot = "pilot_assist:main"` (`pyproject.toml:99`, `setup.py:68`) also referenced a non-existent `main()` (`hasattr(pilot_assist,'main')` → False). Added `main(outdir=None) -> int` (runs `run_pilot()`, writes `P7_PILOT_ASSISTED.json`, prints per-task verdicts, returns 0) + `import os`; `__main__` now calls it. Added `test_pilot_assist.py` (entry-point exists; report is `arm=assisted`, both tasks PASS, human_arm PENDING). Verified: `python pilot_assist.py` → both tasks **PASS** (5/5 mutants, FA 0); `test_pilot_assist` 2 tests OK. Console script `vericlave-pilot` now resolves | Files + run output, this cycle |
| P6-13 | **Human-arm runner hardened so a test run cannot masquerade as evidence.** Review of a real sealed artifact (`P7_PILOT_HUMAN_ssb-2026-10-18T10-22.json`) showed the runner sealed an apparently-valid record whose measurement fields were all `null` — both task "checkers" were invalid (`pilot_assist.py`, and the bare string `interrupt-controller`), so no verification occurred, yet it exited 0 and looked submittable. Fix: `main()` now tracks any task with no valid measurement (`incomplete`), sets `"complete": false` + `"incomplete_reasons"`, seals under a distinct non-submittable name `P7_PILOT_INCOMPLETE_*`, prints a loud "NOT valid pilot evidence" warning, and returns exit code **3**. Attestation-abort records likewise renamed `P7_PILOT_ABORTED_*` (`complete:false`); only complete sessions use `P7_PILOT_HUMAN_*`. `seal_record()` gained an optional `prefix`; the retry prompt was moved into `QUESTION_BANK` (`retry_measure`) per the all-prompts-from-bank rule. Added `test_incomplete_session_not_submittable`, tightened clean/abort tests. Verified: `unittest discover` → **570 tests OK (53 s)**. The invalid `ssb` artifact was deleted (never committed) | Files + run output, this cycle |
