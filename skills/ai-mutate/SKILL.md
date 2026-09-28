---
name: ai-mutate
description: Run BugGen-style mutant campaigns on a target IP with Verilator as oracle, then check in the mutation cache and blind-spot report.
---

# ai-mutate

## What I do
- Partition target modules into regions; select mutation targets for coverage spread (avoid re-hitting cached regions).
- Inject one mutation class per scenario (missing assignment, logic bug, FSM transition, width/signedness), compile, run regression.
- Classify each mutant: killed (detected), blind-spot (valid but undetected — gold), invalid (syntax fail → rollback and log).

## When to use me
Use for WS2 campaigns and any "seed N bugs for localization/repair eval" request.

## Hard rules
1. Mutate copies under `verif/ai/mutants/` — never the golden RTL in place.
2. Roll back on syntax failure; record every attempt in the mutation cache (prevents redundant work across runs).
3. Stop the campaign early if functional accuracy drops below 90% — report, don't grind.
4. Blind-spot bugs (valid + undetected) are the primary output: file them as coverage targets for ai-close.

## Report format
Counts (generated/killed/blind-spot/invalid), functional accuracy, sim CPU-hours, top-3 blind-spot regions with file:line refs.
