# AIQ-VeriClave — Architecture Diagram Alignment & Freeze Recommendations

## Purpose

This document captures the alignment review of the existing `DIAGRAMS.md` diagrams against the latest AIQ-VeriClave strategy and identifies which diagrams are aligned, which require correction, and which should be treated as background/reference material rather than authoritative architecture.

The central architectural principle is:

> **AIQ-VeriClave is a verification system first and a model second.**

Deterministic verification engines are the source of truth. Open-source LLMs provide generation, reasoning, localization, ranking, repair proposals, and related intelligence.

---

# 1. Overall Assessment

The existing diagrams are **broadly aligned with the latest AIQ-VeriClave plan**, particularly the diagrams covering deterministic verification, multi-stage verification, evidence generation, iterative closure, verification flywheel, model bake-off, CPU-first execution, compute abstraction, conditional training, and the three-layer architecture.

A cleanup pass is required before treating the diagram set as frozen.

The most important corrections are:

1. Do not hard-code Qwen3-Coder-Next as the permanent P0 model.
2. Run a model bake-off before selecting the baseline model.
3. Keep the architecture model-agnostic.
4. Move GPU-centric training architecture into optional/future reference material.
5. Use one selected generator in the initial P0 rather than multiple generators.
6. Introduce multiple generators/diversity only after the baseline system is established.
7. Treat CPU-first as CPU-first, not CPU-only.
8. Keep GRPO conditional rather than mandatory.
9. Keep deterministic verification as the truth layer.
10. Make the evidence ledger and auditability first-class architectural components.
11. Use a compute adapter so local CPU, open/free cloud compute, and optional accelerators do not affect the core architecture.

---

# Feedback Integration — Required Changes

The feedback strengthens the existing CPU-first, evidence-first, model-agnostic strategy without changing its core architecture.

## 1. Quantitative P0 Success Gates

The P0 benchmark must make success measurable from the beginning.

| Metric | Target / Gate |
|---|---:|
| Mutant kill rate | >=95% |
| SVA FPV-proven | >=95% |
| True bug in Top-3 | >=95% |
| Auditability / ledger completeness | 100% |
| Golden-vs-golden false-positive rate | <1% |
| Average verified task cost | <=$0.50 target |

Additional P0 measurements:

- Syntax-valid artifact rate
- Functional simulation / FRM pass rate
- Closure success rate
- First-pass success rate
- Average / median / maximum closure iterations
- Engineer review time per verified and accepted task
- Human rejection and override rates
- Latency
- Token usage
- CPU/RAM usage
- Total task cost

These are system-level targets after verification and closure, not a requirement that the first model achieve every target in one generation.

## 2. Closure Success as a First-Class Metric

Use:

```text
Closure Success Rate =
Tasks reaching accepted status within the permitted closure budget
÷
Tasks requiring closure
```

Also record:

```text
First-Pass Success Rate
Average Closure Iterations
Median Closure Iterations
Maximum Closure Iterations
```

This makes it possible to determine whether iterative regeneration actually improves verification outcomes.

## 3. Human-in-the-Loop Efficiency

Human sign-off remains the final authority, but the system should minimize manual inspection.

Measure:

```text
Engineer Review Time / Verified Task
Engineer Review Time / Accepted Task
Human Rejection Rate
Human Override Rate
Evidence Items Reviewed / Task
Dashboard Interaction Time
```

The dashboard should be explicitly evaluated in early prototypes for **exception-only review effectiveness**: whether engineers can focus primarily on unresolved failures, conflicting or missing evidence, and sign-off rather than manually inspecting every generated artifact.

The dashboard should surface:

- verification status,
- failed checks,
- relevant logs,
- proof results,
- mutation results,
- traceability,
- candidate comparison,
- closure history,
- artifact hashes,
- Judge rationale.

The system should automate evidence collection, result aggregation, failure classification, candidate comparison, traceability, and closure history. The human should primarily review exceptions and perform final sign-off.

## 4. Portability and Reproducibility

The same benchmark should be runnable through the compute adapter across:

```text
Local CPU
     ↓
Open / Free Cloud Compute
     ↓
Optional Accelerated Environment
```

Record:

```text
Environment
OS
CPU / Accelerator
RAM
Model
Model Quantization
Runtime Version
Tool Versions
Dataset Version
Benchmark Version
Random Seed
Token Settings
Verification Configuration
Artifact Hashes
```

The P0 objective is to establish the reproducibility envelope empirically. Exact bit-for-bit identity should not automatically be required across different runtimes.

Reproducibility should be evaluated by metric category: deterministic metadata/configuration should match exactly where expected; functional and formal outcomes should remain equivalent; mutation/coverage and timing/resource metrics should use predefined engineering tolerances; model-generated artifacts should be evaluated for semantic/evaluation equivalence rather than byte identity. Numeric tolerance thresholds should be established and versioned from the P0 portability benchmark rather than assumed in advance.

## 5. Portability Test Matrix

| Environment | Purpose | Required Result |
|---|---|---|
| Local CPU | Primary reference | Baseline result |
| Open/Free Cloud CPU | Portability | Comparable result within defined tolerance |
| Optional accelerator | Performance comparison | Same functional/evidence outcome |
| Different local CPU class | Hardware sensitivity | Measure performance variance |

The deterministic verification layer should be tested independently from the LLM runtime wherever practical.

### Reproducibility Envelope by Metric Category

