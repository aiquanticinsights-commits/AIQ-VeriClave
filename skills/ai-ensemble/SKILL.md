---
name: ai-ensemble
description: Run the AIQ-VeriClave router and eval harness over task suites, analyze winners by kind, track cost, and flag any metric below its rating band.
---

# ai-ensemble

## What I do
- Run `router.py` routing and `eval_harness.py` suites (`python eval_harness.py` → JSON: system_accuracy, by_kind closure_rate/avg_rounds).
- Compare per-kind results against blueprint §6 bands (mutant-kill, SVA-validity, localization, coverage, cost/task).
- Sweep ablations on request (k=1..5 shortlist, min_rounds 1..3) and report accuracy-vs-cost trade-offs.

## When to use me
Use for ensemble experiments, rating runs, router calibration, and any "which generator wins" analysis.

## Hard rules
1. Mock backends are for loop/format validation only — never quote mock numbers as model capability; production runs need live Verilator-backed verifiers.
2. Report cost alongside accuracy (avg_rounds × per-call cost); a band hit at 3× cost is a flag, not a pass.
3. Keep generator capability priors in `router.py` synced with the latest measured §6 baselines; note the source commit/date of any prior change.

## Report format
system_accuracy + per-kind table (tasks/closed/rate/rounds), band verdicts PASS/FLAG/FAIL, cheapest config meeting all bands.

## Token-efficiency reporting (see blueprint §12)
- Always include the `tokens` section (input/output/cached/cost_usd/by_generator) with every eval report.
- Compare cascade-vs-flat-BoN cost on identical seeds; report $/task against the ≤$0.50 band.
