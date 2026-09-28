---
name: ai-verify-harness
description: Run the make ai-verify ladder (gen, sim, mutate, localize, close, report), read JSON reports, and enforce per-stage acceptance gates before anything graduates.
---

# ai-verify-harness

## What I do
- Run `make ai-verify`, `ai-gen`, `ai-sim`, `ai-mutate`, `ai-localize`, `ai-close`, `ai-report` targets.
- Parse the JSON report (`eval_harness.py` format: closure_rate, avg_rounds, by_kind) and compare each stage against the trust-ladder gates.
- Update the cost ledger ($/bug, sim CPU-hours) every run.

## When to use me
Use when executing or checking any verification-ladder run (WS0–WS6). nightly CI included.

## Hard rules
1. Never modify files under `rtl/` — artifacts go to `verif/ai/` only.
2. A stage that misses its gate FAILS the run; do not promote its outputs.
3. Golden-vs-golden must be clean before any mutant result is trusted.
4. Every artifact cites requirement IDs from the traceability CSV.

## Report format
Per gate: PASS/FAIL, measured value vs threshold, cost, and the single next action on FAIL.
