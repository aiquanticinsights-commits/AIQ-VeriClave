# AIQ-VeriClave — Adopted Architecture Diagrams

> All 39 block diagrams copied verbatim from the adopted architecture
> review (shared chat 'AI Model Framework Recommendation'). Source order
> preserved; titles added for navigation. Bodies are byte-identical to
> the source (only leading/trailing blank lines trimmed).

---

## A. General AI framework

### D01. General AI project architecture (data pipeline + model design) — BACKGROUND ONLY, not AIQ-VeriClave P0

```text
                    YOUR AI PROJECT
                          │
             ┌────────────┴────────────┐
             │                         │
        Data Pipeline              Model Design
             │                         │
      Hugging Face Datasets       PyTorch
             │                         │
       Cleaning / Tokenizing      Architecture
             │                         │
             └────────────┬────────────┘
                          │
                       Training
                          │
                 Transformers / Trainer
                          │
                    Evaluation
                          │
                ┌─────────┴─────────┐
                │                   │
             Fine-tune           Pretrain
                │                   │
                └─────────┬─────────┘
                          │
                       Model
                          │
                    Deployment
```

### D02. Fine-tune pipeline (foundation model to specialized model) — BACKGROUND ONLY, not AIQ-VeriClave P0

```text
Existing foundation model
        ↓
Your domain data
        ↓
Data cleaning
        ↓
Fine-tuning
        ↓
Evaluation
        ↓
Your specialized AI model
```

### D03. Full serious-model stack (Python to Docker) — REFERENCE ONLY: conventional GPU training stack, NOT AIQ-VeriClave P0

```text
Language
    ↓
Python

Core ML
    ↓
PyTorch

Model ecosystem
    ↓
Hugging Face Transformers

Datasets
    ↓
Hugging Face Datasets

Training
    ↓
Transformers Trainer
    ↓
or custom PyTorch training loop

Experiment tracking
    ↓
Weights & Biases / MLflow

GPU acceleration
    ↓
CUDA

Large-scale training
    ↓
FSDP / DeepSpeed

Inference
    ↓
vLLM / other inference engine

Deployment
    ↓
Docker + cloud GPU
```

---

## B. Verification-side understanding

### D04. Machine-verification pipeline (LLM proposal to sign-off)

```text
LLM generates something
        ↓
Independent verification
        ↓
Does it compile?
        ↓
Does simulation agree?
        ↓
Does formal verification prove it?
        ↓
Does it kill seeded mutants?
        ↓
Does it satisfy requirements?
        ↓
Only then accept it
```

### D05. Multi-agent verification engine (Spec, Router, A/B/C, Judge)

```text
                    Specification
                         │
                         ▼
                     Router
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Model A         Model B        Model C
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                Machine verification
                         │
                         ▼
                       Judge
                         │
              ┌──────────┴──────────┐
              │                     │
             PASS                  FAIL
              │                     │
              ▼                     ▼
          Artifact             Root-cause
                                 analysis
                                    │
                                    ▼
                              Regeneration
```

### D06. Verification flywheel (RTL to training dataset)

```text
Customer RTL
    ↓
Generated tests
    ↓
Detected bugs
    ↓
Bug localization
    ↓
Repair attempts
    ↓
Verification closure
    ↓
Machine-verified trajectory
    ↓
Training dataset
    ↓
Better future model
```

### D07. Evidence chain example (requirement to sign-off)

```text
Requirement R-017
       ↓
Assertion A-017
       ↓
Formal proof PASS
       ↓
Test T-017
       ↓
Mutation M-017 killed
       ↓
Coverage bin closed
       ↓
Evidence recorded
       ↓
SIGN-OFF
```

---

## C. Adopted architecture

### D08. Platform framing (models underneath AIQ-VeriClave)

```text
                    AIQ-VeriClave
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
     Generator          Judge            Router
        │                 │                 │
        └──────────┬──────┴─────────────────┘
                   │
             Verification
                Engines
                   │
     ┌─────────────┼──────────────┐
     │             │              │
 Simulation      Formal        Mutation
     │             │              │
     └─────────────┼──────────────┘
                   │
             Evidence Ledger
                   │
              Human Sign-off
```