| Metric category | Expected comparison |
|---|---|
| Metadata / versions / configuration / hashes | Exact where deterministic |
| Functional correctness | Equivalent PASS/FAIL outcome |
| Formal verification | Equivalent proof/status outcome |
| Mutation / coverage | Within predefined engineering tolerance |
| Timing / resource utilization | Within predefined engineering tolerance |
| Model-generated artifacts | Semantic/evaluation equivalence, not byte identity |

Numeric engineering tolerances should be established empirically during the P0 portability benchmark and versioned as part of the benchmark specification.


## 6. Dataset Quality Controls

The verification flywheel should become:

```text
Verification Run
      ↓
Failure / Repair / Closure
      ↓
Deterministic Re-verification
      ↓
Evidence Validation
      ↓
Quality Filter
      ↓
Governed Training Dataset
```

Only appropriately verified and governed trajectories should enter future training datasets.

Recommended metadata includes:

```text
Task ID
RTL / Design Identifier
Specification Version
Requirement IDs
Generated Artifact
Verification Results
Failure Classification
Localization
Repair
Re-verification Result
Closure Iteration
Evidence References
Tool Versions
Model / Runtime
Acceptance Status
Human Sign-off
```

## 7. BoN Cost-Control Gate

Start with:

```text
BoN = 1
BoN = 3
BoN = 5
```

Expand only when measured verification improvement justifies additional CPU/token cost.

For each setting record:

```text
Verification Improvement
Mutation Kill Delta
Localization Delta
Proof Delta
Latency Delta
Token Delta
Cost Delta
```

Use **verification gain per additional compute/token cost** as the decision criterion.

## 8. Revised P0 Dashboard

### Verification Quality

```text
Syntax Validity
Functional Pass Rate
Mutation Kill Rate
Formal Proof Rate
Top-3 Localization
Coverage
False-Positive Rate
Closure Success Rate
```

### Efficiency

```text
First-Pass Success
Average Closure Iterations
Latency
Tokens
CPU/RAM
Task Cost
```

### Human Oversight

```text
Engineer Review Time
Human Rejection Rate
Human Override Rate
Evidence Items Reviewed
Sign-off Status
```

### Reproducibility / Portability

```text
Environment
Tool Versions
Model / Runtime
Benchmark Version
Dataset Version
Seed
Artifact Hashes
Cross-Environment Result Variance
```

## 9. Revised P0 Gate

The P0 gate should answer five questions:

### Gate A — Does the system work?

Measure syntax, simulation/FRM, formal, mutation, traceability, and evidence generation.

### Gate B — Does closure work?

Measure first-pass success, closure success, and closure iterations.

### Gate C — Is the system efficient?

Measure latency, tokens, CPU/RAM, and cost.

### Gate D — Is human review scalable?

Measure engineer time per verified/accepted task and evidence-review burden.

### Gate E — Is the result reproducible?

Run the same benchmark through the compute adapter and measure cross-environment variance.

A P0 gate miss should trigger diagnosis of the relevant layer rather than automatically escalating to a larger model or more expensive training.

---

# 2. Diagrams That Strongly Align With the Latest Plan

## D04 — Machine Verification Pipeline

This aligns strongly with the evidence-first approach.

```text
Candidate Verification Artifact
        ↓
Syntax / Compile
        ↓
Simulation / FRM
        ↓
Formal Verification
        ↓
Mutation Testing
        ↓
Coverage
        ↓
Traceability
        ↓
Evidence
```

This should remain an important architectural diagram because it makes the deterministic verification layer explicit.

---

## D05 — Multi-Agent Verification

The generator → verification/critic → simulation → judge → verified artifact/evidence flow is aligned with the system concept.

It should be understood as a later-stage architecture rather than a requirement that P0 immediately contain many independent agents.

---

## D06 — Verification Flywheel

This is strongly aligned.

```text
RTL + Specification
        ↓
Generate
        ↓
Verify
        ↓
Fail
        ↓
Localize
        ↓
Repair
        ↓
Re-verify
        ↓
Accepted
        ↓
Training Data
```

This represents the long-term proprietary-data flywheel.

---

## D07 — Evidence Chain

This is one of the most important diagrams.

```text
Artifact
   ↓
Tool Output
   ↓
Proof / Result
   ↓
Evidence Ledger
   ↓
Human Sign-off
```

The evidence ledger should remain central because AIQ-VeriClave is intended to provide auditable verification results rather than only AI-generated suggestions.

---

## D08 — Platform Framing

This framing is aligned:

```text
User Input
   ↓
AIQ-VeriClave System
   ↓
Router / Generator / Verifiers / Judge / Closure
   ↓
Evidence Ledger
   ↓
Human Sign-off
```

This is a good high-level product architecture.

---

## D09 — Redesigned System Architecture

This is strongly aligned:

```text
SPEC + RTL + Context
        ↓
Router / Planner
        ↓
Generator(s)
        ↓
Deterministic Verification
        ↓
Judge / Triage
        ↓
PASS / FAIL
        ↓
Targeted Regeneration
        ↓
Evidence Ledger
        ↓
Human Sign-off
```

### P0 refinement

For P0, `Generator A/B/C` should be simplified to:

```text
Selected Open-Source Generator
```

Multiple generators can be introduced later for diversity and ensemble experiments.

---

# 3. Diagrams That Align After Minor Corrections

## D11 — Minimal P0

The overall structure is correct:

```text
SPEC + RTL
   ↓
Deterministic Router
   ↓
One Selected Open-Source LLM
   ↓
BoN
   ↓
Deterministic Verification
   ↓
Judge
   ↓
PASS / FAIL
   ↓
Closure
   ↓
Evidence
```

