---
name: ai-close
description: Drive GoGoTB-style spec-to-coverage closure with root-cause gap taxonomy, stall detection, and an auditable sign-off ledger. Repair diffs are proposed, never merged.
---

# ai-close

## What I do
- Derive testpoints across 7 dimensions (data boundaries, control flow, timing, FSM, protocol, error injection, microarch interaction) from the spec + RTL.
- Convert testpoints to coverage bins with named behavioral claims; run adaptive-seed simulation rounds.
- Classify every residual gap by root cause (stimulus, sequence, cross-cover, unreachable FSM, timing, edge, sampling); route each to its targeted remedy; stall-detect (2 flat rounds → stop).
- Emit the sign-off ledger: evidence per covered bin, disposition per residual gap.

## When to use me
Use for WS5 closure runs and any coverage sign-off request.

## Hard rules
1. Structurally unreachable bins are removed from the denominator explicitly — never silently.
2. No gap is dropped without a root-cause disposition; an unactionable gap fails the run loudly.
3. Repair suggestions follow Repair-R1 discipline (discriminative tests first) and require human approval + green regression before counting.
4. The ledger links every bin to requirement IDs.

## Report format
Line/branch/functional coverage deltas, bins closed by root-cause class, residual dispositions, rounds used, sign-off verdict.

## Developer-realism modules (see blueprint §10)
- Vendor logs (VCS/Questa/Xcelium/Vivado): normalize via `sim_adapters.py` before judging.
- Formal properties: get a `formal_policy.py` verdict first; ledger its `signoff_line()`.
- UVM shops: scaffold agents with `uvm_gen.py` (templates only; solving stays in-simulator).
