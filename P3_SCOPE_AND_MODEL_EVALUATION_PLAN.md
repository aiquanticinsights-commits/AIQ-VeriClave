# P3 Scope and Model Evaluation Plan

Date: 2026-10-01
Status: **DRAFT — awaiting human approval, and blocked on one resource decision (see §6)**
Predecessors: P0 (V8 GO), P1 (CLOSED), P2 (CLOSED, `P2_COMPLETION_REVIEW.md`)
Reviewer: SSB (Satish Sura, Founder & CEO)

## 1. P2 findings carried forward

From `P2_M3_VERDICT.json` (P2-M3 CLOSED, finding approved; verdict FAIL):

| Track | llama-3.1-8b | deepseek-coder-6.7b | Frozen bar | Result |
|---|---|---|---|---|
| T4 (N=20, temp 0.7) | 14/20 = 70% | 11/20 = 55% | ≥ 90% | **WALL STANDS** |
| R2 (20 cases, arm B) | 0/20 closed | 3/20 closed | ≥ 4 closes | **WALL STANDS / UNDER BAR** |

Carried-forward findings:

- **F3-T4** — instruction-following / final-answer-format capability wall. Confirmed at N=20. The earlier 5-case probe overstated the apparent severity; N=20 is the reliable baseline. Required bar stays ≥ 90%.
- **F3-R2** — width/truncation literal-repair wall. Confirmed: baseline closes 0/20, the P2 candidate closed 3/20 (cases `P2-R2-00/01/16`, one first-pass), providing evidence of a narrow model-specific capability difference on this R2 set; the sample is too small to generalize.
- **F3-ZERO-FP** — no false acceptances by either model. The verifier rejected every incorrect output. This must be preserved: any future candidate that produces a false acceptance is rejected outright, regardless of T4/R2 gains.
- **F3-NO-TRAIN** — training not authorized. P2-M6 NO-GO on scale (~10^2 turns), diversity (2 task families, 1 design), and success density (mostly negative examples).
- **F3-ENV** — the only stronger model on disk (`openai/gpt-oss-20b`) was recorded as not-runnable under the 11 GB measured environment. That is an infrastructure limitation, **not** a model-quality conclusion, and it is exactly what P3-A is meant to resolve.

## 2. P3 objective

P3 is specifically about **candidate-quality / model-capability improvement**, not another broad architecture iteration. Two tracks:

| Track | Purpose |
|---|---|
| **P3-A — Stronger local model evaluation** | Determine whether a stronger open/local model materially improves T4/R2 under the identical frozen verification system. |
| **P3-B — Dataset / training readiness** | Determine whether the existing corpus could support SFT/LoRA later. Readiness assessment only — **no training in P3**. |

Sequencing is strict: scope → freeze the experiment → stronger local-model evaluation → only then decide whether training or another intervention is justified.

The primary question P3 must answer:

> Can a stronger open model, under exactly the same verification system and frozen benchmark, materially reduce the T4/R2 capability gap?

- If **yes** → P3 can justify a focused model-selection/adaptation path.
- If **no** → the limitation is demonstrably not solved by scale alone, and investigation moves to dataset engineering, prompting/structured generation, verifier-guided generation, or other system-level interventions.

## 3. T4/R2 capability-wall definition

A wall is **confirmed** when, under the frozen benchmark, a model fails a bar that is pre-registered, verifier-scored, and reproducible at N=20.

- **T4 wall** — the model does not reliably produce a reason-then-`Answer:X` response where the final standalone letter matches the grader's parsed answer. Bar: **≥ 90%** at N=20. Not lowered in P3.
- **R2 wall** — the model cannot repair an over-wide decimal/width literal to the correct signal width within the frozen closure rules (min 2 rounds, approvals ≥ 2, arm B). Bar: **≥ 4/20 closes**, **zero false acceptances**.
- **False acceptance** — an output the verifier marks correct that is actually wrong. A single false acceptance **rejects** the candidate for that track. Non-negotiable.

## 4. Frozen P2 baseline (comparison anchors)

The following are frozen and reused as-is. No re-measurement, no re-grading, no re-tuning of anchors.

