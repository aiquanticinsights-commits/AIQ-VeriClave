# Capability Result Reconciliation (P4-01)

> One authoritative index of results per P4–P7 plan §7.1. Maturity levels per
> §3 (E0 Designed → E4 Developer Validated). Rule: no E1/E2 result is presented
> as E3/E4. Source program record: developer sync v1.0 (13-Oct-2026, P3 CLOSED).
> Ledger rule: append-only; corrections are new rows.

## P0 — system demonstration (V8 GO, 2026-09-30; sign-off 2026-10-01)

| Capability | Benchmark / model / config | Raw result → derived metric | Verdict / maturity | Evidence artifact |
|---|---|---|---|---|
| A: system works | gates_demo + wb_dma, frozen P0 pipeline | C1 = 95.12%, acceptance fn 6/6 | PASS / **E2** (demonstrated; single-design family) | `P0GATE_REVIEW_V8.md`, `P0_SIGNOFF_V8.md` (human ACCEPT) |
| B: closure works | same + fault-hints/localizer | 2 in-run rescues, hard invariant holds | PASS / **E2** | same as above |
| C: efficiency | same + ledgers | cost/latency/tokens tracked; $0.50/task = target, not claim | PASS (measured, not bounded) / **E2** | same + eval `tokens` reports |
| D: review scales | live reviewer data | 20% review rate, 18.7 s median | PASS / **E2** | same as above |
| E: reproducible | SBY smoke 9/9 (260 MB pinned image); Docker↔WSL 7/7 incl. mutant agreement + one SURVIVED | both committed | PASS / **E3** (independently frozen envs agree) | `SBY_SMOKE.json`, `E2_PORTABILITY_REPORT.json` |
| Formal gates A/B/D/E | gates_demo ok+buggy pairs, SymbiYosys v0.68 | PASS/FAIL both directions correct | PASS / **E2** | `GATES_ABDE.json`, `FORMAL_WB_DMA.json` |

## P1 — limitation findings (CLOSED, all APPROVED)

| Item | Result | Maturity | Evidence |
|---|---|---|---|
| A_IRQ formal disposition | UNPROVEN/toolchain limit; sim/FRM-covered alternative | Finding / **E2** | `P1_01_A_IRQ_DISPOSITION.json` |
| T4/R2/R5 capability walls | Documented, not solved | Finding / **E2** | `P1_02_*` |
| C-band scale validation | Validated within bounded workflow | **E2** | `P1_03_*` |
| Portability/reproducibility | Docker/WSL + env lock-in plan | **E2→E3** (environments frozen) | `P1_04_*`, `PORTABILITY*.json`, `ENVIRONMENT_LOCKIN_PLAN.md` |

## P2 — frozen benchmark (CLOSED 2026-10-01; training NOT authorized)

| Milestone | Raw result | Verdict / maturity |
|---|---|---|
| M1 frozen benchmark | established pre-run | COMPLETE / **E2** (`P2_BENCH.json`) |
| M2 alt models (llama-3.1-8b, deepseek-coder-6.7b) | T4 70%/55% vs 90% bar; R2 0–3/20 vs ≥4 | measured / **E2** (`P2_M2_*.json`) |
| M3 meaningful improvement | walls stand | **FAIL** (recorded, not hidden) |
| M4 no P0 regression | PASS | **E2** |
| M5 dataset baseline | 278 generations catalogued; overwhelmingly negative; **no held-out split** | baseline only — **not SFT-ready** |
| M6 training decision | **NO-GO** | decision logged |

## P3 — four tracks (CLOSED; system direction validated)

| Track | Raw result | Verdict / maturity |
|---|---|---|
| P3-A 14B local (Qwen2.5-Coder-14B Q4_K_M) | R2 17 closes, FA=0 re-derived; T4 re-measure partial | partial — final verdict sign-off pending |
| P3-B ensemble (llama+DeepSeek) | union ceiling 3/20 < bar 4 — capability, not selection, problem | **FAIL** (informative) |
| P3-C structured pipeline | 8/20 closes, 0 FA (baseline 0→8) | partial — final verdict + Qwen amendment pending |
| P3-D data readiness | 278 generations; negatives-rich; no held-out; diversity 1 family / 4–16 bits | **not SFT-ready**; held-out + diversity required |
| Vivado repeat execution | qualified functions reproducible (`VIVADO_GATES.json`, adapter) | **E2→E3** for qualified functions only — never "full Vivado support" |

## Carried constraints (inputs to P4+, not reopeners)

| ID | State per program record | Consumer |
|---|---|---|
| d1 scale (266/1000 positive trajectories) | **parked** unless reauthorized; no auto R-4 cycles | P4 backlog |
| d5 diversity | new design families required, not more same-family cases | P4-04, P5 |
| d8 economics | $0.50/task is a measurement target; full cost vector per §6.3 | every eval report |

## Supersession status
Active record: this file. Prior per-phase reviews (`P0GATE_REVIEW*.md`, `P1/P2_COMPLETION_REVIEW.md`, track verdict JSONs) remain frozen source evidence — referenced, never rewritten.
