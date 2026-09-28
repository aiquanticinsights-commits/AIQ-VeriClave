# AIQ-VeriClave — CPU-First, Open-Source and Open-Cloud Development Strategy

## 1. Executive Direction

AIQ-VeriClave should be developed as a **CPU-first, open-source-first, model-agnostic verification system**.

The development strategy is:

- No dependency on paid GPU cloud platforms.
- Prefer open-source models and open-source software.
- Use the user's local development machine as the primary P0 environment.
- Use free/open or limited open-cloud resources only where useful.
- Treat cloud/GPU acceleration as an optional optimization rather than an architectural dependency.
- Build the verification system before committing to expensive model training.

The central principle is:

> **AIQ-VeriClave should continue functioning even when GPU resources are unavailable.**

---

# 2. Architectural Principle

AIQ-VeriClave should not initially be treated as a single trained AI model.

It should be treated as a **verification system in which AI models are replaceable components**.

The conceptual architecture is:

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

The LLM proposes verification artifacts and reasoning. Deterministic tools produce the engineering evidence.

---

# 3. Why CPU-First Makes Sense

A large portion of AIQ-VeriClave's verification workload is naturally CPU-oriented:

- RTL simulation
- Verilator
- Yosys
- formal verification
- Python reference models
- mutation analysis
- trace analysis
- coverage analysis
- requirement mapping
- evidence generation
- SQLite/database operations
- Git and CI

GPU acceleration is primarily relevant to:

- LLM inference for larger models
- SFT/LoRA training
- reinforcement learning such as GRPO

Therefore the system should not be designed around GPU availability.

The preferred philosophy is:

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

---

# 4. Do Not Start with an 80B Model

The AIQ-VeriClave blueprint identifies Qwen3-Coder-Next as the primary generator candidate, specified as 80B total / 3B active parameters with 256K context.

However, this should not automatically mean that Qwen3-Coder-Next is the first model deployed.

Instead:

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

The model should be selected based on **AIQ-VeriClave's own verification tasks**, not only general coding benchmarks.

The initial question should be:

> Which open model provides the best verification performance under the project's CPU, memory, latency and accuracy constraints?

Qwen3-Coder-Next remains a candidate, not an architectural dependency.

---

# 5. Separate Model Inference from Model Training

There are three different compute problems.

## 5.1 Inference

Running an existing model.

```text
CPU --> YES
```

Small or quantized models can be run locally.

## 5.2 SFT / LoRA

Updating a pretrained model.

```text
CPU --> technically possible for small models
GPU --> useful for larger/faster training
```

This should not be part of P0.

## 5.3 GRPO

GRPO involves repeated candidate generation, verification, reward calculation and training.

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

This can become computationally expensive.

Therefore GRPO should be treated as a later experimental option, not a mandatory early component.

---

# 6. Recommended Open-Source Software Stack

The initial P0 stack can be based on:

| Function | Proposed Technology |
|---|---|
| Programming | Python |
| Local LLM runtime | llama.cpp |
| Model format | GGUF |
| Model source | Hugging Face / open model repositories |
| Orchestration | Python |
| API | FastAPI |
| RTL simulation | Verilator |
| RTL synthesis/checking | Yosys |
| Formal verification | SymbiYosys |
| Testbench | Python / cocotb |
| Reference model | Python |
| Mutation engine | Python |
| Dataset | JSONL / Parquet |
| Initial experiment tracking | JSON / SQLite |
| Containers | Docker |
| Version control | Git |
| CI | GitHub Actions / local CI |
| Evidence storage | SQLite + immutable JSON artifacts |
| Initial UI | Streamlit |

This stack should remain replaceable where practical.

---

# 7. Local LLM Runtime

A local runtime such as `llama.cpp` is highly relevant to the CPU-first strategy.

The intended architecture is:

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

Advantages of this architecture include:

- Local inference.
- Quantized model support.
- No mandatory commercial API.
- No requirement to send RTL/IP to an external AI provider.
- Ability to expose a local model through an API interface.
- Ability to change the underlying model without redesigning the verification system.

---

# 8. Model Strategy

The recommended model strategy is:

## Stage A — Model Discovery

Evaluate multiple open models.

```text
Model A
Model B
Model C
Model D
```

Measure:

- Verilog/SystemVerilog generation
- SVA generation
- test generation
- requirement decomposition
- bug localization
- repair proposals
- syntax validity
- functional correctness
- verification success
- CPU time
- memory usage
- token consumption

## Stage B — Select the Baseline

