# P4 Exit Review — GO with conditions (evidence: `P4_EXIT_EVIDENCE.json`)

Date: 2026-10-13. Reviewer: opencode session (machine-generated draft) —
**human sign-off: PENDING** (named human required per `policy.HUMAN_SIGNOFF_ACTIONS`).

## Method
End-to-end demonstration (`demo_p4_exit.py`) on async-fifo (held-out family
member): intent → 4 generated artifacts → checker-vs-FRM execution incl.
seeded stuck-0 mutant → diagnostics → R0–R2 closure → trace chain → ledger →
formal-policy recommendation → repro envelope. Plus static verification that
P4-01..P4-14 artifacts exist with green tests.

## Per-item verdicts

| Item | Evidence | Verdict / maturity |
|---|---|---|
| P4-01 reconciliation index | file present, rows cite frozen artifacts | GO / **E2** |
| P4-02 architecture status | classification + frozen interfaces recorded | GO / **E2** |
| P4-03 benchmark frozen | `P4_BENCH_v1.json` + 7 schema tests green | GO / **E2** (E3 pending independent re-run) |
| P4-04 held-out manifest | 3+4 families, contamination rules, 6 tests green | GO / **E2** |
| P4-05 intent schema | fail-closed validation incl. live-caught `wclk`/`clk` mismatch during this review | GO / **E2** |
| P4-06 typed generation | 4 emitters, refusal paths, live checker exec | GO / **E2** |
| P4-07 diagnostics | 11-code schema == bench manifest, remedy routing | GO / **E2** |
| P4-08 closure boundary | 9 tripwires green; demo walked R0–R2 → PASS | GO / **E2** |
| P4-09 traceability | chains + completeness 1.0 demonstrated | GO / **E2** |
| P4-10 adapter registry | evidence-backed L1–L5; commercial parsers honestly L1 | GO / **E2** |
| P4-11 evidence workflow | PR template live; CI upload pre-existing | GO / **E2** |
| P4-12 pilot protocol | defined + preregistration rule; **not executed** | OPEN / **E1** (by design — execution is P7-track work) |
| P4-13 repro envelope | env/tool/git/hash record; tools honestly UNAVAILABLE-on-host | GO / **E2** |
| P4-14 P5 draft | frozen-before-execution spec written | GO as draft / **E0→E1** |

## Overall
**P4 EXIT: GO WITH CONDITIONS** — core capabilities demonstrated end-to-end
(E2 across the executable items); pilot execution (P4-12) and independent
re-runs remain open by design. Formal *execution* on this host recorded
UNAVAILABLE (Windows); Linux CI owns sby-backed proof per `formal_policy.py`.
No training authorized or required for this verdict. Human sign-off PENDING.
