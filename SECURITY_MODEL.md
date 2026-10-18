# Security Model — AIQ-VeriClave (P6)

> Scope: the CPU-only, open-core verification harness in this repository. This
> document states the threat model, the enforced controls, and the *explicit*
> residual risks. A control is only "enforced" here if a test or CI check makes
> it fail-closed; otherwise it is listed as procedural and flagged as such.

## 1. Assets

| Asset | Where | Sensitivity |
|---|---|---|
| Design RTL, proprietary specs, customer IP | operator-provided, local only | **HIGH** — never leaves the bench |
| Verification traces (VCD/FST), sim logs, trajectories | `evidence/run_*/`, working dirs | **HIGH** |
| Evidence ledger (hash-chained) | `evidence/` JSON | integrity-critical |
| Release credentials | CI secrets only | **HIGH** |
| Framework code + docs | repo | PUBLIC |

## 2. Trust boundaries

```
[Designer RTL] --local--> [AIQ-VeriClave harness] --local--> [LMStudio :1234]
                                   |                              (default)
                                   +-- optional remote endpoint (REDACTED prompts only)
                                   +-- EDA tools via subprocess (list argv, no shell)
                                   +-- CI: GitHub Actions runner
```

1. **Model boundary.** Default model backend is a **local** LMStudio server on
   `127.0.0.1:1234`. Any remote endpoint is opt-in and receives **redacted**
   prompts only (`cache_policy.redact`, fail-closed).
2. **Tool boundary.** All EDA/tool invocations are `subprocess.run(argv_list)` —
   never `shell=True`; no string interpolation into a shell. Tool absence is
   recorded as `UNAVAILABLE`, never silently ignored.
3. **Storage boundary.** Nothing is uploaded by the framework; it has no
   telemetry. The only outbound calls are the model queries above.

## 3. Enforced controls

| # | Control | Enforcement |
|---|---|---|
| C1 | No shell injection | every `subprocess.run` uses an argv list; repo grep has no `shell=True` |
| C2 | Redaction fails closed | `cache_policy.redact` masks unknown → `[REDACTED-DUT]` (uncertain ⇒ redact everything) |
| C3 | Cache never holds RTL | cache allow-list is spec/tool-defs only; RTL/VCD/logs are tail-only, never cached |
| C4 | Ledger integrity | `evidence.py` hash-chains every event; audit completeness asserted = 1.0 (`test_platform.py`) |
| C5 | Named-human sign-off | `policy.HUMAN_SIGNOFF_ACTIONS`; anonymous approvals rejected (`test_platform.py`) |
| C6 | No secrets in repo | `.gitignore` excludes `*.env`, tokens; CI reads secrets from `secrets.*` only; publish steps guarded by `env.X != ''` |
| C7 | No secrets in logs | CI does not echo secret values; adapters normalize logs, redaction applies to prompts |
| C8 | Deterministic, offline-by-default tests | suite is seeded, no network, no GPU (README contract) |
| C9 | Checker execution is isolated | human-arm/checker run via fresh `sys.executable -c` subprocess with a JSON result contract (`pilot_human.py`) |

## 4. Secrets handling (CI/CD)

Secrets are **never** committed. Required-to-publish (all optional; publish skips
cleanly when absent):

| Secret | Used by | Effect when absent |
|---|---|---|
| `TEST_PYPI_API_TOKEN` | `release.yml` → test-pypi | step skipped |
| `PYPI_API_TOKEN` | `release.yml` → publish-pypi | step skipped |
| `DOCKER_USERNAME`, `DOCKER_PASSWORD` | `release.yml` → docker-build | login/push skipped |

GitHub Actions does not permit the `secrets` context inside `if:`; guards use a
job-level `env:` mapped from the secret and step-level `if: env.X != ''`.

## 5. Confidentiality split

See [`PUBLIC_PRIVATE_SPLIT.md`](PUBLIC_PRIVATE_SPLIT.md). Summary: framework,
generic adapters, and docs are public; RTL, proprietary specs, customer IP,
traces, and confidential evidence are restricted and **must never** be mirrored
or sent to a remote endpoint unredacted.

## 6. Residual risks (tracked, not hidden)

| # | Risk | Status | Mitigation |
|---|---|---|---|
| R1 | Operator may configure a remote endpoint | procedural | redaction is enforced in code; detection of misconfiguration is procedural (no egress firewall in-repo) |
| R2 | No sandboxing/jail for EDA tool subprocesses | accepted | tools run as the invoking user; deploy behind container/VM boundary (see `Dockerfile`) |
| R3 | No in-repo dependency vulnerability scanner in CI | **open** | run `pip-audit` manually per release (T-05); pin via `requirements.txt` |
| R4 | Local LMStudio assumed trusted; no auth on `:1234` | accepted | bind to loopback only; do not expose the port |
| R5 | Evidence files may contain operator RTL snippets | procedural | keep `evidence/` in the restricted boundary; `.gitignore` excludes VCD/logs/partials |

## 7. Deployment guidance

- Run inside the provided container or a dedicated VM/workspace; do not co-locate
  with unrelated secrets.
- Bind the model server to `127.0.0.1`; block inbound ports.
- Keep the repo's `.gitignore` intact so traces/partials never get committed.
- Treat any release-signing and packaging step as human-gated.

## 8. Reporting

Security issues: open a **private** advisory / contact the maintainer rather than
a public issue. Do not paste RTL, specs, or traces into an issue.
