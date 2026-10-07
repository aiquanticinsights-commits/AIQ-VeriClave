# Issue Labels — AIQ-VeriClave

Labels are enforced on the repo (`gh label list` currently shows 22).
Triage rule: every new issue gets `needs-triage` (auto via templates) until a
maintainer replaces it with area + priority labels.

## Type (what kind of work)

| Label | Meaning | Template |
|---|---|---|
| `bug` | Reproducible defect | bug_report.yml |
| `enhancement` | Feature tied to a §6 metric or roadmap phase | feature_request.yml |
| `verify-task` | Scoped verification job (mutate/localize/close/formal/benchmark-repro) | verification_task.yml |
| `documentation` | Docs, guides, examples | — |
| `question` | Needs clarification before action | — |

## Workflow (who must act)

| Label | Meaning |
|---|---|
| `needs-triage` | Fresh, unsorted — maintainers sort weekly |
| `needs-human-review` | Blocked on human sign-off (Evidence-First policy: merges, sign-offs, threshold changes) |
| `help wanted` | Open for any contributor |
| `good first issue` | Newcomer-friendly: small, documented, mentored — see starter list below |
| `wontfix` / `invalid` / `duplicate` | Terminal states with a reason comment |

## Area (where in the tree)

`area-router` · `area-eval` · `area-evidence` · `area-adapters` ·
`area-datasets` · `area-docs` · `area-ci`

## Priority

`priority-high` (blocks a gate/release) · `priority-low` (nice-to-have).
No label = normal priority.

## Good-first-issue starter list (maintainers: file these first)

1. Add one more vendor log fixture to `sim_adapters.py` + test (`area-adapters`, small, fully specified by existing patterns).
2. Add one VCD edge-case fixture to `test_adoption.py` (`area-adapters`).
3. Proofread one blueprint section for stale cross-refs (`area-docs`, no code).
4. Extend `datasets.py` with one new verified corpus entry + tests (`area-datasets`, research-flavored).
5. Reproduce one published number (e.g. BluesFL cost/bug arithmetic) as a test (`area-eval`).

## Bootstrap command (re-run after label changes)

```powershell
gh label list --repo aiquanticinsights-commits/AIQ-VeriClave
```
