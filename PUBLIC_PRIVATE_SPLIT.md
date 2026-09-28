# AIQ-VeriClave — Public / Private split (confidentiality boundary)

Source: `Arch-Docs/dev_env.md` caution (private repo ≠ safe cloud storage).
Enforced by review, not by tooling. When in doubt, keep PRIVATE.

## PUBLIC / OPEN (may go to a future `-public` mirror after review)

- framework (`router.py`, `eval_harness.py`, `rewards.py`, `p0.py`, `evidence.py`, `policy.py`, `compute.py`, `cache_policy.py`, `compact.py`)
- generic verification infrastructure (`sim_adapters.py`, `vcd_events.py`, `formal_policy.py`, `uvm_gen.py`)
- documentation (`ARCHITECTURE.md`, `DIAGRAMS.md`, `OPENCODE_WORKFLOW.md`, `ENVIRONMENT_LOCKIN_PLAN.md`, `Dockerfile`, `.github/workflows/`)
- open-source integrations, benchmark examples (no customer RTL)

## PRIVATE / RESTRICTED (this repo — never mirror)

- AIQI RTL, RideProtect implementation, MIPI CSI-2 implementation
- proprietary specifications, customer IP, proprietary datasets
- verification traces (VCD/FST), confidential evidence (`evidence/run_*/`)

## Rules

1. Remote LLM providers are part of the confidentiality boundary — default to local LMStudio (`:1234`); redacted prompts only to any remote endpoint.
2. Cacheable: system prompts, redacted specs, FRM templates, tool defs. Never cached: RTL bodies, VCD slices, sim logs, trajectories.
3. CI logs must not echo RTL. Evidence artifacts stay in private Actions artifacts.