### Required correction

Do not label the P0 generator permanently as `Qwen3-Coder-Next`.

Use:

```text
Selected Open-Source LLM
```

Qwen3-Coder-Next may remain an initial candidate for the model bake-off.

---

## D33 — CPU-First P0 Architecture

The architecture is aligned, but the model should not be hard-coded.

Replace:

```text
Qwen3-Coder-Next
```

with:

```text
Selected Open-Source LLM
```

The model selection should happen through the bake-off process.

---

## D41 — CPU-First Minimal Architecture

This is essentially the current P0 conceptual architecture and should be treated as one of the principal diagrams.

Recommended structure:

```text
SPEC + RTL
      ↓
Deterministic Router
      ↓
Selected Open-Source LLM
      ↓
BoN = Initial Experimental Width
      ↓
Deterministic Verification
      ↓
Evidence Ledger
      ↓
Judge
      ↓
PASS / FAIL
      ↓
Closure Loop
```

The exact BoN width should remain an experimental parameter rather than a permanently fixed architectural requirement.

---

# 4. Model Selection Must Happen Before Model Freeze

## D43 — Model Discovery / Bake-Off

This diagram is particularly important and should precede final model selection.

Recommended flow:

```text
Model A
Model B
Model C
Model D
   ↓
Same Verification Benchmark
   ↓
Functional Correctness
Verification Quality
Resource Usage
Latency
Token Usage
Cost
   ↓
Select Baseline Model
```

### Principle

The architecture should remain model-agnostic.

The current candidate list can include suitable open-source coding models, but the final baseline should be determined experimentally.

---

# 5. D03 — GPU-Centric Architecture

D03 is useful as a **reference architecture**, but it should not be presented as the AIQ-VeriClave P0 architecture.

It represents a conventional GPU training stack:

```text
Data
 ↓
Model
 ↓
Training
 ↓
CUDA
 ↓
FSDP / DeepSpeed
 ↓
vLLM
 ↓
Docker / Cloud GPU
```

### Recommended treatment

Label it:

> **Reference: Conventional GPU Training Stack — Not AIQ-VeriClave P0**

or move it into:

> **Optional Future Accelerated Compute**

AIQ-VeriClave should not depend architecturally on GPU cloud infrastructure.

---

# 6. D01 and D02 — Generic Background Diagrams

These diagrams are useful for explaining general AI/model-development concepts:

- D01 — generic AI project architecture
- D02 — generic AI verification model architecture

They should not be presented as the authoritative AIQ-VeriClave architecture.

Recommended classification:

> Background / Educational Reference

---

# 7. D10 — Model Hierarchy

The hierarchy concept is aligned:

```text
Large General Generator
        ↓
Medium Domain Generator
        ↓
Small Verification / Specialist Models
        ↓
Deterministic Tools
```

However, this should be presented as a target architecture, not a requirement for P0.

P0 should begin with the minimum useful model stack.

---

# 8. D12 — Deterministic Verification Layer

This is a core architectural diagram.

```text
                 ┌───────────────┐
                 │ Syntax / Lint │
                 └───────┬───────┘
                         ↓
                 ┌───────────────┐
                 │ Simulation    │
                 │ + Python FRM  │
                 └───────┬───────┘
                         ↓
                 ┌───────────────┐
                 │ Formal / SVA  │
                 └───────┬───────┘
                         ↓
                 ┌───────────────┐
                 │ Mutation      │
                 └───────┬───────┘
                         ↓
                 ┌───────────────┐
                 │ Coverage      │
                 └───────┬───────┘
                         ↓
                 ┌───────────────┐
                 │ Traceability  │
                 └───────┬───────┘
                         ↓
                 ┌───────────────┐
                 │ Evidence      │
                 └───────────────┘
```

This layer is the source of truth.

---

# 9. D13 — SVA Verification Flow

The SVA accept/reject flow aligns well:

```text
LLM-generated SVA
        ↓
Syntax Check
        ↓
Formal Verification
        ↓
PROVEN / FAILED / UNPROVABLE
        ↓
Evidence
```

The LLM should not be allowed to declare an assertion correct merely because it is syntactically valid.

---

# 10. D14 — Judge Architecture

The judge architecture aligns with the ensemble approach:

```text
Candidate Artifacts
        ↓
Majority / Self-Check
        ↓
Judge
        ↓
Accept / Reject
```

The judge is not the final source of truth. The deterministic verification layer must provide the underlying evidence.

---

# 11. D15 / D16 — Specialized Model Allocation

The specialized-model concept is useful for later phases:

- requirement extraction,
- bug classification,
- localization,
- ranking,
- routing.

However, this should not be treated as mandatory P0 infrastructure.

### Naming correction

If a diagram currently describes specialized-model allocation but is titled as a BoN experiment matrix, rename it to:

> **Potential Specialized-Model Allocation**

---

# 12. D17 — BoN Experiment Matrix

The initial:

```text
n = 1
n = 3
n = 5
```

experiment is appropriate.

Treat these as initial experimental settings, not final architecture.

Measure:

- functional correctness,
- mutation kill rate,
- formal proof rate,
- localization accuracy,
- latency,
- token consumption,
- verification cost.

Later experiments can evaluate wider settings such as `n = 3 / 5 / 8` if justified by measured results.

---

# 13. D18 — BoN Diversity Matrix

