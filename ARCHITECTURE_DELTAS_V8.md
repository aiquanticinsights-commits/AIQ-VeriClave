# Architecture Deltas vs Frozen Baseline — V8 sync review (2026-09-30)

> Source (FROZEN, unmodified): `Arch-Docs/AIQ-VeriClave_Architecture_Document_Fixed&FinalVersion1.0.md`
> This file records ONLY what differs between that baseline and the build
> at P0 GO (`main` @ v0.8.0): adopted deviations, compatible extensions,
> remaining gaps, and fulfilled open items. Everything else is in sync.

## Verdict

**In sync, with 4 approved deviations, 6 compatible extensions, and
9 remaining gaps (all previously tracked, none new).** No architectural
contradiction found: nothing built violates a MUST in the baseline.

## 1. Deviations (intentional, rationale + approval recorded)

| # | Baseline says | Build does | Why (approved) |
|---|---|---|---|
| D1 | LLM runtime: llama.cpp (`D47`) | LMStudio server (:1234) | Approved 2026-09-28: already installed, GGUF-local, same confidentiality posture; `P0_PROFILE["inference"]` stays one-line swappable |
| D2 | Vivado executes within Linux reference env | Vivado 2026.1 runs on Windows host | Environmental: license/install live on Windows; Linux CI records UNAVAILABLE, never silent |
| D3 | Roadmap P0-A..D / P1..P5 (`§22`) | PHASES 0–7 (`p0.py`) | Naming only: P0-A..D content preserved inside P0 + bake-off; P1..P5 ≡ PHASE 3..7 |
| D4 | Evidence states: 7 listed | 9 states + PROVEN/REFUTED mapping | Additive superset (`SIM_COVERED`, `NOT_APPLICABLE`; PROVEN→PASS, REFUTED→FAIL); `NOT_EXECUTED≠PASS` preserved |

## 2. Compatible extensions (beyond the baseline, no conflict)

| # | Extension | Justification (measured) |
|---|---|---|
| X1 | Elitist closure (incumbent carried free) | T2/T7 backfire class: non-elitist regen destroyed round-1 winners |
| X2 | SVA vacuity rule (`find_vacuity`) | Reviewer-caught vacuous PASS generalized deterministically + regression test |
| X3 | Temperature plumbing + diversity accounting | Prior BoN widths were zero-diversity re-samples; ablation re-measured honestly |
| X4 | Value-gate doctrine (literal value, not text) | `8'd15` ≡ `4'b1111` accepted; over-strict text gates rejected correct fixes |
| X5 | SBY smoke container (37MB toolchain) | E1 acceptance demanded it; full suite explicitly rejected on size/version risk |
| X6 | Crash-safe partials + resume on every long runner | Two timeout kills survived without data loss in production runs |

## 3. Remaining gaps (baseline requires, not yet built)

| # | Baseline requirement | Status |
|---|---|---|
| G1 | D15/D16 rename to Potential Specialized-Model Allocation (`§11`) | Not done (D11/D33/D41 relabels done; D10/D22 keep candidate naming — review at P1) |
| G2 | Vivado evidence: power reports; utilization PERCENTAGES; worst-slack field; spec/testbench/constraint versions (`addendum`) | Partial: raw LUT/FF counts + WNS recorded; the listed fields missing |
| G3 | Adapter reliability / reproducibility / completeness / cross-tool disagreement metrics (`addendum`) | Not computed; raw per-run evidence exists to derive them from |
| G4 | Manual Artifact Inspection Rate; per-accepted-task variants (`D35`) | Dashboard has rate/median/reject/override/opened; these KPIs missing |
| G5 | Coverage tool wired (line/branch, beyond mutation-as-proxy) | Allowlisted + reward-clamped only; no coverage engine runs |
| G6 | C2 ≥95% FPV-proven across generated SVA; C3 Top-3 ≥95% at scale (`§42`) | Measured proxies only (lint-shape, single localizations) |
| G7 | Governed T3 trajectory corpus (`§6` flywheel) | Trajectories collected in reports; no curation/quality-filter process |
| G8 | `vericlave run benchmark.yaml` CLI surface (`X2`) | Module entry points only |
| G9 | ASYNC_REG attributes on synchronizer flops (future CDC rule, `§22`) | Demo syncs lack them; P1 hardening item |

## 4. Fulfilled open items (baseline left open, build closed)

- C1 ≥95% mutant kill: **95.12% measured** (was a target, now evidence).
- FPR <1%: 0.0 measured (20-seed fuzz + lint).
- Cost ≤$0.50/task: $0.00018 nominal + wall-clock recorded.
- Audit 100%: computed on every ledger, every run.
- Supported Vivado versions "only after integration testing": **2026.1 measured**.
- Bake-off then baseline (not Qwen-pinned): executed twice, frozen.
- BoN holds at 3 on measured gain-per-cost (twice, second with real diversity).
- Closure hard boundary (no 4th round): unit-proven + production-observed.
- sby smoke + Docker↔WSL comparison: executed (E1 9/9, E2 7/7).

## 5. Sync judgment

The build implements the baseline's constitution (verification-first,
model-agnostic, CPU-first, open-source-first, evidence-first, bounded
closure, train-only-if-justified) with zero violations found. Deviations
are interface-preserving substitutions with recorded approvals. Extensions
were each forced by measured evidence, never by preference. Gaps are the
already-tracked P1 program, unchanged by this review.
