# Logging & Observability — AIQ-VeriClave (P6)

> The system is **structured-evidence-first**, not log-file-first. Machine truth
> is emitted as JSON (hash-chained ledger + run reports + a `FailureEvent`
> stream), never as free-form console text that could be lost or hand-edited.
> This document describes what is emitted, where it lands, and how to consume
> it. It does **not** claim a Python `logging` framework — the repo uses none
> by design (determinism + auditable artifacts over log scraping).

## 1. Three observability planes

| Plane | Producer | Format | Purpose |
|---|---|---|---|
| **Evidence ledger** | `evidence.py` | append-only, hash-chained JSON (`to_json()`) | the auditable record of requirement → artifact → checks → verdict → sign-off |
| **Run reports** | `eval_harness.py`, `p5_execute.py`, `p5_rerun.py`, `pilot_*.py`, `demo_p4_exit.py` | one JSON per run | per-task metrics: accuracy by kind, tokens, USD, latency, closure rounds |
| **Failure events** | `sim_adapters.py` (`FailureEvent`), bridged by `diagnostics.py` | typed records (11-code diagnostic schema) | normalized tool/sim failures with remedy routing |

## 2. What each plane contains

### 2.1 Evidence ledger (`evidence.py`)
Each `EvidenceRecord` carries: `requirement_id`, `artifact`, `checks{}`,
`verdict` (one of 10 frozen states), `signed_by`, and provenance
(`tool`, `tool_version`, `rtl_commit`, `run_id`, `artifact_hashes`) plus
`prev_hash`/`hash`. Two computed health signals:

- `verify_chain()` → bool: the hash chain is intact (tamper-evident).
- `audit_completeness()` → float: fraction of records with a known verdict and
  evidence or an explicit disposition. **C4 requires 1.0.**

Invariant: `NOT_EXECUTED` is a *complete* record (the gap is recorded, not
dropped) and must **never** be rewritten to `PASS` — mutating a sealed record
breaks `verify_chain()` by construction.

### 2.2 Run reports (JSON)
- `eval_harness.py → report{tokens, accuracy_by_kind, rows[]}`
- `p5_execute.py / p5_rerun.py → P5_EXECUTION.json / P5_RERUN.json`
- `pilot_assist.py / pilot_human.py → P7_PILOT_*.json`
- `demo_p4_exit.py → end-to-end chain record`

These are the numbers cited in gate reviews; they are committed as evidence.

### 2.3 FailureEvent → Diagnostic stream
`sim_adapters.normalize(text, tool)` parses Verilator/VCS/Questa/Xcelium/Vivado
logs into `FailureEvent`s; `diagnostics.py` maps them to a frozen 11-code
schema with remedy routing. `sim_adapters.summarize(events)` aggregates counts.

## 3. Operational logging policy (recommended)

| Concern | Rule |
|---|---|
| RTL / traces in logs | **never** echo RTL bodies, VCD slices, or sim logs to CI stdout (see `PUBLIC_PRIVATE_SPLIT.md`) |
| Redaction | apply `cache_policy.redact` to any prompt/response that may leave the bench |
| Levels | not applicable (no log framework); use JSON artifacts + exit codes |
| Retention | keep every signed gate artifact; prune scratch on release tags (`INSTALL.md` §Retention) |
| Correlation | join records by `run_id` and `rtl_commit`; ledger hash chain is the source of truth |
| CI | upload evidence JSON as Actions artifacts; **do not** print artifacts to the job log |

## 4. Health checks (what to look at)

1. `verify_chain()` is `True` — ledger not tampered.
2. `audit_completeness() == 1.0` — no silent gaps.
3. Re-run agreement: `p5_rerun.py` verdict is `REPRODUCED` (byte-identical JSON).
4. No `UNPROVEN`/`UNAVAILABLE` without an explicit disposition reason.

## 5. Gaps (tracked)

| # | Gap | Note |
|---|---|---|
| L1 | No in-repo aggregate dashboard beyond JSON reports | `review_dashboard.py` provides review KPIs; broader ops dashboards are deferred (see `ARCHITECTURE_STATUS.md` deferred list) |
| L2 | No log-rotation/leveling framework | intentional; artifacts are small JSON, versioned |
| L3 | Remote/cloud run logs not normalized beyond tool adapters | add an adapter per new backend |