This aligns with the longer-term ensemble strategy.

The goal is not simply to generate more outputs.

The goal is to determine whether candidate diversity improves:

- mutant kill rate,
- proof rate,
- localization,
- coverage,
- closure efficiency.

Diversity should therefore be measured rather than assumed to be beneficial.

---

# 14. D19 — GRPO Reward Function

The proposed reward structure aligns with the blueprint:

```text
Reward =
    Mutant Kill
  + Assertion FPV
  + Localization Top-1
  + Coverage Delta
  - Cost
```

Canonical weighting:

```text
kill       = 1.0
proof      = 1.0
coverage   = 0.5
localize   = 0.5
cost       = 0.2
```

GRPO remains a later conditional optimization stage.

---

# 15. D20 — GRPO Loop

The GRPO loop is appropriate as a future learning architecture.

It should not be positioned as a mandatory P0 component.

Recommended sequencing:

```text
P0
↓
Frozen Model Evaluation
↓
Verified Trajectories
↓
SFT / LoRA (if justified)
↓
Specialization (if justified)
↓
GRPO Experiment (if justified)
```

---

# 16. D21 — What GRPO Cannot Fix

Training cannot compensate for:

- poor verification infrastructure,
- incorrect reference models,
- weak datasets,
- bad mutation operators,
- missing deterministic checks,
- inadequate evidence collection,
- weak benchmark design.

Therefore:

> **Improve the verification system and data before increasing training complexity.**

---

# 17. D23 / D24 — Data Flywheel and Data Moat

These diagrams align strongly with the long-term strategy.

Every customer-style verification run can potentially produce:

```text
Specification
+
RTL
+
Generated Verification Artifacts
+
Failures
+
Localization
+
Repairs
+
Reverification
+
Evidence
```

Only accepted and appropriately governed data should enter future training datasets.

This creates a proprietary verification-data flywheel.

---

# 18. D25 — Train / Validation / Held-Out

This is essential for credible evaluation.

The dataset should remain separated into:

```text
Training
Validation
Held-Out Test
Customer-Style / Unseen IP
```

The held-out design set is especially important for preventing leakage and overestimating >95% performance.

---

# 19. D26–D32 — Experimental Progression

These diagrams broadly align with the phased experimental strategy.

Recommended progression:

```text
Infrastructure
      ↓
Deterministic Verification
      ↓
Model Bake-Off
      ↓
Baseline Selection
      ↓
BoN
      ↓
Judge
      ↓
Closure
      ↓
Dataset Flywheel
      ↓
Training
      ↓
Optional Specialization / GRPO
      ↓
Productization
```

---

# 20. D34 — P0 Benchmark

This should remain a core diagram.

The benchmark must measure actual verification objectives rather than generic code-generation quality.

Key measures:

- functional correctness,
- mutant-kill rate,
- SVA formal proof rate,
- bug localization,
- traceability,
- false-positive rate,
- latency,
- token usage,
- verification cost.

---

# 21. D35 — P0 Dashboard

The dashboard should also measure **exception-only review effectiveness** during early prototypes: whether engineers can focus on unresolved exceptions and final sign-off rather than manually inspecting every generated artifact.

Recommended additional KPI:

```text
Exception-Only Review Rate
Manual Artifact Inspection Rate
Engineer Time / Accepted Task
Sign-off Time / Accepted Task
```

The dashboard should make it possible to see:

```text
Accuracy
Verification Success
Mutation Kill
Formal Proof
Localization
Coverage
False Positives
Latency
Tokens
Cost
Closure Iterations
```

---

# 22. D36 — Revised Roadmap

Recommended sequence:

```text
P0-A  Infrastructure + Deterministic Verification
  ↓
P0-B  Open-Model Bake-Off
  ↓
P0-C  Baseline Model Selection
  ↓
P0-D  BoN + Judge + Closure
  ↓
P0 Gate
  ↓
P1  Proprietary Verified Dataset
  ↓
P2  SFT / LoRA
  ↓
P3  Specialized Models
  ↓
P4  Conditional GRPO
  ↓
P5  Productization
```

The exact phase numbering can remain consistent with the existing blueprint where required; the key point is the sequencing.

---

# 23. D37–D39 — Three-Layer Architecture

These diagrams align very strongly with the latest strategy.

## Layer 1 — Learning

```text
SFT
Specialization
GRPO
Dataset Flywheel
```

## Layer 2 — Intelligence

```text
Generate
Reason
Localize
Repair
Rank
Decompose
Route
```

## Layer 3 — Truth / Verification

```text
Simulation
Formal
Mutation
FRM
Coverage
Traceability
Evidence Ledger
```

The third layer is the authoritative truth layer.

---

# 24. D42 — CPU-First Model Strategy

The concept aligns, with one important clarification:

> **CPU-first does not mean CPU-only.**

The system should be capable of running locally on CPU while keeping an abstraction for optional additional compute.

---

# 25. D44 — CPU Execution

Avoid representing this simply as:

```text
CPU → YES
GPU → NO
```

A better representation is:

```text
Primary:
Local CPU

Optional:
Open / Free Cloud Compute

Future:
External Accelerator / GPU
```

The architecture should not require any particular compute provider.

---

# 26. D45 — Training Compute Separation

Inference and training should be architecturally separated:

```text
Inference
    ↓
CPU-first local execution

Training
    ↓
Optional compute adapter
    ↓
Only activated when evidence justifies it
```

---

# 27. D46 — Software Stack