### D09. Redesigned system architecture (router to human sign-off)

```text
                    ┌─────────────────────┐
                    │ SPEC + RTL + Context │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  ROUTER / PLANNER   │
                    │  What needs testing?│
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
          Generator A    Generator B    Generator C
           Qwen/etc.     Diversity LLM    Specialized
                │              │              │
                └──────────────┼──────────────┘
                               ▼
                    ┌─────────────────────┐
                    │ DETERMINISTIC       │
                    │ VERIFICATION LAYER  │
                    ├─────────────────────┤
                    │ Verilator/Yosys     │
                    │ Python FRM          │
                    │ SymbiYosys          │
                    │ Mutation testing    │
                    │ Traceability        │
                    └──────────┬──────────┘
                               ▼
                    ┌─────────────────────┐
                    │   JUDGE / TRIAGE    │
                    │ Evidence-based      │
                    │ decision             │
                    └──────────┬──────────┘
                               ▼
                     PASS ─────┴──── FAIL
                                      │
                                      ▼
                             Targeted regeneration
                             ≤ 3 closure rounds
                                      │
                                      ▼
                             Evidence / Ledger
                                      │
                                      ▼
                              Human Sign-off
```

### D10. Original concept stack (long-term research architecture)

```text
Qwen3-Coder-Next
+
DeepSeek
+
GLM
+
MiniMax
+
Kimi
+
BoN
+
Router
+
Judge
+
SFT
+
GRPO
+
machine verifiers
+
formal verification
+
mutation testing
+
verification flywheel
```

### D11. Minimal P0 system (single LLM, BoN=3, machine checks, Judge)

```text
             RTL + SPEC
                 │
                 ▼
        ┌─────────────────┐
        │ Simple Router   │
        │ deterministic   │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │ ONE primary LLM │
        │ Selected OSS LLM│
        └────────┬────────┘
                 │
          BoN = 3 initially
                 │
                 ▼
        ┌─────────────────┐
        │ Machine checks  │
        ├─────────────────┤
        │ syntax          │
        │ simulation      │
        │ assertions      │
        │ mutation        │
        └────────┬────────┘
                 │
                 ▼
             Evidence
                 │
                 ▼
              Judge
                 │
           ┌─────┴─────┐
           ▼           ▼
          PASS        FAIL
                       │
                       ▼
                 regeneration
```

---

## D. LLM lanes

### D12. Requirement decomposition example (lane A)

```text
"Vehicle must enter safe state within 10 cycles
after watchdog timeout."

              ↓

REQ-001
REQ-002
REQ-003
```

### D13. SVA accept/reject flow, compile to proof (lane C)

```text
LLM
 ↓
compile
 ↓
formal proof
 ↓
accept/reject
```

### D14. Failure context example for explanation (lane D)

```text
simulation failed
cycle = 173
signal = brake_enable
expected = 0
actual = 1
```

### D15. Bug ranking example (lane E)

```text
1. watchdog FSM
2. timeout counter
3. reset sequencing
4. clock-domain crossing
```

---

## E. BoN experiments

### D16. BoN experiment matrix header (candidates, localization, cost)

```text
Task                         Model

Requirement classification   small encoder
Requirement → ID mapping     small classifier
Failure classification      small classifier
Error categorization         small model
Router                       ~86M encoder
Bug localization             small model + evidence
Candidate ranking            small reranker
Token/cost routing           deterministic
```

### D17. BoN test widths n=1/3/5/8

```text
n = 1
n = 3
n = 5
```

### D18. BoN measurement targets (C1/C2/C3/cost/latency)

```text
Does additional generation actually improve:

C1 mutation kill?
C2 proof rate?
C3 localization?
cost/task?
latency?
```

---

## F. Training gates

### D19. GRPO reward components (planned; no rewards.py in tree as of P3 final gate — future-conditional per §15)

```text
mutant_kill
+ assertion_FPV
+ localization_Top1
+ coverage_delta
− cost
```

