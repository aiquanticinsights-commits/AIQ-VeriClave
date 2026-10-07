# Contributing to AIQ-VeriClave

Thank you for your interest in contributing. This project practices
**evidence-led engineering**: every change must prove itself with
machine-checked evidence before merge — the same standard the system
applies to chip designs.

By contributing, you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE) and that you abide by our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to contribute

- **Code**: scaffold modules (`router.py`, `eval_harness.py`, adapters, policies), tests, CI.
- **Verification evidence**: BugGen-style mutant campaigns, localization runs, closure reports on open RTL (OpenTitan, Ibex, your own blocks).
- **Docs**: blueprint clarifications, worked examples, benchmark reproductions.
- **Issues**: bug reports with reproduction steps, feature requests tied to a rating metric (§6 of the blueprint), `good first issue` walkthroughs.

## Ground rules (non-negotiable)

1. **Evidence-First**: no claim without a machine-checked artifact. Benchmark numbers must be reproducible from the repo (command + seed + commit).
2. **No silent gaps**: a failing test or uncovered case is dispositioned in the PR description, never dropped.
3. **Deterministic lanes stay deterministic**: changes to `policy.DETERMINISTIC_OPS` behavior require maintainer approval.
4. **License hygiene**: only Apache-2.0/MIT/BSD-compatible dependencies and data. No GPL/AGPL code, no scraped RTL of unclear provenance. Every new dataset entry in `datasets.py` must carry license + caveats.
5. **No confidential RTL**: never commit customer/proprietary RTL, VCDs with design internals, API keys, or credentials. Free-tier model outputs used for training require a privacy note.

## Development setup

```powershell
# Python 3.10+ (repo CI uses 3.11)
pip install -r requirements.txt   # cocotb, pytest, pyyaml (optional but recommended)

# Fast contract check (stdlib only, runs anywhere):
python -m unittest discover -s . -p "test_*.py"

# Full check incl. pytest suite:
pytest -q
```

Optional tools (gated, non-blocking if absent): Verilator 5 (`--version`),
Yosys, SymbiYosys (`sby`), Vivado xsim, `fsdb2vcd`. The suite skips gracefully
when a tool is missing — see `test_portability.py` conventions.

## Pull request process

1. **Open an issue first** for anything beyond a typo (use the templates in `.github/ISSUE_TEMPLATE/`). Link it as `Fixes #NNN` or `Relates to #NNN`.
2. **Branch**: `git checkout -b <type>/<short-name>` (`feat/`, `fix/`, `docs/`, `eval/`).
3. **Tests mandatory**: every behavior change ships with unit tests in `test_*.py`. Target: full suite green (`python -m unittest discover -s . -p "test_*.py"`).
4. **No duplication**: check the blueprint (§§1–14) and `ARCHITECTURE.md` first — new docs must reference, not repeat. One concept, one canonical home (config values especially).
5. **Small, reviewable diffs**: one concern per PR; update docs touched by behavior changes.
6. **Review**: at least one maintainer approval. Repair/merge-policy changes (`policy.py` guards, sign-off logic) need two approvals, one from a maintainer.
7. **Merge**: squash-merge by maintainers. CI (`vericlave.yml`) must be green.

## Coding standards

- Python 3.10+, type hints on public functions, docstrings stating the contract (what it proves, not just what it does).
- Deterministic tests only: fixed seeds, no network, no wall-clock assertions, no GPU. Mock external tools at boundaries.
- `__pycache__/`, `*.vcd`, `*.log`, partial JSONs stay git-ignored (see `.gitignore`) — never force-add them.
- Keep the no-duplication rule for configuration: single source per knob (see `ARCHITECTURE.md` §5).

## Review expectations

- Reviewers check: evidence attached? gates referenced? tests deterministic? docs updated? license clean?
- Be kind and precise; request changes with file:line references and a suggested fix where possible.
- Response SLA: maintainers aim for first review within 5 working days.

## Recognition

Significant contributors are listed in release notes. Sustained, high-quality contributors are invited as maintainers.