| Artifact | Role |
|---|---|
| `P2_BENCH.json` | Frozen spec: T4 prompt/grader identity, R2 20-case table, R2 grader identity, pre-registered bars. |
| `P2_M2_LLAMA.json` | Baseline: T4 14/20, R2 0/20. |
| `P2_M2_DEEPSEEK.json` | P2 candidate: T4 11/20, R2 3/20. |
| `scripts/p2_bench.py` | Runner. Model injected via `query_fn`; frozen `repair.py` / `p102_t4_reason_probe.py` untouched. |
| `P0_SIGNOFF_V8.md`, `P1_COMPLETION_REVIEW.md` | Acceptance envelope that must be preserved. |

## 5. Candidate local models

P3-A candidate must be **materially stronger** than the 8B/6.7B class, on disk, and open/local. No cloud APIs, no paid endpoints, no hosted inference.

Assessed inventory (measured 2026-10-01, `lms ls`):

| Model | Params | Quant | Size on disk | Runnable here? |
|---|---|---|---|---|
| `meta-llama-3.1-8b-instruct` | 8B | Q5_K_M | 5.73 GB | Yes (P2 baseline) |
| `deepseek-coder-6.7b-instruct` | 6.7B | Q4_K_S | 3.86 GB | Yes (P2 candidate) |
| `openai/gpt-oss-20b` | 20B | MXFP4 | 12.11 GB | **No — see §6** |

`gpt-oss-20b` is the only stronger model present. Any additional candidate (e.g. a 14B-class code model) would require a **new download**, which is outside the current standing constraints (zero spend, no downloads) and therefore needs explicit human authorization.

## 6. Hardware / resource constraints  ⚠ BLOCKER

Measured on this host:

- Total physical RAM: **13.3 GB**; free with no model resident: **~2.7 GB** (OS + WSL + LM Studio + tooling occupy the rest).
- Usable-for-model budget measured earlier: **~11 GB**.
- GPU: AMD Radeon 680M, **2 GB** adapter RAM — not a viable offload target for a 12 GB model.
- `openai/gpt-oss-20b` weights alone are **12.11 GB**, before KV cache, context buffers, and the OS.

Conclusion: `gpt-oss-20b` **cannot** be loaded on this host. The LM Studio load guardrail refuses it, and the arithmetic agrees — this is a genuine physical limit, not a misconfiguration. Attempting to force it would risk system instability and would violate the standing resource guardrail.

**This is a human decision, not an engineering choice. P3-A cannot start until one of the following is authorized:**

- **Option A — Provision RAM.** Run P3-A on a host with ≥ 24 GB usable RAM (32 GB physical recommended). No code or data change; the frozen protocol transfers unchanged. Requires hardware authorization.
- **Option B — Authorize one model download** of a stronger model that fits the ~11 GB budget (a 14B-class Q4 model is ~9 GB and is the largest credible fit). Spend is zero (open weights); only the download needs authorization. Smallest change to the current host.
- **Option C — Defer P3-A; run P3-B only.** Proceed with dataset/training-readiness assessment now, and schedule P3-A when a suitable host or model is available.

Recommended: **Option B** — it keeps the scientific value of P2 intact (same host, same frozen benchmark, same verifiers) with the least deviation. Option A is cleaner on paper but changes the host, which weakens same-host comparability with the P2 anchors.

## 7. Controlled experiment protocol

```
Frozen P2 benchmark (P2_BENCH.json, byte-identical)
        ↓
Same prompts  ·  Same verifiers  ·  Same judge
Same closure rules  ·  Same 20 T4 samples  ·  Same R2 20 cases
        ↓
Stronger local model (candidate under test)
        ↓
Measure T4 + R2
        ↓
Compare against frozen llama / deepseek baselines
```

Rules:

1. **No spec change after the first P3 model sample.** Any change voids the run and requires a new frozen spec commit.
2. **Same prompts, graders, and closure rules as P2.** Reuse `scripts/p2_bench.py` unchanged; the candidate enters only through the model id.
3. **Same T4 N=20, temperature 0.7.** Same R2 20 cases, arm B, min 2 / max 3 rounds, approvals ≥ 2.
4. **Order:** baseline anchors are read from the frozen P2 artifacts (no re-run needed); the candidate is measured once; the verdict is computed last.
5. **R2 set expansion is a separate, pre-registered step** (see §8). An expansion must be committed and frozen **before** the candidate's R2 run, and results reported against both the 20-case frozen set and the expanded set.
6. **Determinism discipline:** verifier-scored labels only; no model-graded labels; no manual relabeling after seeing results.
7. **Zero spend, local only.**

