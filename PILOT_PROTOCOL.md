# Pilot Protocol (P4-12) — developer-value experiment definition

> Compares human-only vs AIQ-VeriClave-assisted verification workflows on the
> same frozen tasks. A technically impressive system is not automatically a
> useful product — this protocol measures the difference.

## Design
- **Tasks**: frozen subset of `P4_BENCH_v1.json` tracks (structured generation,
  verifier feedback, closure boundary, traceability) on one dev family +
  one held-out family (`P4_HELDOUT_v1.json`).
- **Arms**: (H) senior verification engineer, unassisted, capped hours;
  (A) same-profile engineer assisted by the P4 system (router → generate →
  machine verify → Judge → ≤3 closure rounds → ledger).
- **Blinding**: graders see artifacts + evidence only, not arm labels.

## Measures (per task, both arms)
total task time · verification-authoring time · review time · iterations ·
defects discovered · false alarms · accepted/rejected artifacts · rework ·
compute cost · human effort · cost per accepted requirement · defects found ·
evidence completeness · developer satisfaction (1–5 + note).

## Acceptance for "developer-validated" (E4-track, not a pass yet)
- Assisted arm ≥ human-only on defects found AND review burden not worse AND
  evidence completeness = 1.0, with false alarms within the C5 band.
- Anything less is a finding (reported like P2-M3: FAIL with numbers), never
  a quiet scope cut.

## Hygiene (from program rules)
- Frozen benchmark/tags; no threshold edits mid-pilot (new version + ledger row instead).
- Proprietary participant RTL stays local; only aggregate metrics leave the bench.
- Human sign-off on every release-impacting conclusion.
- Pre-register: tasks, bars, arms, and analysis plan BEFORE first run (this file + ledger row = preregistration).
