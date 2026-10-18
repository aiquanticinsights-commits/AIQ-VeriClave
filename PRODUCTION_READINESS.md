# Production Readiness — AIQ-VeriClave (P6 → P7)

> Consolidated, honest gate status as of 2026-10-18. Every "DONE" below cites a
> runnable check or artifact produced this cycle; every "BLOCKED" names the
> exact human/external action required. No criterion is marked done on intent.

## 1. P6 entry criteria (from `DEVELOPMENT_ROADMAP_P4_P7.md`)

| Criterion | Status | Evidence |
|---|---|---|
| P5 qualification at E3 | **DONE** | 4/4 families PASS; independent re-run REPRODUCED (`P5_EXECUTION.json`, `P5_RERUN.json`) |
| Reproducible deploy (source) | **DONE** | `pip install .`, frozen contract suite green |
| Reproducible deploy (Docker) | **DONE** | image builds and runs: 65 tests OK in-image; Verilator 5.020 + Yosys 0.33 present; sby absent → non-blocking |
| Install docs | **DONE** | `INSTALL.md` |
| CI/CD | **DONE** | `vericlave.yml`, `p5-rerun.yml`, `release.yml`, `signoff.yml`; all pass `actionlint`; release pipeline green on v0.9.1 |
| Retention | **DONE** | `INSTALL.md` §Retention, `RECOVERY.md` |
| Security model | **DONE** | `SECURITY_MODEL.md` |
| Logging / observability | **DONE** | `LOGGING.md` |
| Recovery | **DONE** | `RECOVERY.md` |
| Stable interface | **DONE** | frozen interfaces in `ARCHITECTURE_STATUS.md` |
| Registry publish (PyPI) | **BLOCKED** | needs `PYPI_API_TOKEN` + `TEST_PYPI_API_TOKEN` (owner) |
| Registry publish (Docker Hub) | **BLOCKED** | needs `DOCKER_USERNAME` + `DOCKER_PASSWORD` (owner) |

## 2. Verification runs (this cycle)

| Check | Command | Result |
|---|---|---|
| Full unit suite | `python -m unittest discover -s . -p "test_*.py"` | **565 tests OK, 79 s** (T-02 fixed) |
| Container suite | `docker run --rm aiq-vericlave:test` | **65 tests OK** |
| Dependency audit | `pip-audit -r requirements.txt` and `pip-audit .` | **No known vulnerabilities** |
| Workflow lint | `actionlint` | **exit 0** (4 workflows) |
| Docker build | `docker build -t aiq-vericlave:test .` | **success** |

Dependency licenses (all permissive, Apache-2.0-compatible): pyyaml (MIT),
pydantic (MIT), cocotb (BSD-3-Clause), pytest (MIT).

## 2b. Fixes landed this cycle

- **T-02 (suite hang)** — `sim_frm.tool_ok()` and `portability.collect()` gated
  live toolchain tests on the mere presence of `wsl.exe`, then invoked
  `wsl verilator` with up to 600 s timeouts. Replaced with **bounded (15 s)
  reachability probes**; a non-functional WSL now fails fast and tests skip.
  `unittest discover` goes from *hanging* to 565 tests OK.
- **Dockerfile** — fixed a fatal bug (runtime stage copied `/app` from a stage
  that never created it); made `sby` best-effort/non-blocking; bumped the image
  version label to 0.9.1; non-root user; deterministic contract-suite `CMD`.
- **release.yml** — the `docker-build` job previously had **no build step**
  (its "success" was vacuous). Added an always-on image build + in-image
  smoke-run; push remains conditional on Docker Hub secrets.

## 3. P7 (pilot value) — partial

| Arm | Status | Evidence |
|---|---|---|
| Assisted | **DONE** | `P7_PILOT_ASSISTED.json` (5/5 mutants, FA 0) |
| Human | **BLOCKED (needs a person)** | last session ABORTED at the attestation gate (`P4-21`): AI help was used. A clean, human-only session is required |

E4 / developer-value is **not claimed**. The runner and protocol are ready
(`pilot_human.py`, `PILOT_PROTOCOL.md`, `HUMAN_ARM_RUNBOOK.md`).

## 4. What a human must do to finish P6/P7

1. **Registry publish (optional):** add `TEST_PYPI_API_TOKEN`, `PYPI_API_TOKEN`,
   `DOCKER_USERNAME`, `DOCKER_PASSWORD` as repo secrets; re-tag a release. The
   pipeline then publishes automatically (steps currently self-skip).
2. **Pilot human arm:** run `python pilot_human.py` in a session with **no AI
   authoring help**, pass the attestation gate, complete the two held-out tasks,
   and seal the output. Then the blinded human-vs-assisted comparison closes P7.
3. **Sign-off:** every release-impacting conclusion still requires a named-human
   signature (Evidence-First policy) — including ratifying this readiness record.

## 5. Verdict

**Installable and usable today by a technical evaluator** (source or Docker,
CPU-only, offline-capable, audited). **Not yet "publishable product"**: registry
distribution and the human pilot remain gated on owner/human action; capability
walls (T4, R2) stand as tracked research findings, not defects. Maturity: E2/E3,
not E4.