The stack should remain open-source and modular.

Candidate components include:

```text
Python
FastAPI
Verilator
Yosys
SymbiYosys
cocotb
Python FRM
Git
SQLite / JSONL / Parquet
Docker
CI
Streamlit
```

The exact tool should remain replaceable through adapters where practical.

---

# 28. D47 — llama.cpp Runtime

This aligns well with the CPU-first approach.

```text
AIQ-VeriClave
      ↓
LLM Runtime Adapter
      ↓
llama.cpp / compatible local runtime
      ↓
Selected Open Model
```

The model runtime should remain replaceable.

---

# 29. D48 — Model Strategy

The correct long-term model strategy is:

```text
Open Models
     ↓
Benchmark
     ↓
Compare
     ↓
Select
     ↓
Specialize if justified
     ↓
Train only when evidence supports it
```

Do not assume that the largest model is automatically the best model for AIQ-VeriClave.

---

# 30. D49 — Baseline Selection

D49 aligns strongly with the bake-off approach.

The selected baseline should be based on:

- verification quality,
- correctness,
- resource usage,
- latency,
- token efficiency,
- cost,
- reproducibility.

Not merely general benchmark scores.

---

# 31. D50 — Model Specialization

Potential specialist roles include:

```text
Requirement Extractor
SVA Generator
Bug Classifier
Bug Localizer
Repair Generator
Candidate Ranker
Router
```

These should only be separated into dedicated models when the measured workload justifies the additional complexity.

---

# 32. D51 — SVA Verification

The flow should be:

```text
Requirement
   ↓
SVA Candidate
   ↓
Syntax
   ↓
Formal Verification
   ↓
Proof Evidence
   ↓
Accept / Reject
```

---

# 33. D52 — Conditional GRPO

GRPO should be:

> **Conditional, evidence-driven, and not part of the initial P0 dependency.**

If P0/P1 demonstrate that model training can materially improve verification metrics, GRPO can be evaluated.

If not, compute should not be spent merely because GRPO is available.

---

# 34. D53 — Verification Flywheel

The long-term architecture remains:

```text
Customer / Internal IP
        ↓
Verification Task
        ↓
AI Generation
        ↓
Deterministic Verification
        ↓
Failure / Localization
        ↓
Repair
        ↓
Reverification
        ↓
Accepted Evidence
        ↓
Governed Training Data
```

---

# 35. D54 — Compute Adapter

This is a core architectural principle.

```text
                 AIQ-VeriClave
                       ↓
                 Compute Adapter
                /       |                      /        |                Local CPU   Open/Free   Optional
                    Cloud       Accelerator
```

The core verification system should not depend on one compute environment.

---

# 36. D55 — Privacy and IP

The architecture should explicitly protect customer RTL, simulation data, waveforms, and verification trajectories.

Important principle:

> Customer RTL/VCD/simulation logs/trajectories should not be treated as generic cached inference data.

The blueprint calls for redacted-prefix caching only, while sensitive RTL/VCD/simulation logs/trajectories should not be cached.

---

# 37. D56 — Cost Target

The `$0.50 average verified task` figure should remain a **target**, not an assumed achieved value.

Early prototypes should be expected to show variance while model selection, token budgets, benchmark composition, verification runtime, and closure behavior stabilize. Report measured task-cost distribution during P0 rather than treating `$0.50` as a fixed guaranteed cost.

Measure:

- CPU time,
- RAM,
- model inference time,
- tokens,
- verification runtime,
- closure iterations,
- cloud usage where applicable,
- total task cost.

---

# 38. D57 — No Training From Scratch

The initial approach should be:

```text
Existing Open Model
       ↓
Evaluation
       ↓
Verified Data
       ↓
Optional SFT / LoRA
       ↓
Optional Specialization
       ↓
Optional GRPO
```

Training a foundation model from scratch is not part of the initial plan.

---

# 39. D58 — Revised Roadmap

Preserve the principle:

> **Build the verification system first; train the model only when evidence shows training is necessary.**

---

# 40. D59 — Immediate Blueprint Change

Make model selection explicit.

Instead of:

```text
P0 → Qwen3-Coder-Next
```

use:

```text
P0 → Open-Model Bake-Off
       ↓
Selected Baseline
       ↓
Verification System
```

Qwen3-Coder-Next remains a candidate rather than an architectural dependency.

---

# 41. D60 — Recommended P0 Architecture

This should be one of the principal authoritative diagrams.

```text
SPEC + RTL + Context
          ↓
   Deterministic Router
          ↓
 Selected Open-Source LLM
          ↓
      BoN Experiment
          ↓
Deterministic Verification
          ↓
     Evidence Ledger
          ↓
        Judge
          ↓
      PASS / FAIL
       ↙       ↘
     PASS      FAIL
       ↓         ↓
Human Sign-off  Targeted Closure
                   ↓
              Re-generation
                   ↓
              Re-verification
```

**Closure boundary refinement:** The maximum automatic closure budget is **3 rounds**. After the third unsuccessful closure round, the system must hard-stop automatic regeneration and escalate to human review. No automatic fourth round is permitted. This hard boundary prevents runaway loops and uncontrolled compute/token consumption.

---

# 42. D61 — P0 Benchmark

The benchmark should evaluate the complete system rather than only the LLM.

| Metric | Target |
|---|---:|
| Mutant kill rate | >=95% |
| SVA FPV-proven | >=95% |
| True bug in Top-3 | >=95% |
| Auditability | 100% |
| Golden-vs-golden FPR | <1% |
| Average verified task cost | <=$0.50 target |

