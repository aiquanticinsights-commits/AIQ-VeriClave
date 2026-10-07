# AIQ-VeriClave — Verification AI Platform for Silicon

> LLMs propose. Machines dispose. Nothing is valid because a model claims it —
> only machine-checked evidence counts.

**AIQ-VeriClave** is an open, CPU-first system that turns RTL designs +
specifications into verified verification artifacts (testbenches, reference
models, SVA assertions, coverage sign-off) with an auditable evidence trail.
Verification consumes 60–70% of chip effort; every open RTL model optimizes
*generation* scores instead. AIQ-VeriClave optimizes *verification closure*
on real SoC IP — ensemble generation, machine verification, iterative
closure, human sign-off.

- **Status**: P0 signed GO (gates A–E PASS, C1 = 95.12%) · P1 complete ·
  P2 closed with training explicitly NOT authorized (capability walls stand —
  see reviews; honesty is the feature) · P3 experimental program in progress.
- **License**: Apache-2.0 — see [LICENSE](LICENSE).
- **Contributing**: start with [CONTRIBUTING.md](CONTRIBUTING.md) and the
  [Code of Conduct](CODE_OF_CONDUCT.md).

## How it works (60 seconds)

```
SPEC + RTL ─► ROUTER ─► GENERATORS (BoN) ─► MACHINE VERIFIERS ─► JUDGE ─► PASS/FAIL
                                                                    │        │
                                                              artifact   closure (≤3)
                                                                    │        │
                                                              LEDGER ◄──────┘
                                                                    │
                                                              HUMAN SIGN-OFF
```

1. **Route** (`router.py`): pick the cheapest capable generators (adaptive BoN 3/5/8, cascade, $0.50/task ceiling).
2. **Generate**: candidate testbenches, reference models, assertions.
3. **Verify with machines, not opinions**: Verilator/Yosys/SymbiYosys/sv-parser, BugGen-seeded mutants, requirement traceability (`sim_adapters.py` also normalizes VCS/Questa/Xcelium/Vivado logs).
4. **Judge + close**: majority vote with self-check discipline, GoGoTB-style root-cause closure, stall detection (`ai-close`).
5. **Evidence ledger** (`evidence.py`): hash-chained, 100% audit completeness required, named-human sign-off — no anonymous approvals, no silent gaps.

Full design: [`AIQ_VERICLAVE_MODEL_BLUEPRINT.md`](AIQ_VERICLAVE_MODEL_BLUEPRINT.md) ·
build order: [`ARCHITECTURE.md`](ARCHITECTURE.md) · diagrams: [`DIAGRAMS.md`](DIAGRAMS.md) ·
execution pipeline: [`../V2X-OBU-AIS230/docs/AI_VERIFY_EXECUTION_PLAN.md`](../V2X-OBU-AIS230/docs/AI_VERIFY_EXECUTION_PLAN.md).

## Quickstart

```powershell
# 1. Python 3.10+ (repo CI uses 3.11). CPU-only; no GPU needed for P0.
pip install -r requirements.txt   # cocotb, pytest, pyyaml (optional)

# 2. Contract check — stdlib only, runs anywhere:
python -m unittest discover -s . -p "test_*.py"

# 3. Full suite (pytest):
pytest -q

# 4. Run the ensemble eval on mocks (no infra needed):
python eval_harness.py            # -> JSON: accuracy by kind + tokens/USD/CPU ledger
```

Optional (gated, non-blocking): Verilator 5, Yosys, SymbiYosys (`sby`),
Vivado xsim, `fsdb2vcd`. Missing tools skip gracefully. For the OpenCode
agentic workflow (skills per pipeline stage), see [`OPENCODE_WORKFLOW.md`](OPENCODE_WORKFLOW.md).

## Repository layout

| Path | What lives here |
|---|---|
| `router.py`, `rewards.py`, `eval_harness.py` | Ensemble routing, canonical RL reward, eval + token ledger |
| `evidence.py`, `policy.py`, `p0.py`, `compute.py` | Ledger, constitutional policy, P0 profile/ablation, compute backends |
| `cache_policy.py`, `compact.py` | Redacted-prefix caching, CliffCompaction rules |
| `sim_adapters.py`, `vcd_events.py`, `formal_policy.py`, `uvm_gen.py` | Vendor log adapters, VCD drift pinpointer, bounded-formal policy, UVM skeletons |
| `datasets.py` | External corpora registry (license/consumer/caveats enforced by tests) |
| `bakeoff.py`, `mutate.py`, `localize.py`, `repair.py`, `review.py`, `portability.py`, … | Pipeline stage implementations |
| `test_*.py` | Deterministic unit tests (fixed seeds, no network, no GPU) |
| `skills/` | OpenCode skill definitions per stage (`ai-verify-harness`, `ai-mutate`, …) |
| `P0*_*.md`, `P1_*`, `P2_*`, `P3_*`, `GATE_*` | Signed gate reviews and evidence records |
| `.github/workflows/vericlave.yml` | CI |

## Roadmap (gated — phases unlock on evidence, never on dates)

- [x] **PHASE 0** — CPU-first P0: harness, frozen models, C1–C5 baselines → **GO (V8 sign-off)**
- [x] **PHASE 1** — CPU model benchmark + baseline pick → **COMPLETE**
- [x] **PHASE 2** — Verification system evaluation → **CLOSED, training NOT authorized** (walls documented)
- [ ] **PHASE 3** — Proprietary dataset (trajectories, mutants, proofs, closures) — *in progress: 4 controlled tracks*
- [ ] **PHASE 4** — SFT/LoRA, only if a model-specific limitation is proven
- [ ] **PHASE 5** — Specialized small models (router, classifiers, reranker)
- [ ] **PHASE 6** — GRPO experiment, only if a measured residual suits RL
- [ ] **PHASE 7** — Productization (local-first, Apache-2.0 weights, eval cards)

## Design principles (the short version)

1. **Evidence-First**: proposals from AI, truth from machines, sign-off from humans.
2. **CPU-first**: works with zero GPU; accelerators are optional optimizations.
3. **No silent gaps**: every failure is dispositioned with a root cause or the run fails loudly.
4. **Open by default**: Apache-2.0 code, open toolchains, reproducible CPU-runnable evals.

Questions, pilot IPs, or research collaboration: open a
[GitHub Issue](https://github.com/aiquanticinsights-commits/AIQ-VeriClave/issues)
or reach us via [aiqi.in](https://aiqi.in).
