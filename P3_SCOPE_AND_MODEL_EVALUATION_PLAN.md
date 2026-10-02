# P3 Scope and Model Evaluation Plan

Date: 2026-10-01 (four-track restructure approved 2026-10-02)
Status: **Scope frozen; tracks execute independently; P3-A requires one model download (authorized)**
Predecessors: P0 (V8 GO), P1 (CLOSED), P2 (CLOSED, `P2_COMPLETION_REVIEW.md`)
Reviewer: SSB (Satish Sura, Founder & CEO)

## 0. Track structure (approved)

P3 is executed as **four controlled tracks**, not one broad iteration:

```
P2 CLOSED
   │
   ▼
P3 experimental scope frozen
   │
   ├──► P3-A: 14B local model (model track)
   ├──► P3-B: llama + DeepSeek ensemble (model track)
   ├──► P3-C: structured / verifier-guided generation (system track)
   └──► P3-D: training readiness (data track)
             │
             ▼
       P3 decision gate
             │
       ┌─────┼─────┐
       ▼     ▼     ▼
    model  system  data
   works   works   ready
```

Two decisions are explicitly **rejected** by this scope:

- **Option A (provision RAM to load gpt-oss-20b) is NOT taken.** It changes the experimental hardware environment and still would not establish that a larger model solves the walls. It is not the cleanest comparison.
- **SFT/LoRA is NOT started merely because the corpus was baselined.** Training remains conditional on measured evidence (§11).

Every track keeps the same **host, prompts, benchmark, verifier, judge, closure rules, and acceptance bars**. That invariance is what makes the tracks comparable and is the reason P3-A is a download on this host rather than a hardware change.

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

P3 is specifically about **candidate-quality / model-capability improvement**, not another broad architecture iteration. Four tracks, three of which are model-free or model-agnostic:

| Track | Purpose | Needs a new model? |
|---|---|---|
| **P3-A — Stronger local model** | Determine whether a 14B-class local model materially improves T4/R2 on this same host. | Yes (one authorized download) |
| **P3-B — Ensemble / complementary models** | Exploit the measured candidate diversity of llama + DeepSeek. No new model required. | No |
| **P3-C — Structured candidate generation** | Attack the known T4/R2 failure mechanisms with constrained generation, decomposition, candidate extraction, and verifier-guided ranking. System-level, not training. | No |
| **P3-D — Training readiness** | Determine whether the existing corpus can support SFT/LoRA later. **No training.** | No |

**P3-B rationale.** The R2 data already indicates complementary behaviour: llama closes 0/20, DeepSeek closes 3/20, and they close *different* cases. Exploiting that complementarity costs nothing and needs no new model, which makes it the cheapest available test of "does the gap close without scaling the model?"

**P3-C rationale.** T4 failures are instruction-following/format failures and R2 failures are arithmetic/truncation failures. Both are attackable by structure (decompose, constrain, verify, rank) rather than by scale, so P3-C is a system-level lever that is independent of model size.

**P3-D rationale.** Dataset readiness is assessed on measured properties (size, diversity, success/failure balance, verifier labels, contamination, held-out separation, trajectory quality, failure-mode coverage) — not assumed. It proposes, never performs, training.

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

**Invariant across all four tracks:** same host, same prompts, same benchmark, same verifier, same judge, same closure rules, same acceptance bars. Only the model (P3-A), the candidate set (P3-B), or the generation structure (P3-C) changes.

Assessed inventory (measured 2026-10-01, `lms ls`):

| Model | Params | Quant | Size on disk | Role in P3 |
|---|---|---|---|---|
| `meta-llama-3.1-8b-instruct` | 8B | Q5_K_M | 5.73 GB | Frozen baseline (both tracks) |
| `deepseek-coder-6.7b-instruct` | 6.7B | Q4_K_S | 3.86 GB | P2 candidate / P3-B ensemble member |
| `openai/gpt-oss-20b` | 20B | MXFP4 | 12.11 GB | **Excluded** — see §6 |

**P3-A candidate: one 14B-class Q4 model (~9 GB), downloaded to this host.** It is the largest credible fit in the ~11 GB usable budget and therefore preserves same-host comparability, which is precisely what loading gpt-oss-20b on new hardware would destroy. Spend is zero (open weights); the only requirement is that the download be explicitly authorized (it is). The exact model and quantization must be recorded in the P3-A spec before its first sample — no post-hoc model swap.

## 6. Hardware / resource constraints

Measured on this host:

- Total physical RAM: **13.3 GB**; usable-for-model budget **~11 GB**.
- GPU: AMD Radeon 680M, **2 GB** adapter RAM — not a viable offload target.
- Free disk: **42.2 GB** — sufficient for one 14B-class Q4 (~9 GB).
- `openai/gpt-oss-20b` weights alone are **12.11 GB**, so it cannot load here.

**Decisions:**

- **Rejected: provision RAM to load gpt-oss-20b.** Changing the host would break same-host comparability with the frozen P2 anchors without establishing that scale solves the walls.
- **Adopted: P3-A = one 14B-class Q4 download onto this host.** Same host, same benchmark, frozen protocol transfers unchanged. Zero spend, ~9 GB disk, fits the ~11 GB budget.
- **P3-B/C/D require no new model and no new hardware** — they run on the models already present.

**Standing guardrail unchanged:** the LM Studio load guardrail is not disabled or bypassed. A model that cannot load within budget is recorded as not-runnable, never forced.

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