### D20. P1 hypothetical results shaping the GRPO decision

```text
Mutation kill = 91%
SVA proof = 94%
Top-3 localization = 93%
```

### D21. Failure causes GRPO cannot fix

```text
RTL context is incomplete
formal engine times out
testbench is wrong
reference model is wrong
requirements are ambiguous
```

### D22. P1 training flow (model-agnostic, readiness-gated — NOT Qwen-committed)

```text
Selected Baseline (post bake-off AND post readiness gate)
        ↓
verified AIQI trajectories
        ↓
LoRA/SFT (only if justified; P3-D NOT READY as of P3 final gate)
```

Prior wording hard-coded one specific model as the training source. Per the
architecture review (§1 correction 1, §48 principles 2 and 9) and the
measured P3-D NOT READY verdict, no model is pre-committed to training and
no training direction is authorized. LoRA/SFT remains conditional on a
future READY verdict plus a separate training authorization.

---

## G. Flywheel and data

### D23. Flywheel data loop (moat mechanics)

```text
RTL
 ↓
verification candidate
 ↓
machine verification
 ↓
failure
 ↓
localization
 ↓
repair
 ↓
closure
```

### D24. Moat assets (dataset plus trajectories plus ledger)

```text
AIQ proprietary verification dataset
+
failure trajectories
+
mutation corpus
+
RTL/requirement relationships
+
proof outcomes
+
repair trajectories
+
closure histories
+
evidence ledger
```

---

## H. Evaluation discipline

### D25. Train/validation/held-out split with leakage prohibitions

```text
                 DATA
                  │
       ┌──────────┼──────────┐
       ▼          ▼          ▼
   TRAINING     VALIDATION   HELD-OUT
     IP          IP          IP
```

### D26. Experiment A, baseline (1 RTL, 1 spec, 1 generator, n=1)

```text
1 RTL block
+
1 specification
+
1 generator
+
n=1
```

### D27. Experiment A metrics (syntax to cost)

```text
syntax pass
simulation pass
SVA proof
mutation kill
bug localization
cost
```

### D28. Experiment B (same RTL, BoN=3)

```text
same RTL
+
BoN=3
```

### D29. Experiment C (same RTL, BoN=5)

```text
same RTL
+
BoN=5
```

### D30. Experiment D (multiple generators)

```text
same RTL
+
multiple generators
```

### D31. Experiment E (plus Judge)

```text
multiple generators
+
Judge
```

### D32. Experiment F (plus closure loop)

```text
F + closure loop
```

---

## I. P0 system

### D33. P0 full architecture (closure rounds 1-3)

```text
                AIQ-VeriClave P0
                       │
        ┌──────────────┴──────────────┐
        │                             │
     Input                        Configuration
   SPEC + RTL                     YAML/JSON
        │
        ▼
                 Deterministic Router
                         │
                         ▼
                   Selected Open LLM
                         │
                       BoN=3
        │
        ▼
 ┌──────────────────────┐
 │ Verification Engine  │
 │                      │
 │ Verilator            │
 │ Yosys                │
 │ Python FRM           │
 │ SymbiYosys           │
 │ Mutation engine      │
 └──────────┬───────────┘
            │
            ▼
       Evidence Ledger
            │
            ▼
          Judge
            │
       ┌────┴────┐
       ▼         ▼
     PASS       FAIL
                  │
                  ▼
              Closure
              Round 1
                  │
                  ▼
              Round 2
                  │
                  ▼
              Round 3
```

### D34. P0 benchmark split (internal plus held-out)

```text
AIQI internal development set
            +
AIQI internal validation set
            +
external held-out benchmark
```

### D35. P0 dashboard metrics

```text
AIQ-VeriClave P0
─────────────────────────────
Tasks executed             100
Candidates generated       300
Syntax valid               XX%
Simulation valid            XX%
Assertions proven           XX%
Mutants detected            XX%
Mutation kill rate          XX%
Top-3 localization          XX%
Closure success             XX%
Audit completeness         100%
False positive rate         XX%
Average cost/task            $X
```

---

## J. Roadmap

