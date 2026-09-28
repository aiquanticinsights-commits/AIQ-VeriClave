# P0 Gate Review — Gates A–E verdict from measured data (2026-09-28)

> Rule (frozen §9): a gate miss triggers diagnosis of the relevant layer —
> never automatic escalation to a larger model, GPU spend, or training.
> This review measures; it does not overclaim. C1–C5 bands are NOT asserted.

## Inputs (all committed evidence, no prose claims)

| Input | Content |
|---|---|
| `P0D_REPORT.json` (+ `P0D_PARTIAL.json` histories, local) | 9 tasks, BoN=3, temp 0.7, baseline llama-3.1-8b |
| `P0B_BASELINE.json` | bake-off: llama-3.1-8b 0.50/46.3s/1006tok over deepseek 0.33/77.5s/1490 |
| Verilator lint `rideprotect-rv/rtl/wb_dma.v` | PASS, benign warnings only (WIDTHEXPAND note, UNUSEDSIGNAL) |
| Yosys `synth -top wb_dma` (measured this review) | PASS, 1070 cells, 0.2s |
| sby `wb_dma.sby` | NOT_EXECUTED — no properties bound in RTL; a property-less run would manufacture false confidence, so it was refused |
| Sim/FRM in-loop | NOT_EXECUTED (no TB/FRM wired in P0-D v1) |

## Per-task ground truth (from partial histories)

| Task | Kind | Approvals r1→r3 | Outcome | Note |
|---|---|---|---|---|
| T1-sva-ack | sva | 0,0,0 | ESCALATED | generator never lint-clean |
| T2-sva-irq | sva | 2,0,0 | ESCALATED | round-1 winner DESTROYED by forced round 2 (min-rounds backfire) |
| T3-localize-bus | loc | 2,1,1 | CLOSED r3 | plurality drift, not regen improvement |
| T4-classify-reset | loc | 1,1,1 | CLOSED r3 | weak close (plurality) |
| T5-req-ids | cov | 2,2 | CLOSED r2 | only first-pass close (1/9) |
| T6-width-fix | mut | 0,0,0 | ESCALATED | never lint-clean |
| T7-sva-cyc | sva | 2,0,0 | ESCALATED | same backfire as T2 |
| T8-localize-irq | loc | 2,1,1 | CLOSED r3 | plurality drift |
| T9-status-fix | mut | 0,0,0 | ESCALATED | never lint-clean |

Closure regen rescued **zero** failing tasks. Every close came from round-1
output surviving plurality vote — never from iteration improving anything.

## Verdicts

| Gate | Question | Verdict | Evidence |
|---|---|---|---|
| A — system works? | syntax/sim/FRM/formal/mutation/trace/evidence | **FAIL** | evidence 1.0 ✅, trace ✅, lint/yosys ✅; sim/FRM + formal NOT_EXECUTED; mutant-kill 0/2; SVA validity 0/3 under Judge |
| B — closure works? | first-pass / success / iterations | **FAIL** | mechanics ✅ (bounded, 1.0 ledgered); effectiveness ❌ — 0 rescues, success 0.375 via drift, T2/T7 actively harmed by non-elitist regen |
| C — efficient? | latency/tokens/CPU/cost | **FAIL** | v1 recorded no per-call usage (fix implemented this review for v2); bake-off per-call data exists (46.3s avg) |
| D — review scalable? | engineer time / burden | **FAIL** | nothing measured (all fields None by design, never fabricated) |
| E — reproducible? | cross-env variance | **FAIL** | envelope ✅ single-env; Docker↔WSL benchmark portability unrun |

**Decision: P0 GATE = NO-GO.** Five fails, zero disputed — and that is the
system working as designed: every failure was caught, ledgered, and escalated
instead of shipped. No GPU, no SFT, no bigger-model spend is authorized by
this result.

## What passed (keep)

- Evidence-First spine: audit 1.0, chain valid, 5/5 failures escalated, 0 silent passes.
- Bake-off selection + ablation discipline (hold BoN=3, gain-per-cost = 0).
- Lint/Yosys truth layer on real `wb_dma` RTL.
- sby refusal doctrine: no vacuous proofs.

## Prescriptions (sequenced, no training)

1. **Elitist closure** (loop fix): carry the best candidate forward; never let
   regen discard a round-1 winner (kills the T2/T7 backfire class).
2. **Efficiency instrumentation** — DONE this review (`run_one` records
   latency/tokens/cost; 120 tests green). Effective P0-D v2 re-run.
3. **Constrained generation**: SVA/TB skeletons with LLM-filled blanks instead
   of free-form codegen (attacks the 0/5 code-task rate without new models).
4. **Wire sim/FRM + real sby properties** into the loop (clears A's
   NOT_EXECUTED rows).
5. **Exception-review dashboard measurement** (Gate D) + **Docker↔WSL
   portability run** (Gate E), then **P0 re-gate**.

Sign-off: PENDING (named human required per `policy.HUMAN_SIGNOFF_ACTIONS`).