## 8. Evaluation metrics

**T4 (N=20 per model):** accuracy; per-sample outcome; `marked:C` vs `last:X` vs unparseable breakdown; tokens; latency. Bar: **≥ 90%**.

**R2 (20 cases per model, arm B):** closures; first-pass correctness; mean rounds to close; false acceptances (**must be 0**). Bar: **≥ 4/20 closes, 0 false acceptances**.

**R2 set expansion (pre-registered, before candidate run):** extend the R2 set with additional independent width/truncation cases across more widths and more than one design family, to remove the single-design-family weakness identified in P2-M5. Target: ≥ 40 cases total, ≥ 2 design families, all cases genuine truncation bugs with deterministic `expect = value mod 2**width`. The expansion is committed and frozen ahead of the candidate's R2 run; it never replaces the original 20.

**Comparison requirement:** the improvement claim must be **repeatable** — a single 20-sample win is not sufficient on its own. Any claimed improvement must hold on the frozen 20-case R2 set and on the expanded set, with no unacceptable regression.

## 9. Acceptance / rejection criteria

**Acceptance (P3-A success).** A candidate passes only if **all** of the following hold:

1. It **pre-defined, repeatable** improvement on **at least one confirmed wall** (T4 or R2).
2. **T4 bar retained at ≥ 90%** (not lowered).
3. **R2 bar retained at ≥ 4/20 closes** on the frozen set, **and** no regression on the expanded set.
4. **Zero false acceptances** on both R2 sets.
5. The frozen P0/P1 acceptance envelope is preserved (see §10).

**A higher score alone is not success.** "New model scores higher" is explicitly rejected as an acceptance criterion.

**Rejection.** The candidate is rejected if it: misses both bars; improves one track while regressing the other; produces any false acceptance; breaks the P0/P1 envelope; or requires a post-hoc spec change to pass. A miss is recorded as a result, not repaired into a pass, and the pre-registered bar is never relaxed to convert a miss.

**On failure**, the recorded conclusion is that model scale alone does not close the gap, and the investigation moves to system-level interventions (dataset engineering, prompting/structured generation, verifier-guided generation) — with the failure itself as the evidence that justifies that direction.

## 10. Regression protection against P0/P1

Any P3 change must leave the P0 V8 GO decision and all P1 findings **unchanged**:

- Full `unittest` discovery green (331 tests at P2 close) + `check_evidence.py` PASS.
- P0/P1 evidence files **byte-unchanged**; frozen P0/P1 artifacts are never overwritten.
- R5/B control still closes under the candidate (it closed for the P2 candidate at round 2).
- P1 open findings (A_IRQ formal status, T4/R2 walls, C-band breadth, cross-host portability) remain exactly as dispositioned; P3 may not silently close or alter them.
- If any P0/P1 artifact would need to change, P3 stops and the change is raised as a separate, human-approved item.

## 11. Training decision gate

**No training in P3.** No SFT, no LoRA, no fine-tuning, no dataset consumption for training.

P3-B is a **readiness assessment** of the existing corpus (`P2_M5_DATASET.json`: ~158 turns, 21 prompts, mostly-failure density, single design family, verifier-labeled). It answers only: *could this corpus support SFT/LoRA later, and what would have to change first?* It trains nothing and claims no trainability.

A training path may be **proposed** (not started) only if:

1. P3-A **passes** per §9 — a stronger model demonstrably reduces the wall gap; **and**
2. P3-B finds the corpus insufficient but identifies a concrete, sufficient path to a sufficient one (scale, diversity, positive-example density); **and**
3. A separate, human-approved plan exists with its own frozen spec and evidence gates.

If P3-A fails, the training question is deferred and the direction becomes system-level intervention.

## 12. Human approval / sign-off

| Item | Disposition | Approval |
|---|---|---|
| P3 scope (this document) | Awaiting review | PENDING |
| P3-A candidate + host decision (§6 A/B/C) | Blocked — human decision required | PENDING |
| P3-B readiness scope | Awaiting review | PENDING |
| R2 set expansion (§8), if authorized | Not started | PENDING |
| P3-A experiment spec freeze | Not started | PENDING |
| Training authorization | **NOT AUTHORIZED** | — |

No P3 model run may begin before this scope is approved **and** the §6 resource decision is made and recorded. No P3 change alters any P0 or P1 evidence or decision.
