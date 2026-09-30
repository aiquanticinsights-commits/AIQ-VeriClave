# P0 Gate Review V8 — Gate E closes: P0 GO (2026-09-30)

> v1–v7 stand frozen. This review executes the V8 objective verbatim
> (E1 + E2, A–D preserved untouched — no architecture/model/gate changes).
> Same rule throughout.

## E1 — SBY smoke container: PASS (9/9 criteria)

Minimal formal toolchain proven working, not asserted: yosys 0.69 +
sby 0.69 + boolector 3.2.4 + system python3 in ~260MB (vs the rejected
745MB suite — 2.8× smaller with pinned URL+sha256). Counter proof PROVEN
in-container; versions, git commit, image digest, and exclusion reasons
recorded (`SBY_SMOKE.json`). No host toolchain used (verified: no mounts).
Subset-trial path documented the rejections (bundled python, extra
solvers, GUI libs) with measured sizes.

## E2 — Docker ↔ WSL live benchmark: PASS (7/7 rows)

E2-BENCH-001 at one git commit, both envs: lint, FRM traces (identical
sha), unittest (320 green both), sby demo (WSL) + smoke proof (container),
5-mutant spot (identical classifications incl. one SURVIVED — agreement
includes negative outcomes), evidence presence. Normalized comparison —
no byte-identity demands anywhere. Overall PASS (`E2_PORTABILITY_REPORT.json`).

Two genuine infrastructure findings fixed en route (both recorded in
code): container→host mount writes proved non-durable (stdout transport
now), and an arg-passing bug mounted the wrong tree (caught by the
UNMEASURED tripwire doing exactly its job).

## Full board

| Gate | Verdict | Ground (frozen evidence) |
|---|---|---|
| A — system works? | **PASS** | C1 95.12%, acceptance fn 6/6, sim/formal/FPR/trace/audit |
| B — closure works? | **PASS** | 2 in-run rescues + hard invariant, fault-hints + localizer live |
| C — efficient? | **PASS** | Measured cost/latency/tokens, still tracked |
| D — review scalable? | **PASS** | Live reviewer data: 20% rate, 18.7s median |
| E — reproducible? | **PASS** | E1 9/9 + E2 7/7, both committed |

**Decision: P0 GATE = GO — first ever.** Seven consecutive reviews earned
it: five NO-GOs that each certified a smaller unknown, then this one.

What GO means and does not mean:
- GO means the P0 *system* is demonstrated on wb_dma with full evidence;
  C-bands at loop scale, A_IRQ formal, T4/R2/R5 walls, and benchmark
  portability beyond the smoke remain tracked open items for P1 — listed,
  not hidden.
- Release is still gated on named-human sign-off (unchanged policy —
  sign-off PENDING everywhere, including this file).

Sign-off: PENDING (named human required per `policy.HUMAN_SIGNOFF_ACTIONS`).