### D36. Revised roadmap (P0/P1/P2/P3/P4 gates)

```text
P0 — SYSTEM PROOF
│
├── Harness
├── deterministic verification
├── frozen LLM
├── BoN
├── Judge
├── evidence ledger
└── baseline C1–C5
        │
        ▼
P0-GATE
"Does the system work?"
        │
        ▼
P1 — SFT
│
├── verified trajectories
├── LoRA/SFT
├── compare against frozen model
└── held-out evaluation
        │
        ▼
P1-GATE
"Does training improve it?"
        │
        ▼
P2 — SPECIALIZATION
│
├── router
├── localization model
├── reranker
└── specialized verification models
        │
        ▼
P2-GATE
"Does specialization improve cost/reliability?"
        │
        ▼
P3 — GRPO EXPERIMENT
│
└── only if a measurable bottleneck
    is suitable for RL
        │
        ▼
P4 — PRODUCTIZATION
```

---

## K. Three layers

### D37. Layer 1, truth layer (deterministic)

```text
Simulation
Formal
Mutation
Coverage
Reference model
Traceability
Evidence
```

### D38. Layer 2, intelligence layer (AI)

```text
Generation
Reasoning
Localization
Repair
Candidate ranking
Requirement decomposition
```

### D39. Layer 3, learning layer (only after evidence)

```text
SFT
Specialized models
Router
GRPO — conditional
Verification flywheel
```

---

## Appendix — illustrative code fragment (not a diagram)

### X1. SVA stub example (lane C: LLM proposes, machine disposes)

```systemverilog
property watchdog_safe_state;
   ...
endproperty
```

---

## Supplement: CPU-first strategy diagrams (D41-D67)

> Second source: `AIQ-VeriClave_CPU_First_Open_Source_Open_Cloud_Strategy_ChatGTP.md`
> (on-disk artifact). 28 blocks; 4 byte-identical duplicates of Section A–K
> already recorded above were skipped (diff-verified, none missing). Bodies
> below are byte-identical to the source (leading/trailing blanks trimmed).

---

## L. CPU-first system

### D41. Conceptual architecture (SPEC+RTL to closure loop)

```text
                 SPEC + RTL
                     |
                     v
              +--------------+
              | Simple Router|
              +------+-------+
                     |
                     v
              +--------------+
              | Local Open   |
              | LLM          |
              +------+-------+
                     |
                  BoN=1/3
                     |
                     v
       +---------------------------+
       | Deterministic Verification|
       |                           |
       | Verilator                 |
       | Yosys                     |
       | Python FRM                |
       | SymbiYosys                |
       | Mutation Engine           |
       +-------------+-------------+
                     |
                     v
              Evidence Ledger
                     |
                     v
                   Judge
                     |
              +------+------+
              |             |
             PASS           FAIL
                            |
                            v
                       Closure Loop
```

### D42. CPU-first philosophy (P0, engines, small LLMs, benchmarks)

```text
Local CPU
   |
   +----> P0 development
   |
   +----> verification engines
   |
   +----> small/quantized local LLMs
   |
   +----> benchmark and evaluation
```

### D43. Model discovery bake-off (same benchmark, compare)

```text
Small Open Model A
Small Open Model B
Small Open Model C
        |
        v
Same AIQ-VeriClave Benchmark
        |
        v
Compare actual verification performance
```

---

## M. Compute separation

### D44. Inference compute (CPU to YES)

```text
CPU --> YES
```

### D45. SFT/LoRA compute split (CPU possible, GPU useful)

```text
CPU --> technically possible for small models
GPU --> useful for larger/faster training
```

### D46. GRPO cost loop (generate to repeat)

```text
Candidate generation
        |
Simulation/Formal verification
        |
Reward calculation
        |
Training
        |
Repeat
```

---

## L. CPU-first system

### D47. llama.cpp local runtime (controller to pipeline)

```text
AIQ-VeriClave Controller
          |
          v
      llama.cpp
          |
          v
     Local GGUF
       Model
          |
          v
Verification Pipeline
```

---

## N. Model discovery and selection

