# Recovery — AIQ-VeriClave (P6)

> How the harness survives interruption and how an operator recovers a run
> without losing already-produced machine truth. The design principle is
> **crash-safe partials + deterministic re-run**: progress is checkpointed to
> disk as it happens and any frozen result can be independently reproduced.

## 1. Failure classes

| Class | Example | Recovery |
|---|---|---|
| Long run interrupted (timeout/kill/host reset) | `bakeoff.py`, `p0d.py`, `scripts/p3*`, `run_mutants.py`, `p5_execute.py` | re-launch with `--resume`; completed units are reloaded from the partial |
| Tool absent / unavailable | `sby`/Verilator not installed | recorded as `UNAVAILABLE` / `NOT_EXECUTED` (complete record), non-blocking |
| Network/model endpoint drop | LMStudio `:1234` connection reset (WinError 10054) | retry under identical frozen conditions; both attempts recorded, only the completed one scored |
| Evidence ledger tampering / corruption | edited JSON breaks the chain | `verify_chain()` returns `False`; do **not** hand-patch — re-run the producing step |
| CI job failure | transient runner/network | re-dispatch the workflow; publish steps self-skip when secrets absent |
| Partial file truncated mid-write | power loss during `json.dump` | delete the corrupt `*_PARTIAL*.json` and restart that unit (see residual risks) |

## 2. Checkpoint/resume convention

Long runners write a `*_PARTIAL*.json` after each completed unit and accept
`--resume`:

| Runner | Partial file | Resume flag |
|---|---|---|
| `bakeoff.py` | `BAKEOFF_PARTIAL_<suite>.json` | `--resume` |
| `p0d.py` | `P0D_PARTIAL.json` | `--resume` |
| `run_mutants.py` | `MUTATION_PARTIAL[__S<seed>].json` | `--resume` (seed-isolated) |
| `scripts/p3a_t4_remeasure.py` | `P3_A_T4_REMEASURE_PARTIAL.json` | reload-by-default |
| `scripts/p3c_qwen_run.py` | `P3_C_QWEN_PARTIAL.json` | reload-by-default |

Seed isolation matters: a fresh-seed mutant campaign never resumes from (or
clobbers) a frozen seed's partial (`run_mutants.py`). Partials are
`.gitignore`d so scratch never pollutes the evidence record.

## 3. Reproducibility as the ultimate recovery

Because runs are deterministic (fixed seeds, frozen tags, no network in tests),
the strongest recovery is **re-derivation**, not restoration:

```powershell
python p5_rerun.py     # clean subprocess re-run vs committed P5_EXECUTION.json
# verdict REPRODUCED == canonical JSON byte-identical across runners
```

If a committed result cannot be reproduced, that is a finding, not a retry.

## 3a. Interactive human-arm session recovery
`pilot_human.py` uses forward-only phases and an attestation gate. An
interrupted session is sealed and the abort is recorded (as in ledger `P4-21`);
a clean restart requires a new session with no AI authoring help and no partial
data carried forward — aborted data is never laundered into the result.

## 3. Ledger integrity

- `EvidenceLedger.verify_chain()` recomputes every record hash and link.
- A `False` result is an **incident**: the ledger is untrusted. Re-run the
  producing step to regenerate; never edit sealed records to make the check pass.
- `audit_completeness() != 1.0` means an entry lacks a verdict or evidence —
  record the gap explicitly (`record_not_executed`) rather than deleting it.

## 3. Retention & backup

Per `INSTALL.md`: keep every signed gate artifact; prune scratch/partials on
release tags. `.gitignore` excludes `*_PARTIAL*.json`, `*.vcd`, `*.log`. Back up
the committed evidence JSON — the ledger hash chain makes integrity verifiable
after restore.

## 6. CI recovery

- Re-run a failed workflow from the Actions UI (or `gh run rerun <id>`).
- `release.yml` publish jobs skip cleanly when registry secrets are unset, so a
  missing secret never blocks the build/test/release jobs.
- On a bad tag/release: delete the GitHub release and tag, re-tag the intended
  commit, and push (this was done for the v0.9.1 re-cut — see ledger P6-04).

## 3. Residual risks (tracked, not hidden)

| # | Risk | Status | Note |
|---|---|---|---|
| RC1 | Partials written non-atomically (`json.dump` directly to the final path) | **open** | a crash mid-write can truncate a partial; recovery = delete + restart unit. Fix: write-to-temp + `os.replace` |
| RC2 | No auto-resume / supervisor | accepted | runs are operator-driven; `--resume` is manual |
| RC3 | No automated backup of `evidence/` | procedural | keep evidence in version control / restricted store |
| RC4 | Wall-clock retries are manual | accepted | documented in the retry record (`P3_A_VERDICT.json` sample-4 precedent) |