Select the model that provides the best practical balance of:

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

## Stage C — Specialization

Only after P0 data demonstrates a need should the project consider:

- LoRA/SFT
- specialized models
- router training
- reranker training
- localization models

---

# 9. Use Different Model Sizes for Different Tasks

A future AIQ-VeriClave architecture does not need to use one large model for everything.

A possible specialization is:

| Task | Potential Model Type |
|---|---|
| Requirement extraction | Small model |
| Requirement classification | Small encoder |
| Requirement-to-ID mapping | Small classifier |
| SVA generation | Medium coding model |
| Test generation | Medium coding model |
| Bug classification | Small model |
| Bug localization | Small/medium model |
| Candidate ranking | Small reranker |
| Routing | Small encoder |
| Evidence verification | Deterministic |
| Simulation | Deterministic |
| Formal verification | Deterministic |
| Mutation measurement | Deterministic |

This could substantially reduce infrastructure requirements.

---

# 10. What Must Remain Deterministic

The following should remain deterministic wherever practical:

- Verilog/SystemVerilog syntax validation
- Compilation
- RTL simulation
- Reference-model comparison
- Assertion execution
- Formal proof
- Mutation generation
- Mutation-kill measurement
- Coverage measurement
- Requirement-ID traceability
- Evidence recording
- Reproducibility
- Pass/fail thresholds
- Security/privacy rules
- Artifact hashes
- Version tracking

The core principle is:

> **The LLM may propose evidence-producing actions. It should not manufacture the evidence.**

An AI-generated assertion is not valid because the LLM says it is correct.

It becomes accepted only after the appropriate machine verification succeeds.

---

# 11. Where the LLM Should Be Used

LLMs are appropriate for tasks such as:

## Requirement Decomposition

Convert natural-language specifications into structured requirements.

```text
"Vehicle must enter safe state within
10 cycles after watchdog timeout."

              |
              v

REQ-001
REQ-002
REQ-003
```

## Verification-Plan Generation

Generate:

- scenarios
- assertions
- directed tests
- constrained-random ideas
- coverage objectives
- corner cases

## SVA Generation

The LLM proposes SVA.

```systemverilog
property watchdog_safe_state;
   ...
endproperty
```

Then the deterministic verification pipeline checks:

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

## Failure Explanation

The LLM can interpret structured failure information such as:

```text
simulation failed
cycle = 173
signal = brake_enable
expected = 0
actual = 1
```

and propose likely causes.

## Bug Localization

The LLM can rank possible sources:

```text
1. watchdog FSM
2. timeout counter
3. reset sequencing
4. clock-domain crossing
```

The ranking should be supported by machine-generated evidence.

## Repair Proposals

The LLM can propose RTL or verification changes.

Every proposed repair must return through the verification pipeline.

---

# 12. BoN Strategy

The blueprint proposes BoN with approximately 5–8 candidates.

For CPU-first P0, start smaller.

Recommended experiment:

```text
n = 1
n = 3
n = 5
```

Measure:

- mutation kill rate
- proof rate
- localization performance
- closure success
- latency
- CPU time
- token consumption
- cost/task

If `n=3` produces nearly all of the improvement obtained by `n=8`, there is no reason to use eight candidates.

BoN should therefore be an experimentally measured parameter rather than a fixed assumption.

---

# 13. GRPO Should Be Conditional

GRPO should not automatically become part of AIQ-VeriClave simply because it appears in the long-term blueprint.

The correct question is:

> What measurable failure remains after the frozen baseline and SFT, and is that failure suitable for reinforcement learning?

For example:

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

Potential causes of failure may instead be:

- incomplete RTL context
- incorrect reference model
- formal timeout
- incorrect testbench
- ambiguous requirement
- insufficient mutation quality
- poor candidate selection

GRPO should not be used to solve a problem that is actually caused by one of these system-level issues.

---

# 14. Verification Flywheel

The verification flywheel remains one of the most important long-term components.

The system can produce:

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

The resulting trajectories can become training data.

Potential proprietary data includes:

- requirements
- RTL relationships
- verification plans
- generated assertions
- generated tests
- mutation data
- failures
- bug localizations
- repairs
- proof outcomes
- closure histories
- evidence records

The long-term competitive asset may therefore be the **AIQ proprietary verification dataset and trajectory history**, rather than the base open model itself.

---

# 15. Open Cloud Strategy

The cloud should be treated as an **optional accelerator**, not a dependency.

Use an abstraction such as:

```text
AIQ-VeriClave Compute Adapter

             |
       +-----+-----+
       |     |     |
       v     v     v
     Local  Free  Optional
      CPU   Cloud  External
```

The same experiment should be runnable in different environments.

For example:

```bash
vericlave run benchmark.yaml
```

The benchmark should not care whether inference is:

```text
Local CPU
    |
    v
llama.cpp
```

or:

```text
Open/Free Cloud
    |
    v
Remote inference endpoint
```

or, later:

```text
Optional accelerated environment
```

This keeps the architecture portable.

---

# 16. Privacy and Semiconductor IP

The CPU/local-first architecture has an additional benefit for semiconductor development.

AIQ-VeriClave may process:

- proprietary RTL
- verification environments
- VCDs
- simulation logs
- specifications
- customer IP
- internal design information

Therefore, local inference reduces the need to send sensitive RTL/IP to commercial external AI APIs.

The preferred architecture is:

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

External/open-cloud resources should only receive data that the project's security policy permits.

---

# 17. Cost Target

The blueprint currently specifies:

> Cost <= $0.50 average verified task.

This should remain a target, not an assumption.

The system should measure:

- CPU seconds
- peak RAM
- LLM tokens
- inference time
- verification CPU time
- number of candidates
- closure iterations
- cloud compute usage
- estimated electricity cost

Then calculate:

```text
AIQ-VeriClave Cost / Verified Task
```

This provides a meaningful cost metric even when the system operates primarily on local hardware.

---

# 18. Do Not Train From Scratch

The preferred training strategy is:

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

Avoid:

```text
Raw data
   |
   v
Train 7B/30B/80B from scratch
```

This is not compatible with the project's initial low-cost strategy and is unnecessary for P0.

---

# 19. Revised AIQ-VeriClave Roadmap

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

---

# 20. Immediate Change to the Existing Blueprint

The existing blueprint contains compute estimates involving GPU-hours for future SFT/GRPO work.

Those estimates should **not be deleted**, but should be classified as:

> **Optional Future Accelerated Compute**

rather than the expected development path.

The primary development path should explicitly state:

> **CPU/local/open-compute-first development.**

Then:

> GPU acceleration is an optional optimization to be introduced only if experiments demonstrate that it is necessary.

---

# 21. Recommended P0 Architecture

The first implementation should therefore be:

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

---

# 22. First P0 Benchmark

The first benchmark should use existing AIQ assets.

The blueprint identifies T0 assets including:

- `verif/`
- simulations
- VCDs
- traceability CSV
- sign-off reports
- RideProtect
- MIPI
- V2X
- existing vectors
- seeded bugs

The recommended sequence is:

### P0-A

**RideProtect-RV v2.5**

### P0-B

**MIPI CSI-2**

Then add carefully selected external designs for independent evaluation.

The objective is:

```text
AIQ internal development set
          +
AIQ validation set
          +
External held-out benchmark
```

---

# 23. P0 Dashboard

The first milestone should not be:

> "We trained AIQ-VeriClave."

It should be:

> **"AIQ-VeriClave automatically generates verification artifacts, executes deterministic verification, records evidence, identifies failures, and performs controlled closure iterations."**

A basic P0 dashboard should measure:

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

# 24. Recommended Development Principle

The most important architectural principle is:

> ## Evidence-First AI

**No AI-generated verification artifact is considered valid merely because an AI model claims that it is valid.**

It becomes valid only after passing the appropriate deterministic verification and evidence checks.

This principle creates a clear separation:

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

---

# 25. Final Recommendation

The AIQ-VeriClave development strategy should now be defined as:

### Primary principles

1. **CPU-first**
2. **Open-source-first**
3. **Local-first**
4. **Open-cloud optional**
5. **No paid GPU cloud dependency**
6. **No training in P0**
7. **Small/quantized models first**
8. **Model-agnostic architecture**
9. **Deterministic verification as the source of truth**
10. **SFT only when experimentally justified**
11. **Specialized small models where appropriate**
12. **GRPO only as a conditional experiment**
13. **Evidence-led evaluation**
14. **Proprietary verification-data flywheel**
15. **GPU acceleration only when proven necessary**

### The immediate objective

Build the **AIQ-VeriClave P0 system**, not the final trained model.

P0 should establish whether the complete verification architecture can work reliably and economically on local/open infrastructure.

Only after P0 produces real measurements should the project decide:

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

This keeps AIQ-VeriClave aligned with a low-cost, open, privacy-conscious and experimentally driven development strategy.