These are system-level targets after verification/closure, not merely single-shot model scores.

---

# 43. D62 — P0 Dashboard / Roadmap

Recommended dashboard sections:

```text
Verification Quality
--------------------
Mutation Kill
Formal Proof
Localization
Coverage
False Positives

System Efficiency
-----------------
Latency
Tokens
CPU/RAM
Verification Runtime
Closure Iterations
Cost

Evidence
--------
Traceability
Tool Results
Artifact Hashes
Reproducibility
Human Sign-off
```

---

# 44. D63 — Evidence-First AI

The system should not simply say:

> “The AI thinks this verification artifact is correct.”

Instead:

```text
AI Proposal
     ↓
Machine Verification
     ↓
Measured Result
     ↓
Evidence
     ↓
Auditable Decision
```

---

# 45. D64 — Final Recommendation

The architectural recommendation is:

> **AIQ-VeriClave should be built as a CPU-first, open-source, model-agnostic verification system whose deterministic verification layer is the source of truth.**

The LLM is an intelligence component within the system.

---

# 46. D65 — Final P0 Architecture

Recommended authoritative P0:

```text
                    AIQ-VeriClave P0

              SPEC + RTL + CONTEXT
                        │
                        ▼
               ROUTER / PLANNER
                        │
                        ▼
              MODEL BAKE-OFF
                        │
                        ▼
            SELECTED OPEN-SOURCE LLM
                        │
                        ▼
                 BoN / CANDIDATES
                        │
                        ▼
        ┌─────────────────────────────┐
        │ DETERMINISTIC TRUTH LAYER   │
        │                             │
        │ Syntax / Compile            │
        │ Simulation + Python FRM     │
        │ Formal / SVA                │
        │ Mutation                    │
        │ Coverage                    │
        │ Traceability                │
        └──────────────┬──────────────┘
                       │
                       ▼
                EVIDENCE LEDGER
                       │
                       ▼
                     JUDGE
                       │
                 ┌─────┴─────┐
                 │           │
               PASS         FAIL
                 │           │
                 ▼           ▼
          HUMAN SIGN-OFF   TARGETED
                           CLOSURE
                              │
                              ▼
                         RE-GENERATE
                              │
                              ▼
                         RE-VERIFY
```

---

# 47. Recommended Authoritative Diagram Set

For architecture discussions and future documentation, the most important diagrams should be treated as the authoritative set:

1. Overall AIQ-VeriClave architecture
2. Deterministic truth / verification layer
3. Model bake-off and baseline selection
4. CPU-first compute abstraction
5. Learning strategy and conditional training
6. Verification data flywheel
7. Evidence and auditability chain

The remaining diagrams can serve as supporting, experimental, educational, or future-architecture diagrams.

---

# 48. Final Architecture Principles

### Principle 1 — Verification First

Build deterministic verification infrastructure before investing heavily in model training.

### Principle 2 — Model Agnostic

Do not architect the product around one specific foundation model.

### Principle 3 — CPU First

The initial system should run locally on CPU wherever practical.

### Principle 4 — Open Source First

Prefer open-source models, runtimes, tools, and infrastructure.

### Principle 5 — Cloud Optional

Open/free cloud compute can accelerate experiments but must not become a hard dependency.

### Principle 6 — Deterministic Truth

Simulation, formal verification, mutation testing, FRM, coverage, and traceability provide authoritative evidence.

### Principle 7 — Evidence First

Every accepted result should have machine-generated evidence that can be audited.

### Principle 8 — Iterative Closure

Failures should feed targeted regeneration and re-verification, with bounded closure iterations.

### Principle 9 — Train Only When Justified

SFT, specialization, and GRPO should be introduced only when benchmark evidence demonstrates that they improve the system.

### Principle 10 — Measure Everything

Measure:

- verification quality,
- robustness,
- false positives,
- localization,
- coverage,
- latency,
- tokens,
- compute,
- cost,
- closure iterations,
- auditability.

---

## Additional Architecture Principles From the Feedback

### Human Review Efficiency

Human sign-off remains part of the workflow, but engineer time must be measured and progressively reduced through evidence aggregation, dashboards, automated checks, and exception-focused review.

### Reproducible Portability

The compute adapter must allow the same benchmark to run across supported environments while recording environment, model, runtime, tool, dataset, seed, and artifact metadata.

### Data Quality Before Data Volume

The verification flywheel should favor high-quality, deterministically verified and governed trajectories over simply accumulating large quantities of training data.

---

# 49. Bottom Line

The existing `DIAGRAMS.md` is **substantially aligned with the latest AIQ-VeriClave strategy**, but it should not yet be frozen unchanged.

The most important cleanup is to remove the implication that Qwen3-Coder-Next is permanently fixed as the P0 model.

The correct architecture is:

```text
Open Models
    ↓
Common Verification Benchmark
    ↓
Measured Bake-Off
    ↓
Selected Baseline
    ↓
AIQ-VeriClave Verification System
```

The final system remains:

```text
SPEC + RTL
      ↓
ROUTER / PLANNER
      ↓
SELECTED OPEN LLM
      ↓
BoN / GENERATION
      ↓
DETERMINISTIC VERIFICATION
      ↓
EVIDENCE LEDGER
      ↓
JUDGE
      ↓
PASS / FAIL
      ↓
BOUNDED CLOSURE
      ↓
HUMAN SIGN-OFF
```

with:

