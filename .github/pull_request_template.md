## Summary

<!-- One paragraph: what changes and which requirement/gate it serves. -->

## Evidence checklist (all PRs)

- [ ] Unit suite green: `python -m unittest discover -s . -p "test_*.py"` (paste tail)
- [ ] No benchmark/acceptance-bar/threshold changes; if changed, new version + ledger row linked below
- [ ] No proprietary RTL, VCD internals, keys, or credentials in the diff
- [ ] Docs updated where behavior changed (no duplicated prose — point at canonical homes)
- [ ] New dependencies are Apache-2.0/MIT/BSD-compatible (or justification attached)

## Gate impact

<!-- Which gates does this touch (A–E, C1–C5, cost)? "None" is an acceptable answer with reasoning. -->

## Ledger / issues

- Fixes/Relates: #NNN
- Evidence artifacts: <!-- paths to JSON/ledger entries -->
