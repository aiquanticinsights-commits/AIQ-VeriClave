# Development Roadmap P4–P7 (P4–P7 plan §14 + backlog §20, tracked)

> Living tracker. Status values: DONE · IN-PROGRESS · OPEN · BLOCKED · DROPPED.
> P3 is CLOSED and stays closed — its constraints feed P4 as inputs (§6).

```text
P3 CLOSED → P4 system/workflow → P5 held-out qualification → P6 productization → P7 pilot value
```

## P4 backlog (§20)

| ID | Work item | Priority | Status | Evidence when done |
|---|---|---|---|---|
| P4-01 | `CAPABILITY_RESULT_RECONCILIATION.md` | P0 | **DONE** (this cycle) | this file's companion |
| P4-02 | `ARCHITECTURE_STATUS.md` | P0 | **DONE** (this cycle) | companion file |
| P4-03 | Freeze P4 benchmark protocol | P0 | **DONE** (this cycle: `P4_BENCH_v1.json` frozen + `test_p4_bench.py` 7 tests) | versioned benchmark tag |
| P4-04 | Define held-out design families | P0 | **DONE** (this cycle: `P4_HELDOUT_v1.json` frozen — 3 dev + 4 held-out families, contamination rules + 6 schema tests) | frozen family manifest |
| P4-05 | Structured verification-intent schema | P0 | **DONE** (this cycle: `intent.py` typed schema + fail-closed validation + round-trip; `test_intent.py` 10 tests) | schema + tests |
| P4-06 | Typed generation interface | P0 | **DONE** (this cycle: `generate.py` — SVA/covergroup/checker/test emitters from validated intent only, invalid intents refused; `test_generate.py` 10 tests) | generated-artifact tests |
| P4-07 | Machine-readable verifier feedback | P0 | Diagnostic schema (SYNTAX_ERROR…CLOCK_DOMAIN_MISMATCH) + tests |
| P4-08 | Qualify 3-round closure boundary | P0 | OPEN | boundary-test evidence (no Round 4, no overwrites) |
| P4-09 | Requirement-to-evidence traceability | P0 | OPEN | end-to-end trace artifacts (states per §7.7) |
| P4-10 | EDA adapter maturity metadata | P1 | OPEN | adapter registry (L1–L5 per tool×function) |
| P4-11 | GitHub evidence workflow | P1 | OPEN | CI evidence artifacts on PRs |
| P4-12 | Developer-value experiment definition | P1 | OPEN | pilot protocol (human-only vs assisted) |
| P4-13 | Reproducibility envelope | P1 | OPEN | reproduction report (Docker/WSL pinned) |
| P4-14 | P5 qualification protocol draft | P1 | OPEN | frozen-protocol specification |

Also tracked: this file itself (roadmap tracker = DONE on creation).

## P5 → P6 → P7 gates (entry criteria, not started)
- **P5**: P4 exit (core ≥E2, critical E3 where frozen) + frozen protocol/families/model/criteria → independent eval, leakage controls, FP + review-burden quantified.
- **P6**: P5 E3 + reproducible deploy, install docs, CI/CD, retention, security model, logging, recovery, stable interface.
- **P7**: P6 stable + controlled pilot (human-only baseline vs assisted), productivity/quality delta, economics, satisfaction, risks documented.

## Training decision framework (standing)
Training NOT authorized merely because: more data / model available / larger model wins / benchmark hard / d1 low. Reconsider only on: repeatable gap + exhausted system methods + adequate scale/diversity + contamination screened + balanced labels + learnability + held-out eval + measurable hypothesis + cost justification + audit preservation. (No change — restated for tracker completeness.)