```text
Learning Layer
      +
Intelligence Layer
      +
Truth / Verification Layer
```

and:

```text
Local CPU
   ↕
Compute Adapter
   ↕
Open / Free Cloud
   ↕
Optional Accelerator
```

This is the architecture direction that matches the latest AIQ-VeriClave discussion and the CPU-first, open-source, model-agnostic strategy.

---

# Deep-Review Addendum: AMD Xilinx Vivado Cross-Verification

## Architectural Finding

The final review identified an important capability to explicitly include in AIQ-VeriClave:

> **EDA Cross-Verification Adapter Layer**, with AMD Xilinx Vivado as an important target-specific implementation and validation adapter.

This does **not** change the CPU-first, Linux-first, open-source-first architecture. Vivado should enrich the verification evidence for AMD/Xilinx FPGA-targeted designs while remaining outside the mandatory P0 core.

The governing principle remains:

> **AIQ-VeriClave AI models propose, reason, rank, localize, and repair; deterministic verification and EDA tools provide the truth and evidence.**

## Proposed Architecture

```text
SPEC + RTL + TESTBENCH
          |
          v
    AIQ-VeriClave
          |
    +-----+----------------+
    |                      |
    v                      v
Open Verification     AMD Vivado Adapter
    |                      |
 Verilator              Synthesis
 Yosys                  Implementation
 SymbiYosys             Timing
 cocotb                 Utilization
 Python FRM             DRC
 Mutation               XSim where applicable
    |                      |
    +----------+-----------+
               |
        Cross-Verification
               |
        Evidence Ledger
               |
          Judge/Triage
               |
         PASS / FAIL
               |
        Human Sign-off
```

## Vivado Artifacts as Evidence

Where the configured Vivado flow produces them, AIQ-VeriClave should be able to collect and normalize relevant artifacts such as:

| Artifact/result | Potential use |
|---|---|
| Synthesis reports | Synthesis status and structural evidence |
| Implementation reports | Implementation evidence |
| Timing reports | Timing-closure evidence |
| Utilization reports | LUT/FF/BRAM/DSP evidence |
| DRC reports | Design-rule evidence |
| Power reports | Optional power evidence |
| Vivado logs | Execution/failure diagnostics |
| Tcl scripts | Reproducibility/provenance |
| `.dcp` checkpoints | Synthesis/implementation state |
| `.xdc` constraints | Constraint/provenance evidence |
| Simulation scripts/artifacts | Simulation evidence |
| `.bit` bitstream | Final FPGA implementation artifact where appropriate |

The system should record what was actually produced rather than assuming every project generates every artifact.

## Structured Evidence

Vivado output should ultimately be converted into normalized, machine-readable evidence rather than being stored only as PDFs or raw logs.

Conceptually:

```json
{
  "tool": "AMD Vivado",
  "tool_version": "<recorded>",
  "target_device": "<recorded>",
  "rtl_commit": "<Git commit>",
  "run_id": "<unique ID>",
  "synthesis": "<PASS/FAIL>",
  "implementation": "<PASS/FAIL>",
  "timing": {
    "status": "<PASS/FAIL>",
    "worst_slack_ns": "<recorded>"
  },
  "utilization": {
    "lut_percent": "<recorded>",
    "ff_percent": "<recorded>",
    "bram_percent": "<recorded>",
    "dsp_percent": "<recorded>"
  },
  "drc": "<PASS/FAIL>",
  "artifacts": [],
  "evidence_hash": "<hash>"
}
```

This is an architectural example, not a claim that this schema is already implemented.

## Vendor-Neutral Adapter Contract

The core should use a common adapter abstraction, conceptually:

```text
EDA Adapter
    |
    +-- prepare()
    +-- execute()
    +-- collect_artifacts()
    +-- parse_results()
    +-- normalize_evidence()
    +-- calculate_hashes()
    +-- report_status()
```

The exact API can be finalized during implementation.

This permits future adapters such as:

- AMD Vivado / XSim
- Siemens Questa
- Synopsys VCS
- Cadence Xcelium

without embedding vendor-specific logic into the AI layer.

## P0 Versus Optional Integration

### Canonical P0

- Linux 64-bit
- CPU-first execution
- Open-source verification stack
- Model-agnostic inference
- Deterministic verification
- Evidence Ledger
- Reproducible benchmark harness

### Optional/target-specific validation

- AMD Vivado
- Vivado XSim
- Other commercial EDA tools

AIQ-VeriClave should remain useful without a commercial EDA license. For an AMD/Xilinx FPGA target, Vivado can provide an additional validation path.

## Linux Relationship

The platform statement should be:

> **Linux is the canonical AIQ-VeriClave platform; Vivado is a target-specific EDA adapter that may execute within the Linux reference environment when the required AMD/Xilinx installation and licensing are available.**

Therefore:

- Linux = canonical operating environment
- CPU = primary compute mode
- Open-source tools = default verification foundation
- Vivado = optional target-specific EDA integration
- Open/free cloud Linux = portability target
- GPU/accelerator = optional future compute
- Windows = non-canonical development/access environment if needed

Actual supported Vivado versions should be specified only after integration testing.

## Provenance and Auditability

Every EDA run should record, where available:

- RTL Git commit/hash
- specification version
- testbench version
- constraint version
- target FPGA/device
- tool and version
- operating environment
- adapter version
- invocation/Tcl configuration
- run ID and timestamp
- configuration parameters
- artifact hashes
- PASS/FAIL status
- warnings/errors
- report references
- Evidence Ledger reference

