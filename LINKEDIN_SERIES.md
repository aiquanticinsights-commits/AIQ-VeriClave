# AIQ-VeriClave — LinkedIn Series (9 posts)
Architecture · Plan · Status · Accomplished · Pending. All figures from signed repo evidence (P0_SIGNOFF_V8.md, P1/P2 completion reviews, P3 scope doc, P4 exit review, P5 freeze + execution/rerun records, v0.9.1 release).

---

## Post 1/7 — The problem (hook)

Everyone trains AI to *write* RTL. Nobody trusts it — because a wrong guess ships to silicon.

60–70% of chip effort is verification, not design. Yet every open RTL model is rated on generation benchmarks (pass@1), while the money burns in testbenches, debug closure, and respins.

So we flipped the objective. Meet **AIQ-VeriClave**: not an RTL generator — a verification intelligence platform. LLMs propose; deterministic engines dispose. Nothing is valid because a model claims it. Only machine evidence counts.

Evidence-First AI. That's the whole thesis. 🧵 6 more posts: architecture, plan, signed results, an honest NO-GO, and what's next.

#Semiconductors #AI #HardwareVerification #RISC-V #OpenSource #EDA #AISilicon

---

## Post 2/7 — Architecture

AIQ-VeriClave is a platform, not a checkpoint. Three layers:

**Layer 1 — Truth (deterministic, 16 ops).** Simulation, formal proof, mutation kill, coverage, traceability, evidence recording. No LLM allowed here — ever.

**Layer 2 — Intelligence (AI).** Generation, reasoning, localization, repair ranking, requirement decomposition. The LLM proposes evidence-producing actions; it never manufactures evidence.

**Layer 3 — Learning (gated).** SFT, specialization, GRPO — each unlocked only by measured evidence, never by roadmap optimism.

Around it: a RouteMoA-style router (cheap model first, escalate on failure), a hash-chained evidence ledger with human sign-off, and adapters for Verilator *and* commercial sims (VCS/Questa/Xcelium/Vivado) plus UVM skeletons.

Models are replaceable components. Evidence is the product. 3/7 next: the plan.

#ComputerArchitecture #FormalVerification #LLM #SystemDesign #ChipDesign

---

## Post 3/7 — Plan (CPU-first, PHASE 0–7)

No GPU farm. No $100K training run on day one. The plan:

**PHASE 0** — CPU-first P0: frozen open models + deterministic harness + C1–C5 baselines on our own IPs (RideProtect-RV, MIPI CSI-2).
**PHASE 1** — Benchmark 1B/3B/7B-class models on CPU; pick baseline on *our* verification tasks.
**PHASE 2** — Full verification system with closure loop.
**PHASE 3** — Proprietary dataset (trajectories, mutants, proofs, closures).
**PHASE 4/5/6** — SFT, then specialization, then GRPO — *each conditional* on the previous gate proving a need.
**PHASE 7** — Productize only what the gates earned.

Standing rule: the system must keep working with **zero GPU**. Cloud/GPU is an optional accelerator, never a dependency. Training is a hypothesis to be tested, not a milestone to be hit. 4/7: signed results.

#BuildInPublic #EngineeringManagement #MLOps #StartupIndia #DeepTech

---

## Post 4/7 — Accomplished: P0 signed GO ✅

Receipts, not claims. P0 Sign-Off V8 (2026-10-01), human-signed:

- Gates A–E: **all PASS**, acceptance function 6/6
- Mutant-kill rate **C1 = 95.12%**
- **2 genuine in-run closure rescues** (the loop demonstrably saves runs)
- Median human review time **18.7 s**, review load 20%
- Formal/tasks E1 = 9/9, E2 = 7/7
- Cost/latency/token ledgers recorded per task

P1 closed complete behind it: formal dispositions, capability findings, scale validation, portability/reproducibility — all approved.

Known limits were written down, not buried: C-band scale work, formal bounds, T4/R2/R5 capability walls → carried as tracked P1 items. A sign-off that lists its own gaps is worth more than a demo that hides them. 5/7: the NO-GO we're proud of.

#Verification #QualityEngineering #EvidenceBased #Tapeout #SoC

---

## Post 5/7 — The honest NO-GO (P2: training NOT authorized) 🛑

This one matters most. P2 asked: do bigger/alternative models break through our capability walls (T4 ≥90%, R2 closes)?

Measured, frozen-benchmark answer:
- T4: llama 70%, deepseek 55% — bar 90% → **WALL STANDS**
- R2: llama 0/20, deepseek 3/20 → **UNDER BAR**

Verdict: **FAIL — training NOT authorized.** P2 closed with P2-M4/M5 passes intact and frozen P0/P1 evidence unchanged.

