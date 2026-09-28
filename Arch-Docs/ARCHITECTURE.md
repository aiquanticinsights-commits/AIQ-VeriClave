# AIQ-VeriClave — Architecture Baseline (implement from this document)

> Status: implementation baseline. Strategy sources: `AIQ_VERICLAVE_MODEL_BLUEPRINT.md`
> (§§1–14), `AIQ-VeriClave_CPU_First_Open_Source_Open_Cloud_Strategy_ChatGTP.md`,
> adopted review diagrams (`DIAGRAMS.md` D01–D67). This document *composes* them
> into one build order — it specifies interfaces and assembly, and points at
> (never repeats) the design docs. In any conflict, machine-checked gates win
> over prose.

## 1. System composition (what gets built)

```text
SPEC + RTL ─► ROUTER ─► GENERATORS (BoN) ─► MACHINE VERIFIERS ─► JUDGE ─► PASS/FAIL
                                                                    │        │
                                                              artifact   closure (≤3)
                                                                    │        │
                                                              LEDGER ◄──────┘
                                                                    │
                                                              HUMAN SIGN-OFF
```

Three layers: **Truth** (deterministic: `policy.DETERMINISTIC_OPS`) /
**Intelligence** (LLM lanes A–F, `policy.LLM_LANES`) / **Learning** (gates in
§5 below — nothing trains before its gate). Evidence-First rule: the LLM
proposes evidence-producing actions; only machine checks manufacture evidence.

## 2. Module map (file → responsibility → design reference)

| Module | Responsibility | Specified in |
|---|---|---|
| `router.py` | top-k routing, adaptive BoN (3/5/8), cascade, cost ceiling | Blueprint §2, §11.4, §12 |
| `rewards.py` | canonical `R = kill+proof+0.5·cov+0.5·loc−0.2·cost`, group-relative advantage | Blueprint §5/§11.2–11.3 |
| `eval_harness.py` + `TokenLedger` | suites, C1–C5 + tokens/USD/CPU report | Blueprint §6, §12 |
| `p0.py` | P0 profile (single gen, BoN=3, deterministic router), PHASES 0–7, ablation runner, dashboard fields | Blueprint §13/P0, strategy PHASE 0 |
| `evidence.py` | hash-chained ledger, C4 audit completeness, named-human sign-off | Blueprint §13.2 |
| `policy.py` | deterministic allowlist (16), LLM lanes, small-model table, merge guards | Blueprint §13.2–13.3 |
| `compute.py` | local-cpu / free-cloud / accelerated-external backends, benchmark configs | Blueprint §14.3 |
| `cache_policy.py` | redacted-prefix caching, per-stage tool schemas | Blueprint §12 |
| `compact.py` | truncate/drop-only compaction, cache-safe | Blueprint §12 |
| `sim_adapters.py` | Verilator/VCS/Questa/Xcelium/Vivado-xsim → `FailureEvent` | Blueprint §10 G2 |
| `vcd_events.py` | VCD → drift sentences ("signal X at cycle N") | Blueprint §10 G3 |
| `formal_policy.py` | pre-run PROVE/BOUND/ABSTRACT/UNPROVABLE verdicts | Blueprint §10 G4 |
| `uvm_gen.py` | deterministic UVM agent skeletons (solving stays in-simulator) | Blueprint §10 G1 |
| `datasets.py` | external corpora registry (license/consumer/caveats) | Blueprint §4.1 |
| `skills/ai-*` (6) | OpenCode session entry points per pipeline stage | `OPENCODE_WORKFLOW.md` |

Interfaces between modules are plain Python calls returning JSON-able dicts
(`run_task()` result shape, ledger `to_json()`, eval `report`); no shared
mutable state except the append-only ledger.

## 3. Data flows (the three loops)

1. **Verify loop** (per task): route → generate (BoN) → machine verifiers →
   Judge filter → majority vote → (min 2 rounds) → winner or escalation.
2. **Closure loop** (per gap): spec-grounded bin → root-cause class → targeted
   regen → re-sim → ledger disposition; stall after 2 flat rounds (§10 G4
   policy caps formal spend; `ai-close` owns the ledger).
3. **Flywheel loop** (per IP run): mutants → localizations → repairs →
   closures → versioned training corpus (T2). Feeds PHASE 3+, never trains
   anything by itself.

## 4. Build order (do not skip steps)

1. **WS0 skeleton**: `make ai-verify` targets + CI nightly (CPU-only) — §A plan.
2. **P0 assembly**: `P0_PROFILE` defaults, `run_ablation(ns=(1,3,5))` on one
   `wb_*` block, dashboard fields populated, C1–C5 baselines recorded.
3. **Gates before scale**: trust ladder (§A2) per stage; BoN width earns its
   keep; learned scorer only at PHASE 5 envelope (86M, k=3, 97.9% hit).
4. **Training only at gates**: PHASE 4 SFT iff frozen baseline fails on
   AIQ metrics; PHASE 6 GRPO iff a measured residual suits RL.
5. **Productize (PHASE 7)**: GGUF/Ollama/vLLM/OpenAI-server/MCP, Apache-2.0,
   eval cards per release, held-out-only rating.

## 5. Configuration reference (single source per knob)

| Knob | Lives in | Default |
|---|---|---|
| Default model / BoN / rounds / train-nothing | `p0.P0_PROFILE` | qwen3-coder-next / 3 / 2–3 / nothing |
| Reward weights | `rewards.WEIGHTS` | 1.0/1.0/0.5/0.5/0.2 (P6 calibrates) |
| Cost ceiling | `router.TASK_BUDGET_USD` | $0.50/task |
| Pricing | `router.PRICE` | editable per-1M table |
| Benchmark split | `p0.P0_BENCHMARKS` | P0-A RideProtect / P0-B MIPI / P0-C held-out |
| Backends | `compute.BACKENDS` + JSON configs | local-cpu |
| Sign-off policy | `policy.HUMAN_SIGNOFF_ACTIONS` | 6 guarded actions |

Any knob referenced anywhere else (docs, skills, scripts) must import from
these definitions — the duplication ban from the adoption program applies to
configuration most of all.

## 6. Acceptance mapping (how "done" is proven)

| Claim | Proven by | Threshold |
|---|---|---|
| C1 mutant kill ≥95% | `eval_harness` + BugGen-seeded suites, ≤3 iters | §6 band |
| C2 SVA ≥95% FPV-proven | Judge filter + SymbiYosys proofs | §6 band |
| C3 Top-3 ≥95% | localization eval on seeded bugs | §6 band |
| C4 100% ledgered | `ledger.audit_completeness() == 1.0` | exact |
| C5 FPR <1% | golden-vs-golden runs | §6 band |
| Cost ≤$0.50/task | `tokens.cost_usd` + CPU ledger per eval | §6/§12 |
| No silent gaps | stall dispositions + UNPROVABLE verdicts all ledgered | exact |

Test command (entire executable contract): `python -m unittest discover -s . -p "test_*.py"` — currently green; any red test blocks release
regardless of prose claims elsewhere.
