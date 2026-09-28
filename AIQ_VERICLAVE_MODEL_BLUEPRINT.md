# AIQ-VeriClave — Product Model Blueprint (verification-side, developer-facing)

> Goal: a reusable model *system* other developers run to get **>95% accuracy**
> on verification tasks — not a 95%-accurate single checkpoint (no such open
> model exists; best published single-model numbers sit at 57–89% per task).
> The >95% is **system-level**: ensemble generation + machine verifiers +
> iterative closure + human sign-off, with every point earned by a named
> mechanism in §3 and measured by §6.
>
> Prior doc: `V2X-OBU-AIS230/docs/AI_VERIFY_EXECUTION_PLAN.md` (Part A =
> internal adoption pipeline; Part B = AIQ-VeriClave v0 thesis). This blueprint
> generalizes Part B into a shippable product.

Research anchors (primary sources): Qwen3-Coder-Next tech report (arXiv
2603.00729) · MAV/BoN-MAV (arXiv 2502.20379) · RouteMoA (ACL 2026) · TUMIX
(ICLR 2026) · Agent Forest (arXiv 2402.05120) · PRO-V-R1 (arXiv 2506.12200) ·
BugGen (arXiv 2506.10501) · BluesFL (arXiv 2605.17290) · GoGoTB (arXiv
2607.26181) · CorrectBench (arXiv 2411.08510) · Repair-R1 (arXiv 2507.22853)
· AssertLLM/AssertLLM2 (arXiv 2402.00386, 2605.27472) · CodeV-R1 (NeurIPS'25)
· LiK · VeriPilot · VCDiag · SWE-rebench Jan-2026 community runs.

---

## 1. What "accuracy >95%" means here (claim decomposition)

No single open model clears 95% on hard verification tasks, so the claim is
decomposed per task, each with the mechanism that earns it:

| # | Task claim | Target | Earning mechanism (§3) |
|---|---|---|---|
| C1 | Mutant-kill rate on requirement-linked blocks, ≤3 closure iterations | ≥95% | BoN sampling (n=5–8) + machine-verifier vote + GoGoTB root-cause loop |
| C2 | Generated SVA both syntactically valid AND FPV-proven | ≥95% | AssertLLM-style 3-LLM decomposition + Judge filter (CorrectBench discipline: unproven assertions are discarded, never shipped) |
| C3 | True bug inside Top-3 shortlist (human confirms Top-1) | ≥95% | BluesFL slicing + MAV aspect verifiers; human confirms, machine ranks |
| C4 | Coverage sign-off with zero silently-dropped gaps | 100% auditability | GoGoTB spec-grounded bins + stall detector + disposition ledger |
| C5 | False-positive rate on golden-vs-golden (reference self-check) | <1% | CodeV-R1 lesson: rule-based equivalence beats LLM testbenches (their 2.7% vs 7.6% misclassification); FRM≡RTL gate blocks everything else |

Single-shot pass@1 is reported for reference only — the product contract is
*C1–C5 after closure*, which is also exactly what a product launch needs
(deterministic behavior, auditable evidence, bounded cost).

## 2. Base-model selection (best LLMs for each role)

Selection criteria: open weights, Apache-2.0/MIT-compatible license,
tool-calling native, 128K+ context (SoC-scale blocks + VCD slices +
trajectories), inference cost per task.

| Role | Pick | Why (verified numbers) | Alternatives |
|---|---|---|---|
| Primary generator (TB/FRM/SVA drafts) | **Qwen3-Coder-Next** (80B tot / 3B active, 256K ctx, Apache-2.0) | SWE-Bench Verified ~71% ≈ models with 10–20× active params; scaffold avg 92.7; agentic training (20K parallel envs) = tool-use robustness; 3B-active = cheapest $/task in its band | Qwen3-Coder-30B-A3B (same family, larger active) |
| Diversity generators (BoN n=5–8) | **DeepSeek-V3.2** (671A37, ~70–72%), **GLM-4.7** (~74%), **MiniMax-M2.1** (~71–75%), **Kimi-K2.5** (~73%) | Top open agentic band; different labs = uncorrelated failure modes, which is what makes voting work (Agent Forest: +4–9% code gains; small-ensemble can beat larger single) | Kimi-K2-Thinking (SWE-rebench 43.8% open lead) for hard cases |
| Judge / terminator | Qwen3-Coder-Next (same) + PRO-V-style Judge head | TUMIX result: LLM-as-Judge termination keeps peak accuracy at **49% of inference cost** (min 2 rounds — overconfident early stopping is the documented failure) | Majority-vote fallback when judges disagree |
| Cheap aspect verifiers | Small/local models (Ollama-class) + **deterministic tools** | MAV finding: weak verifiers improve even strong generators (+10–20%); tools (Verilator/Yosys/SymbiYosys/sv-parser) vote free and never hallucinate | VCDiag-style XGBoost triage (~94% top-3, classical ML cost) |
| Router scorer | 86M-class encoder (RouteMoA pattern: mDeBERTa-v3-base) | Predicts per-task top-k without inference; 97.9% top-3 hit; cuts MoA cost **89.8%** / latency 63.6% | Heuristic router first (see `router.py`), learned scorer at PHASE 5 |

Deliberately NOT the core: 480B/671B flagships (inference cost destroys $/bug economics), closed APIs (license + data-retention vs RTL confidentiality), 2023-era Verilog fine-tunes (pre-reasoning, syntax-level).

## 3. System architecture (integration is the model)

```
 SPEC + RTL ─► ROUTER (scorer, k=3 generators) ─► GENERATORS (BoN, n=5–8)
      │                    │                              │
      │                    ▼                              ▼
      │            MACHINE VERIFIERS (vote, $0)    LLM ASPECT VERIFIERS
      │            ├─ syntax: Verilator/Yosys/sv-parser
      │            ├─ functional: Python-FRM ≡ RTL sim
      │            ├─ formal: SymbiYosys SVA prove
      │            ├─ mutation: BugGen-seeded kill check
      │            └─ trace: requirement-ID linkage present?
      │                    │                              │
      │                    ▼                              ▼
      │            JUDGE (majority + CorrectBench self-check + TUMIX stop rule)
      │                    │
      ├─ pass ─► ARTIFACT (TB/SVA/report + evidence ledger)
      └─ fail ─► CLOSURE LOOP (GoGoTB root-cause taxonomy → targeted regen,
                 ≤3 rounds → human sign-off; Repair-R1 discipline: discriminative
                 tests BEFORE any patch suggestion; patches never auto-merge)
```

Why this earns >95%: each unreliable LLM output must survive *independent*
machine checks (syntax, equivalence, proof, kill, trace) plus a Judge that
discards rather than repairs-into-truth; iteration budget is bounded and every
residual is dispositioned (C4). This is MAV/BoN-MAV + RouteMoA + TUMIX +
PRO-V/GoGoTB/CorrectBench composed — each cited gain (+10–20% MAV, 49% cost
TUMIX, 8.8× PRO-V speed, +28pp GoGoTB closure) stacks on a different failure
mode, which is precisely why the ensemble beats any single checkpoint.

## 4. Dataset plan (extensive use — the actual moat)

| Tier | Source | Volume (projection) | License/provenance rule |
|---|---|---|---|
| T0 own assets | `verif/`, `sim/`, VCD libraries, `ais230_traceability.csv`, sign-off reports (RideProtect/MIPI/V2X) | 10Ks vectors + 100s seeded bugs to start, compounding via flywheel | clean, owned, contamination-free by construction |
| T1 open corpora | OpenTitan IPs (BugGen's 5-block protocol), AssertLLM2 (83 designs + buggy variants), VCDiag-style waveform sets, VerilogEval/RTLLM (**calibration only**, Rouge-L ≤0.5 filter per CodeV-R1) | 100Ks examples | Apache-2.0/MIT only; pin commits; record per-sample license |
| T2 synthetic flywheel | round-trip NL↔code with equivalence filter (CodeV-R1 method); BugGen-seeded mutants = infinite localization/repair labels; GoGoTB testpoint→bin closure traces = process supervision | unbounded, quality-gated (golden-vs-golden + kill-verified or discarded) | generated in-house → owned |
| T3 trajectories | teacher traces (Testcase/FRM/Judge roles) kept iff Verilator ≡ FRM on all vectors (PRO-V V(·) filter) | 10–50K accepted trajectories | teacher outputs are transient; only machine-verified traces persist |

Flywheel (compounding advantage competitors lack): every customer IP run through
§3 emits mutants → localizations → repairs → closures → next training round.
Static-GitHub-trained rivals cannot replicate a living loop.

## 4.1 External corpora annex (verified Sep 2026; extends §4, does not replace T0/T2)

Registry: `datasets.py` (machine-readable; every entry carries license posture,
consumer stage, and curation caveats — `test_datasets.py` enforces completeness).

| Corpus | Verified scale | Consumed by | Standing correction to the proposal |
|---|---|---|---|
| CircuitNet 2.0 (ICLR'24) | 10,000+ samples; CPU/GPU/AI-chip; 14nm FinFET commercial flows; routability/timing/power | PHASE 5 PPA/congestion auxiliary head; WS4 trade-offs | Backend-stage data, NOT RISC-V-mapped; congestion/PPA features only, never RTL-correctness labels |
| DeepCircuitX (ICLAD'25) | 4,000+ repos; repo/file/module/block; 57K+ GPT-4/Claude CoT annotations; 2,078 RISC-V repos; netlists + PPA (HF, 1.04GB) | PHASE 4 SFT reasoning traces; block-context training | CoT is silver-standard (LLM-generated): FRM-equivalence filter before training |
| HLSDataset (ASAP'23, UT-LCA) | ~9,000 Verilog/FPGA; Polybench/Machsuite/CHStone/Rosetta; Vivado HLS+impl reports; ~50GB | Synthesis-aware features; Arty regeneration via their scripts | Targets ZU9EG/XC7V585T, NOT Arty — re-run flows for Arty claims; "Kaggle HLS" is not the artifact |
| Koios 2.0 | 40 DL Verilog benchmarks, 12K–1.6M primitives, VTR-clean | Open-flow sanity + heterogeneity (pairs HLSDataset) | Benchmarks, not profiles — complements, doesn't replace |
| OpenTitan bug histories (arXiv 2402.00684 method) | 4,148 issues → 170 curated RTL bugs; 52.9% security; 55% single-file | WS5 closure eval + WS6 repair realism check vs BugGen synthetics | 28% noise — raw scraping FORBIDDEN; replicate closed-issue + fix-linkage + AST-footprint curation first |

Net effect on robustness: PPA/congestion awareness (tapeout realism), CoT
reasoning traces (understanding depth), synthesis profiles (FPGA-grounded
resource/timing judgment, Arty-regenerated), and human-bug realism (closure
loops hardened against synthetic-only^(blindness)). The internal flywheel
remains the contamination-free core; externals augment, never replace.

## 5. Training recipe (CPU-first phased roadmap; GPU figures = optional future)

> Standing decision (adopted): the primary path is **CPU/local/open-compute-first
> development**. GPU acceleration is an *optional optimization introduced only if
> experiments prove it necessary* — never an architectural dependency. The system
> must keep functioning with zero GPU. Earlier GPU-hour estimates are retained
> below classified as **Optional Future Accelerated Compute**.

- **PHASE 0 — CPU-first P0**: open-source stack (§14), open models, no training,
  local CPU, deterministic verification, BoN, Judge, evidence ledger, C1–C5
  baseline. Gate: baselines recorded, flywheel schema frozen.
- **PHASE 1 — Model benchmark**: 1B/3B/7B-class open models evaluated on CPU
  (Stage A discovery → Stage B baseline pick on correctness + resources +
  latency + cost, never general benchmarks alone). Gate: baseline selected with data.
- **PHASE 2 — Verification system**: selected model + BoN + Judge + closure +
  ledger + C1–C5 evaluation. Gate: §6 target bands on own blocks.
- **PHASE 3 — Proprietary dataset**: verified trajectories, mutants, failures,
  localizations, repairs, proof outcomes, closure histories. Gate: corpus
  versioned with licenses + contamination checks.
- **PHASE 4 — SFT / LoRA**: only if PHASE 0–2 identify a model-specific limitation.
  Gate: beats the frozen baseline on AIQ metrics (else dropped), Eval1-style
  func-correctness ≥ PRO-V-R1-8B band (57.7%).
- **PHASE 5 — Specialized models** (router, classifiers, reranker, localization):
  cheaper/more reliable than the generalist on narrow jobs. Gate: beats frozen
  baseline on cost/reliability, else dropped. (Supersedes former "P2".)
- **PHASE 6 — GRPO experiment (CONDITIONAL)**: only if a measured residual
  failure remains after SFT that RL can plausibly fix (poor candidate selection
  — yes; incomplete context, engine timeouts, wrong TB/FRM, ambiguous
  requirements — no). (Supersedes former "P3".) Gate: the question "what
  failure remains that GRPO fixes?" answered with data first.
- **PHASE 7 — Productization**: local deployment first; optional open cloud /
  accelerated compute; GGUF + Ollama/vLLM endpoints + OpenAI-compatible server
  + MCP surface; Apache-2.0 weights; versioned releases with eval cards.
  Gate: §6 on held-out customer-style IPs, never on training blocks.
  (Supersedes former "P4".)

Compute framing: CodeV-R1 cost ~2,656 A100-h for 7B; 30B-class SFT+GRPO is estimated in single-thousands of GPU-hours — quoted as a band under **Optional Future Accelerated Compute**, firmed at phase gates from measured sim costs (sim cluster first, GPUs second, and only if proven necessary).

## 6. Rating protocol (how >95% is proven, per task)
| Task | Metric | Reference best (published) | AIQ-VeriClave target | Falsifier |
|---|---|---|---|---|
| Mutant kill (C1) | kill ratio, ≤3 iters | BugGen 94.2% *generation* acc.; GoGoTB +28pp closure | **≥95%** | stalls <90% after 3 iters |
| SVA validity (C2) | FPV-proven / generated | AssertLLM 88–89%, 93–97% COI | **≥95% post-Judge** | Judge precision <90% |
| Localization (C3) | bug in Top-3 | BluesFL 24/24 Top-1 ($0.25); LiK 93.3% line-level | **≥95% Top-3** | <85% on our blocks |
| Sign-off (C4) | gaps dispositioned | GoGoTB 98.4/97.2/83.2 + audit | **100% ledgered** | any silent drop |
| Self-check (C5) | golden-vs-golden FPR | CodeV-R1 rule-based 2.7%→0.3% | **<1%** | ≥2% blocks release |
| Cost | $/verified task | PRO-V 91s; BluesFL $0.25/bug | **≤$0.50 avg** | exceeds manual equiv. |

Generation benchmarks (VerilogEval/RTLLM) reported for reference only —
mid-tier expected and openly stated; the product is rated on the six rows above.

## 7. Significance vs other models
- **vs CodeV-R1/VeriGen-class**: they maximize spec→RTL pass@1 (~27%+ wrong with no harness); AIQ-VeriClave maximizes *caught* errors with machine proof. Complementary, not competing — their generators are admissible *inside* our BoN layer, judged by our verifiers.
- **vs PRO-V-R1**: closest cousin and intended Stage-1 substrate — AIQ-VeriClave adds SoC-scale dogfood data, assertion/closure rewards, ensemble routing, and product packaging PRO-V-R1 never attempted.
- **vs generalist coders (Qwen3/DeepSeek/Kimi/GLM/MiniMax)**: best substrates, wrong objective — they become our generator pool, rated by our rewards.
- **vs commercial (Certitude-class)**: beaten 36-to-2 on blind spots by open BugGen; AIQ-VeriClave is the open, learning, compounding counterpart — and the *only* one whose training data grows with every customer tapeout path it serves.

## 8. Roadmap gates (ship/no-ship)
PHASE 0 baselines → PHASE 1 benchmark pick → PHASE 2 system bands → PHASE 3 corpus → PHASE 4 SFT bands → PHASE 5 specialization → PHASE 6 GRPO only if gated → PHASE 7 release on held-out IPs.
Any gate miss stops GPU spend and returns to data/harness — the plan prices
discipline above velocity, because a verification product that overclaims is
worse than none.

*Confidence notes: component figures are from the cited primary sources;
UVM2/Laude-style vendor-adjacent claims are excluded until reproduced (see
AI_VERIFY_EXECUTION_PLAN.md WS7). Volume figures in §4 are projections pending
P0 measurement. No benchmark-contaminated data enters T0–T2 by construction.*

---

## 10. Developer-realism gaps — audit and closure (no duplication)

Audit verdict on the four raised gaps: two were absent, two partially present.
Only the missing pieces were added; existing sections are referenced, not repeated.

| # | Gap | Already present (referenced, not repeated) | Newly adopted (this section + code) |
|---|---|---|---|
| G1 | Native UVM + SystemVerilog constraints | Nothing (only UVM2-as-unverified-claim in execution plan WS7) | `uvm_gen.py`: deterministic agent/driver/monitor/item/scoreboard skeletons from a spec dict. Boundary (stated in module): constraint *solving* stays in VCS/Questa/Xcelium; we generate `rand` fields + `constraint` blocks for the solver |
| G2 | Commercial sim hooks (VCS/Questa/Xcelium/Vivado) | Nothing (flow was Verilator-only) | `sim_adapters.py`: `FailureEvent` model + 5 adapters (Verilator/VCS/Questa/Xcelium/Vivado-xsim) with tool auto-detect; one stream feeds Judge + sign-off ledger |
| G3 | Waveform comprehension (drift pinpoint) | BluesFL VCD slicing + VCDiag clustering (plan only) | `vcd_events.py`: VCD→chronological transitions + `drift_report()` → "signal X drifted at cycle N (expected A, got B)". FSDB users convert via `fsdb2vcd` first (proprietary format; no vendor lib vendored) |
| G4 | Formal sign-off bounding | GoGoTB stall detector (stops *loops*) | `formal_policy.py`: pre-run verdicts PROVE/BOUND/ABSTRACT/UNPROVABLE-AT-BUDGET with engine + depth k + abstraction + `signoff_line()` ledger strings. Conservative thresholds: a wrong PROVE wastes a night, a wrong ABSTRACT costs minutes |

Integration points (pointers, not copies): G1 feeds WS1/WS5 environment
construction; G2 feeds the Judge and `ai-close` sign-off; G3 feeds WS3
localization evidence (`ai-localize` reads slices, `vcd_events` writes the
sentence); G4 gates every formal property before SymbiYosys/JasperGold runs
and its verdict strings land directly in the ledger. Tests:
`test_adoption.py` (17 tests, fixture logs per vendor).

---

## 11. Adopted algorithm standards (integration layer — new facts only)

Already specified elsewhere and NOT repeated here: RouteMoA cost/latency
figures + k=3 (§2, `router.py`), the full reward equation (§5 PHASE 6), PRO-V
verifiable-reward doctrine + 2.7%→0.3% false-positive stats (C5, §6),
GoGoTB taxonomy + BoN n=5–8 loop (§1 C1, §3, `ai-close`). This section adds
only what was missing:

### 11.1 Architecture requirement: RoPE + long context (new)
Base models MUST use Rotary Position Embedding with ≥256K native context
(Qwen3-Coder-Next/30B and DeepSeek-class all qualify). Rationale, specific to
this product: a single `wb_*` IP plus its VCD slice plus trajectory history
exceeds 16K practice windows by an order of magnitude; models without RoPE
degrade on exactly the long SoC-block + waveform inputs the product lives on.
Re-check at every base-model refresh; disqualify otherwise-strong models that
lack it.

### 11.2 Canonical reward, executable (`rewards.py`, new code)
§5's equation now has one implementation: `compute_reward()` with weights
`kill 1.0 / proof 1.0 / coverage 0.5 / localization 0.5 / cost 0.2`
(initial values from published bands; calibrated at the GRPO gate, PHASE 6 conditional). Any SFT/GRPO run,
eval harness, or paper claim referencing "the reward" must import this module
— no divergent re-implementations.

### 11.3 GRPO configuration (new linkage)
Group size = BoN sample count (5–8): one sample set serves generation voting
*and* relative scoring — no separate rollout phase. No critic model;
`group_normalize()` implements advantage = (r − mean)/std. Temperature and
batch size set at the GRPO gate (PHASE 6, conditional — see §13/§14), not guessed here.

### 11.4 Router scorer specification (new detail)
Heuristic `router.py` scorer stands until PHASE 5; the learned replacement targets
the RouteMoA envelope: ~86M-parameter encoder, top-k with k=3, ranking
priority performance > output-cost > input-cost > latency, 97.9%-class top-3
hit rate before it may replace the heuristic. Below that bar, the heuristic
ships.

---

## 12. Token efficiency program (P0 implemented; pointers only)

Mechanisms live in code (`cache_policy.py`, `compact.py`, `TokenLedger`,
adaptive BoN/cascade in `router.py`); this section records the policy
decisions, not the implementations.

1. **Measure first**: `TokenLedger` (per-task/stage input/output/cached/USD)
   is the gate every lever reports to. Mock backends emit token shapes, so the
   loop is validated before live spend. Current mock baseline: ~2.3M in /
   ~0.4M out per 100 tasks at ~$1.28 (≈$0.013/task) — the number live runs
   must beat per §6 cost band, not the reverse.
2. **Adaptive BoN + cascade** (accepted assumption: easy tasks stay easy):
   n=3/5/8 by difficulty; round 1 cheapest-only, escalate on Judge fail;
   `max_cost_usd` ceiling (default `TASK_BUDGET_USD` = $0.50) never empties
   the shortlist (cheapest survives).
3. **Redacted-prefix caching only** (confidentiality decision): cacheable =
   system prompts, specs, FRM templates, fixed tool-defs — all pre-checked;
   VCD slices, sim logs, trajectories, RTL bodies go to the prompt tail and
   are never cached. Redaction fails closed. Rationale: provider-side caching
   discounts are real (−41–80% in agentic studies) but incompatible with
   RTL-confidential content.
4. **Tool-schema filtering per stage** (only reproducibly-positive lever,
   −21–57K tokens/turn in measured studies): each pipeline lane declares
   minimal tools (`cache_policy.stage_tools`).
5. **CliffCompaction rules** (`compact.py`): truncate/drop tool outputs only,
   never rephrase, never re-compact, compact at budget exhaustion (preserves
   KV-cache continuity); VCD slices were already tail-pinned (ai-localize).
6. **Stacking expectation**: caching × routing × early-termination ×
   compaction compound toward the ≤$0.50/task band with roughly an order of
magnitude of headroom — verified by measurement at phase gates, never
assumed.

---

## 9. Developing and operating this system with OpenCode

Full adoption doc: `OPENCODE_WORKFLOW.md` (this directory). In brief:
OpenCode trains no weights — it owns everything around the model (dataset
pipelines, training configs, eval harness runs, experiment debugging, CI
gates, releases) via the five project skills in `skills/` (`ai-verify-harness`,
`ai-mutate`, `ai-localize`, `ai-close`, `ai-ensemble`; install to
`~/.config/opencode/skills/` since this tree has no git worktree), per-agent
model mapping for cost control, and copy-paste session recipes for each
pipeline stage. The scaffold in this directory (`router.py`,
`eval_harness.py`) is what those sessions execute.

---

## 13. Adopted platform architecture (external review, adopted as-is)

Source: independent architecture review of this blueprint ("AI Model
Framework Recommendation" chat). Adopted verbatim where quoted; integration
notes mark where each item lives in code. Nothing here duplicates §§1–12 —
those sections hold the specifications, this one records the reframing.

### 13.1 Reframe: platform, not checkpoint
**AIQ-VeriClave = Verification AI Platform** with Generator / Judge / Router
models underneath — never "one trained verification model." Concretely:
Qwen3-Coder-Next is **Generator-01** (replaceable by any model that beats it
on SVA, testbenches, localization, or patches), not the product identity.
`P0_PROFILE["generators"]` in `p0.py` is the machine-readable form of this
decision: a one-line list, swappable without touching anything else.

### 13.2 Evidence-First AI Principle (constitutional)
> No AI-generated verification artifact is valid because a model claims it
> valid. It becomes valid only after passing deterministic verification and
> evidence checks. The LLM may propose evidence-producing actions; it must
> never manufacture the evidence. Where AI ends: at the proposal. Where
> engineering truth begins: at independently reproducible evidence.

Enforced by `policy.py` (16-item `DETERMINISTIC_OPS` allowlist, sign-off
guards) and recorded by `evidence.py` (hash-chained ledger, computed C4
audit completeness, named-human sign-off only).

### 13.3 LLM lanes A–F + small-model table (pointers)
Lanes (requirement decomposition, verification-plan gen, SVA gen with
compile→prove→accept/reject, failure explanation, ranked localization,
pipeline-gated repair proposals) and the small-model assignment table
(requirement/failure classification → small classifiers; router → 86M;
ranking → reranker; token/cost routing → deterministic) live as data in
`policy.py` (`LLM_LANES`, `SMALL_MODELS`). Rule: largest model only where
reasoning/generation genuinely requires it; everything else cheap.

### 13.4 BoN ablation discipline (adopted experiment)
n=8 is never assumed: `p0.run_ablation()` runs n=(1,3,5,8) on the same task
and reports closure/rounds/cost per width, so each step must earn its keep
against C1/C2/C3/cost before production widths are set. P0 production
default: n=3 (`P0_PROFILE["bon"]`).

### 13.5 GRPO is a hypothesis (roadmap revised accordingly)
PHASE 5 is **specialization** (router, localization model, reranker);
**PHASE 6 is a GRPO experiment gated on the question "what measured failure
remains after SFT that RL can plausibly fix?"** (candidate-selection failures:
yes; incomplete context, engine timeouts, wrong TB/FRM, ambiguous
requirements: no); **PHASE 7 is productization**. `rewards.py` and §11.3 now
point at the PHASE 6 conditional gate instead of any training obligation.

### 13.6 Evaluation and benchmark discipline (adopted constraints)
Publish per-metric C1–C5, never a single "95%"; train/validation/held-out
split (P0-A RideProtect-RV v2.5 / P0-B MIPI CSI-2 / P0-C external) with
held-out designs excluded from training, prompts, thresholds, mutation
templates, and judge tuning; ablation ladder A (n=1 baseline) → F (+closure)
so each component's value is isolated; P0 dashboard fields fixed in
`p0.py:DASHBOARD_FIELDS` (tasks, candidates, syntax/sim/SVA/kill/localization
rates, closure, audit, FPR, $/task, CPU time, tokens/task).

---

## 14. CPU-first adoption (strategy artifact adopted; pointers only)

Source artifact (preserved verbatim):
`AIQ-VeriClave_CPU_First_Open_Source_Open_Cloud_Strategy_ChatGTP.md` (this
directory). What it changes vs §§1–13: the *default compute assumption*
(CPU/local first, GPU only when proven necessary), the *phase numbering*
(PHASE 0–7, see §5), and the *model-selection process* (Stage A/B discovery on
own verification tasks, §5/PHASE 1). Everything else in that artifact
(deterministic lists, lanes, flywheel, sign-off doctrine) was already this
blueprint's §§1–13 and is referenced, not repeated.

### 14.1 Standing principle
AIQ-VeriClave keeps functioning with zero GPU. GPU/SFT/GRPO figures anywhere
in this repo are **Optional Future Accelerated Compute** unless a phase gate
promotes them.

### 14.2 Canonical P0 stack (replaceable per row)
| Function | Technology | Status here |
|---|---|---|
| Programming / orchestration | Python | in use |
| Local LLM runtime / format | llama.cpp / GGUF (HF repos) | `P0_PROFILE["inference"]`; swap model without redesign |
| API / UI | FastAPI / Streamlit | Phase-gated (adopt on first service need) |
| RTL sim / synth / formal | Verilator / Yosys / SymbiYosys | in use (WS0) |
| Testbench / reference | Python / cocotb / Python FRM | in use |
| Mutation engine | Python (BugGen-style, WS2) | planned |
| Dataset / tracking | JSONL-Parquet / JSON-SQLite ledger | `evidence.py` implements the ledger half |
| Evidence storage | SQLite + immutable JSON artifacts | `evidence.py` |
| Containers / CI / VCS | Docker / GitHub Actions-local CI / Git | CI-gated at WS0 |

### 14.3 Compute adapter (`compute.py`)
One interface, three backends (`local-cpu` default, `free-cloud`, optional
`accelerated-external`): `vericlave run benchmark.json` executes the same
suite anywhere. Remote backends receive only policy-permitted (redacted)
prompts — privacy rule from §16 of the source artifact, enforced by
`cache_policy.py`, not by convention.

### 14.4 Cost metric (extends §6/T-ledger)
Per verified task: CPU seconds + peak-RAM note + LLM tokens + inference time
+ verification CPU + candidates + closure iterations + cloud usage; electricity
estimated from wall-time × platform factor (documented assumption, never
presented as metered). `eval_harness.evaluate()` already reports
`avg_cpu_time_s`, `avg_cost_per_task_usd`, and the full `tokens` section.

### 14.5 Privacy posture (pointer)
Local-first RTL handling per source §16 = the redaction/never-cache rules in
`cache_policy.py` plus local `llama.cpp` inference default. No new rules here.