Why post a failure? Because the gate worked exactly as designed: no GPU spend, no SFT started "because the corpus exists," no benchmark moved. A verification company that grades its own homework honestly is the entire product thesis, demoed live.

Walls stand → they become the P3 experimental program, not a quiet footnote. 6/7: what's pending.

#Integrity #AIEthics #MLResearch #FailForward #DeepTech

---

## Post 6/7 — P3 closed: what the four tracks found 🔬

Scope was frozen; invariance (same host/benchmark/verifier/judge/bars) held throughout:

- **P3-A** (14B local): R2 17 closes, 0 false acceptances — partial win, verdict sign-off pending
- **P3-B** (ensemble): union ceiling 3/20 < bar 4 — **FAIL**, and an informative one: the gap is capability, not selection
- **P3-C** (structured pipeline): 0→8/20 closes, 0 FA — system beats model-swap
- **P3-D** (data readiness): 278 generations catalogued, overwhelmingly negative — valuable for failure analysis, **not SFT-ready** (no held-out split)

P3 validated the system direction and priced the next bottlenecks. It did not authorize training — that discipline is the point. 7/7: the ask (updated below), then what's new since.

#Roadmap #ExperimentDesign #OpenSource #FPGA #RISC-V

---

## Post 7/7 — The ask 🤝

AIQ-VeriClave is open, evidence-led silicon verification — and we're looking for:

1. **Pilot IPs** — teams with RTL blocks + specs who want a free P0-style verification pass (you keep your IP; we publish only aggregate metrics).
2. **Verification engineers** — especially formal (SymbiYosys/JasperGold), UVM, and mutation-testing practitioners in Bangalore/Hyderabad.
3. **Collaborators** — EDA researchers working on assertion generation, fault localization, coverage closure.

What you get: machine-checked evidence ledgers, blind-spot reports your regressions missed, and honest gates — including NO-GOs when the data says so.

DM me here or reach via aiqi.in. P3 results are published with receipts in the repo — and the story continues in post 9/7. 🙏

#Hiring #Collaboration #SemiconductorIndustry #IndiaTech #Founder #AIQVeriClave

---

## Post 8/7 — Contributors call (repo is public)

We're open — and we mean it. 🤝

**AIQ-VeriClave is now public on GitHub**: Apache-2.0, README, contributing guide, code of conduct, issue templates, protected `main`, and CI. github.com/aiquanticinsights-commits/AIQ-VeriClave

What we're building: verification AI for silicon where *evidence beats claims* — ensemble routing, machine-checked testbenches, mutation-driven blind-spot reports, bounded formal proof, hash-chained sign-off ledgers. P0 signed GO (C1 = 95.12%); P2 closed with an honest NO-GO when models hit capability walls. That's the culture you'd join.

**8 mentored starter issues are live** — vendor-log fixtures, VCD edge cases, docs proofreads, dataset proposals, benchmark reproductions, R2-wall attack, held-out family #5, T4 ablation. Each has acceptance criteria; maintainers review within days.

Start here: README (5-min quickstart, CPU-only) → CONTRIBUTING → pick a `good first issue` → PR. Students welcome — curiosity + rigor matter more than titles.

Star it, try the eval harness (`python eval_harness.py`, zero infra needed), break things, tell us. That's the contribution. 🙏

#OpenSource #ContributorsWelcome #GoodFirstIssue #ChipDesign #FormalVerification #Python #EDA #BuildInPublic #AIQVeriClave

---

## Post 9/7 — Release v0.9.0: P5 freeze ratified, independently reproduced 🚢

Since post 6/7, the program moved two full gates:

- **P4 exit: GO WITH CONDITIONS**, human-signed — including an end-to-end demo on a held-out FIFO family (seeded mutant killed, closure PASS, ledger sound). Along the way the harness caught *my own* 1-cycle FRM latency bug. The system works, including against its author.
- **P5 execution: 4/4 held-out families PASS** — 10/10 seeded mutants killed, 0 false alarms, deterministic re-runs agree, frozen inputs hash-verified.
- **Independent re-run: REPRODUCED** — byte-identical in a clean process, then green again on Linux CI (second machine). The CI gate now *fails* on any mismatch.
- **P5 freeze RATIFIED.** Training: still not authorized. Nothing in v0.9.0 changes that.

Release notes + evidence JSONs are downloadable on the GitHub release page. Next: P6 packaging is underway (INSTALL, Docker, changelog discipline); the pilot track awaits real participants.

Star, reproduce (`python p5_rerun.py` — one command), challenge our numbers. That's the whole game. 🙏

#Release #Reproducibility #OpenScience #CI #Semiconductors #AIQVeriClave
