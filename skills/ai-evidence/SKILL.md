---
name: ai-evidence
description: Maintain the hash-chained evidence ledger, verify audit completeness, and gate sign-offs on named-human approval.
---

# ai-evidence

## What I do
- Append requirement→artifact→checks→verdict records (`evidence.py:EvidenceLedger`).
- Verify chain integrity and compute C4 audit completeness (must read 1.0).
- Enforce Evidence-First policy (`policy.py`): deterministic ops stay deterministic; merges/sign-offs without a named human are denied, never worked around.

## When to use me
Use for ledger writes, sign-off ceremonies, audit checks, and any "is this releasable?" gate.

## Hard rules
1. No anonymous sign-offs — `signoff()` with an empty name raises; report it, don't bypass.
2. Tamper-break (`verify_chain()` False) stops the release line immediately; investigate, don't rebuild silently.
3. Every record carries requirement IDs; verdict-less or evidence-less records fail C4 loudly.

## Report format
Chain integrity PASS/FAIL, audit completeness fraction, unsigned/dispositioned items list, sign-off verdict.