This is essential because EDA results can depend on tool versions, constraints, device targets, settings, and environment.

## Important Limitation: Cross-Tool Agreement Is Not Proof

Multiple tools do not automatically establish correctness.

For example:

```text
RTL
 |----> Verilator
 |----> Yosys
 |----> Vivado
```

can provide valuable tool diversity, but all flows can still inherit an incorrect specification, inadequate stimulus, or the same RTL defect.

Therefore, cross-verification remains supporting evidence and does not replace:

- requirement-ID traceability
- functional reference-model comparison
- assertions/formal properties
- mutation testing
- coverage
- human review where required
- evidence completeness

## Evidence-Ledger States

External-tool execution should explicitly distinguish:

```text
EXECUTED
NOT_EXECUTED
PASS
FAIL
UNPROVEN
UNAVAILABLE
SKIPPED_BY_POLICY
```

In particular:

> **NOT_EXECUTED must never silently become PASS.**

This directly reinforces the existing zero-silently-dropped-gaps requirement.

Example:

```text
Vivado unavailable
       |
       v
Open verification continues
       |
       v
Evidence Ledger:
"Vivado cross-verification NOT_EXECUTED"
       |
       v
No silent PASS
```

## Commercial EDA Risk

Commercial EDA adapters introduce constraints that do not apply equally to open-source tools:

- licensing
- floating-license availability
- installation complexity
- version restrictions
- CI execution constraints
- cloud execution constraints
- redistribution limitations
- customer confidentiality
- artifact-sharing restrictions

Therefore, commercial EDA must not become a hidden dependency of the CPU-first/open-source P0 architecture.

## Recommended Roadmap Position

### P0-A — Core verification

Linux + Python + Git + Verilator + Yosys + SymbiYosys + cocotb + Python FRM + mutation + Evidence Ledger.

### P0-B — Model bake-off

Compare several open-source local models on the same benchmark using correctness, verification quality, latency, tokens, CPU/RAM and cost.

### P0-C — AI verification loop

Generation → deterministic verification → evidence → Judge → closure → human sign-off.

### P1 — Vivado adapter prototype

Use a controlled AMD/Xilinx FPGA benchmark to measure:

- adapter reliability
- run reproducibility
- report parsing
- artifact collection
- evidence normalization
- execution overhead
- tool-version sensitivity

### P1/P2 — Broader EDA integration

Consider additional commercial adapters according to customer demand and measured technical value.

## New Adapter Metrics

Add:

### Adapter reliability
Percentage of runs where the adapter starts, completes, collects expected artifacts, and parses them successfully.

### Reproducibility
Equivalent normalized evidence from repeated runs with the same RTL, constraints, tool version, target, and configuration, within defined tolerances.

### Evidence completeness
Percentage of expected evidence fields successfully captured.

### Cross-tool disagreement
Cases such as:

```text
Open-source flow = PASS
Vivado flow      = FAIL
```

or the reverse.

These should trigger diagnosis, not an automatic assumption that either tool is correct.

## Three-Layer Architecture Update

The existing architecture remains:

```text
+------------------------------------------------------+
| LEARNING LAYER                                       |
| SFT / LoRA / specialization / conditional GRPO      |
+------------------------------------------------------+
| INTELLIGENCE LAYER                                   |
| Generate / reason / localize / repair / rank / plan |
+------------------------------------------------------+
| TRUTH & VERIFICATION LAYER                           |
| Verilator / Yosys / SymbiYosys / FRM / mutation     |
| coverage / traceability / Evidence Ledger            |
|                                                      |
| Optional EDA adapters:                               |
| AMD Vivado / XSim / Questa / VCS / Xcelium           |
+------------------------------------------------------+
```

EDA adapters belong in the **Truth & Verification Layer**, not the Intelligence or Learning Layer.

## Final Freeze Checklist Addition

Before freezing the architecture document, explicitly represent:

1. Linux 64-bit as the canonical P0 platform.
2. CPU-first, not CPU-only.
3. Open-source verification as the P0 foundation.
4. Model-agnostic local inference.
5. A vendor-neutral EDA Cross-Verification Adapter Layer.
6. AMD Vivado/XSim as an optional target-specific adapter.
7. Normalized machine-readable EDA evidence.
8. Tool/version/configuration provenance.
9. Explicit NOT_EXECUTED and UNPROVEN states.
10. Commercial EDA licensing and availability boundaries.
11. Cross-tool disagreement analysis.
12. Adapter reliability and reproducibility metrics.
13. No assumption that multiple tools automatically constitute independent proof.
14. No commercial EDA dependency in P0.
15. Separation of customer/project FPGA evidence from generic benchmark evidence.

## Overall Finding

The Vivado concept is a strong architectural enhancement when positioned correctly:

> **AIQ-VeriClave should provide a vendor-neutral EDA Cross-Verification Adapter Layer. AMD Vivado is an important target-specific adapter, especially for AMD/Xilinx FPGA designs. It can enrich the Evidence Ledger with synthesis, implementation, timing, utilization, DRC, simulation, and related artifacts where available, while remaining optional and outside the CPU-first/open-source P0 core.**

This preserves the central architecture:

```text
AI / LLM
   |
   | proposes / reasons / repairs
   v
Deterministic Verification
   |
   | establishes evidence
   v
EDA Cross-Verification
   |
   | target-specific evidence
   v
Evidence Ledger
   |
   v
Human Sign-off
```