### D48. Discovery set (Models A to D)

```text
Model A
Model B
Model C
Model D
```

### D49. Baseline selection criteria (five-way balance)

```text
Correctness
+
Verification quality
+
Resource requirements
+
Latency
+
Cost
```

---

## O. Requirements and SVA checks

### D50. Watchdog requirement decomposition example

```text
"Vehicle must enter safe state within
10 cycles after watchdog timeout."

              |
              v

REQ-001
REQ-002
REQ-003
```

### D51. SVA pipeline check (accept/reject)

```text
LLM
 |
 v
Compile
 |
 v
Formal Proof
 |
 +----> Accept
 |
 +----> Reject
```

---

## P. GRPO decision

### D52. P0 to GRPO decision tree (measure first)

```text
P0
 |
 v
Frozen model
 |
 v
Measure failures
 |
 v
SFT
 |
 v
Measure remaining failures
 |
 v
Is the remaining failure suitable for RL?
 |
 +---- NO ---> Do not use GRPO
 |
 +---- YES --> Small GRPO experiment
```

---

## Q. Flywheel and training strategy

### D53. Verification flywheel production chain

```text
RTL
 |
 v
Verification candidate
 |
 v
Machine verification
 |
 v
Failure
 |
 v
Localization
 |
 v
Repair
 |
 v
Closure
```

---

## R. Compute adapter and backends

### D54. Compute adapter (local, free, external)

```text
AIQ-VeriClave Compute Adapter

             |
       +-----+-----+
       |     |     |
       v     v     v
     Local  Free  Optional
      CPU   Cloud  External
```

### D55. Local CPU backend via llama.cpp

```text
Local CPU
    |
    v
llama.cpp
```

### D56. Open/free cloud backend

```text
Open/Free Cloud
    |
    v
Remote inference endpoint
```

### D57. Optional accelerated backend

```text
Optional accelerated environment
```

### D58. Sensitive-RTL local architecture

```text
Sensitive RTL
     |
     v
Local verification environment
     |
     +----> Local LLM
     |
     +----> Local deterministic tools
     |
     +----> Local evidence ledger
```

### D59. Cost-per-verified-task formula

```text
AIQ-VeriClave Cost / Verified Task
```

---

## Q. Flywheel and training strategy

### D60. Preferred training strategy (pretrained to conditional GRPO)

```text
Open pretrained model
        |
        v
P0 frozen-model evaluation
        |
        v
Collect verified trajectories
        |
        v
SFT / LoRA if justified
        |
        v
Evaluate against frozen baseline
        |
        v
Specialization if justified
        |
        v
GRPO only if justified
```

### D61. Anti-pattern (raw data to from-scratch training)

```text
Raw data
   |
   v
Train 7B/30B/80B from scratch
```

---

## S. Roadmap, P0 and dashboard

### D62. PHASE 0-7 revised roadmap

```text
PHASE 0 — CPU-FIRST P0
----------------------
- Open-source software
- Open model(s)
- No model training
- Local CPU
- Deterministic verification
- BoN
- Judge
- Evidence ledger
- C1–C5 baseline

             |
             v

PHASE 1 — MODEL BENCHMARK
-------------------------
- 1B/3B/7B-class open models
- CPU/local evaluation
- Verification benchmark
- Resource measurement
- Select baseline

             |
             v

PHASE 2 — VERIFICATION SYSTEM
-----------------------------
- Selected model
- BoN
- Judge
- Closure
- Evidence ledger
- C1–C5 evaluation

             |
             v

PHASE 3 — PROPRIETARY DATASET
-----------------------------
- Verified trajectories
- Mutations
- Failures
- Localizations
- Repairs
- Proof outcomes
- Closure histories

             |
             v

PHASE 4 — SFT / LoRA
--------------------
Only if P0 identifies a model-specific
performance limitation.

             |
             v

PHASE 5 — SPECIALIZED MODELS
----------------------------
- Router
- Classifier
- Reranker
- Localization model
- Other small models

             |
             v

PHASE 6 — GRPO EXPERIMENT
-------------------------
Only if a measurable remaining
failure is suitable for RL.

             |
             v

PHASE 7 — PRODUCTIZATION
------------------------
- Local deployment
- Optional open cloud
- Optional accelerated compute
- Enterprise verification workflow
```

