# Architecture Status (P4-02)

> Canonical state record per P4–P7 plan §7.2. Labels: CURRENT / EXPERIMENTAL /
> FUTURE / EDUCATIONAL / SUPERSEDED. Rule: only CURRENT constrains implementation.

## Canonical version
- **Architecture version:** CPU-first verification platform (P4–P7 plan v1.0, 13-Oct-2026).
- **Canonical repo commit:** recorded at each release tag (see `git log`; this file is refreshed on phase transitions).
- **Frozen principles:** deterministic truth layer · LLM-proposes/evidence-disposes · model-agnostic layer · CPU-first, zero-GPU operation · ≤3 auto closure rounds, no silent Round 4 · human sign-off where required · no silent PASS · held-out qualification · training only on evidence.

## Document classification

| Document | Label | Note |
|---|---|---|
| P4–P7 plan v1.0 (13-Oct-2026 program record) + this file + `DEVELOPMENT_ROADMAP_P4_P7.md` | **CURRENT** | Direct implementation requirements |
| `AIQ-VeriClave_Architecture_Document_Fixed&FinalVersion1.0.md`, `ARCHITECTURE_DELTAS_V8.md` | **CURRENT** | Consolidated architecture reference |
| `DIAGRAMS.md` D41–D67+X2 (CPU-first supplement) | **CURRENT** | Matches P4 direction |
| `DIAGRAMS.md` D01–D40+X1 (review-era diagrams) | **EDUCATIONAL** | Background; BoN=5–8 era, pre-P0-minimal stance |
| `AIQ-VeriClave_CPU_First_*_ChatGTP.md` (strategy source) | **CURRENT** | Adopted program record |
| OpenRouter/OmniRoute-era model pool notes | **SUPERSEDED** | Free-tier gateway era closed |
| GRPO-as-roadmap-obligation readings | **SUPERSEDED** | GRPO is PHASE 6-conditional only |
| 80B-model-as-identity readings | **SUPERSEDED** | Generator-01 is replaceable |
| Future: learned 86M router, SFT/GRPO configs | **FUTURE** | Gated, not specified for build |
| Experiments A–F ladder, BoN ablation tables | **EXPERIMENTAL** | Valid within frozen benchmark tags only |

## Active interfaces (frozen)
`run_task()` result shape · ledger `to_json()` · eval `report` (+tokens/CPU) · `FailureEvent` stream · benchmark JSON configs (`compute.load_config`) · benchmark tags (`p3-pipeline-bench-v2` pattern; P4 tags frozen at P4-03).

## Active diagrams
P0 minimal system · compute adapter + backends · PHASE 0–7 roadmap · evidence chain · closure boundary (R0–R3 + escalation). Frozen others are reference-only.

## Deferred / experimental features
Learned router scorer · SFT/LoRA configs · GRPO harness · broad commercial-EDA support · dashboard UI beyond JSON reports. None may be cited as current capability.

## Reviewer / sign-off status
Maintainer review required for any reclassification. Reclassification itself is a signed ledger event.