### D63. P0 implementation (BoN=1/3, local LLM)

```text
                 AIQ-VeriClave P0
                        |
             +----------+----------+
             |                     |
          SPEC + RTL          Configuration
             |                 YAML / JSON
             |                     |
             +----------+----------+
                        |
                        v
                Deterministic Router
                        |
                        v
                  Local Open LLM
                    llama.cpp
                        |
                     BoN=1/3
                        |
                        v
          +---------------------------+
          | Deterministic Verification|
          |                           |
          | Verilator                 |
          | Yosys                     |
          | Python FRM                |
          | SymbiYosys                |
          | Mutation Engine           |
          +-------------+-------------+
                        |
                        v
                  Evidence Ledger
                        |
                        v
                      Judge
                        |
                   +----+----+
                   |         |
                  PASS       FAIL
                             |
                             v
                        Closure Loop
```

### D64. Objective dataset split (internal plus held-out)

```text
AIQ internal development set
          +
AIQ validation set
          +
External held-out benchmark
```

### D65. P0 dashboard metrics (with CPU/tokens/cost)

```text
AIQ-VeriClave P0
─────────────────────────────
Tasks executed             XXX
Candidates generated       XXX
Syntax valid               XX%
Simulation valid            XX%
Assertions proven           XX%
Mutants detected            XX%
Mutation kill rate          XX%
Top-3 localization          XX%
Closure success             XX%
Audit completeness         100%
False positive rate         XX%
Average CPU time/task       XX
Average tokens/task         XX
Average cost/task           $X
```

---

## T. Principles and decisions

### D66. AI/deterministic/evidence separation

```text
AI
 |
 +--> proposes
 +--> generates
 +--> reasons
 +--> localizes
 +--> repairs
 |
 v
Deterministic Verification
 |
 +--> tests
 +--> simulates
 +--> proves
 +--> mutates
 +--> measures
 |
 v
Evidence
 |
 v
Human Sign-off
```

### D67. Post-P0 decision ladder (model to GPU)

```text
Which model?
        |
        v
Which model size?
        |
        v
Does SFT help?
        |
        v
Do specialized models help?
        |
        v
Is GRPO justified?
        |
        v
Is GPU acceleration actually necessary?
```

---

## Appendix — command fragment (not a diagram)

### X2. Benchmark run command (`vericlave run benchmark.yaml`)

```bash
vericlave run benchmark.yaml
```

---

## Freeze amendment (2026-09-29, frozen architecture — document bodies above unchanged except noted)

Source: `Arch-Docs/AIQ-VeriClave_Architecture_Document_Fixed&FinalVersion1.0.md`
(frozen verbatim; this amendment only records diagram-set alignment, it does
not restate the architecture).

- D11/D33: generator relabeled `Selected Open/OSS LLM` (was Qwen). P0 names no
  foundation model; the P0-B bake-off (`gpt-oss-20b`, `deepseek-coder-6.7b`,
  `llama-3.1-8b` on LMStudio trio, same benchmark) freezes the baseline.
- D01/D02: background/educational reference. D03: conventional-GPU reference
  (optional future accelerated compute), never P0.
- Closure boundary: max 3 automatic rounds, then `escalated_to_human` (see
  `router.run_task()`); BoN starts 1/3/5, n=8 only as a measured extension.
- Evidence states: EXECUTED / NOT_EXECUTED / PASS / FAIL / UNPROVEN /
  UNAVAILABLE / SKIPPED_BY_POLICY (+ DISPOSITIONED); NOT_EXECUTED is never
  rewritten as PASS (see `evidence.EvidenceLedger`).
- Authoritative set: overall architecture (D08/D09), truth layer (D04/D12),
  bake-off + baseline (D43/D49), compute abstraction (D42/D54), conditional
  training (D15/D19–D21/D52), flywheel (D06/D23/D53), evidence chain (D07).
