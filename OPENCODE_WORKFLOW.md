# Developing AIQ-VeriClave with OpenCode (adoption of "can I develop models using OpenCode?")

> Short answer: OpenCode does not train model weights itself (no GPU training
> stack — it is an agentic coding client), but it is the correct development
> environment for *everything around* the model: dataset pipelines, training
> configs/recipes, eval harnesses, experiment running and debugging, CI gates,
> docs, and release engineering. This file maps the AIQ-VeriClave blueprint and
> the `make ai-verify` pipeline onto concrete OpenCode usage.
>
> Source for OpenCode mechanics: https://opencode.ai/docs/skills/ and
> https://opencode.ai/docs/agents/ (verified Sep 2026).

## 1. Role split (what lives where)

| Layer | Owner | Notes |
|---|---|---|
| GPU training (SFT/GRPO runs) | Cluster scripts launched *from* OpenCode | OpenCode writes/monitors `train/` configs, submits jobs, parses logs — compute lives on the cluster, never in the agent |
| Dataset curation (T0–T3) | OpenCode Build sessions + `ai-mutate` skill | BugGen mutants, VCD slicing, traceability linkage, license checks |
| Eval + gates (§6) | `eval_harness.py` + `ai-verify-harness` skill | Deterministic, CPU-only, CI-runnable |
| Ensemble routing | `router.py` + `ai-ensemble` skill | Heuristic now, learned scorer at PHASE 5 |
| Closure loop ops | `ai-localize`, `ai-close` skills | Bounded rounds, human sign-off preserved |
| Release engineering | OpenCode Build (versions, eval cards, GGUF/Ollama packaging) | Same flow as any software release |

## 2. Skills (this directory)

| Skill dir | Loaded as | Job |
|---|---|---|
| `skills/ai-verify-harness/` | `ai-verify-harness` | run `make ai-verify` targets, read JSON reports, enforce §A2 gates |
| `skills/ai-mutate/` | `ai-mutate` | BugGen-style mutant campaigns + blind-spot reports |
| `skills/ai-localize/` | `ai-localize` | BluesFL-style VCD-sliced fault localization runs |
| `skills/ai-close/` | `ai-close` | GoGoTB-style coverage closure + sign-off ledger |
| `skills/ai-ensemble/` | `ai-ensemble` | router/eval-harness runs, winner analysis, cost tracking |
| `skills/ai-evidence/` | `ai-evidence` | ledger writes, chain/audit checks, sign-off gating |

Each `SKILL.md` carries valid OpenCode frontmatter (`name` = directory name,
lowercase-hyphen; `description` 1–1024 chars).

## 3. Installation (important: this repo has no git worktree)

OpenCode discovers project skills by walking up to the git worktree.
`C:\Projects\ChipDesign` is **not** a git repo, so copy the skills to the
global location where they always load:

```powershell
Copy-Item -Recurse C:\Projects\ChipDesign\AIQ-VeriClave\skills\* `
  -Destination $env:USERPROFILE\.config\opencode\skills\
```

Verify inside OpenCode: the `skill` tool description should list
`ai-verify-harness`, `ai-mutate`, `ai-localize`, `ai-close`, `ai-ensemble`.
Invoke with `skill({ name: "ai-mutate" })`. (Alternative: `git init` the
ChipDesign tree then use `AIQ-VeriClave/.opencode/skills/` — not recommended
until the tree's huge vendor drops are git-ignored.)

## 4. Recommended agent↔model mapping (cost control)

Per-agent models in `opencode.json` (see /docs/agents — `model` overrides
per agent; cheap models for mechanical lanes, strong ones for judgment):

| Agent lane | Suggested model class | Why |
|---|---|---|
| explore (scouting RTL/VCD inventory) | cheap/fast (Flash-class, MiniMax/MiMo-class) | read-only volume |
| build/verify-loop execution | Qwen3-Coder-Next-class (broad, cheap-active) | long tool loops, 256K ctx |
| judge/repair-review (CorrectBench role) | strongest available (frontier or 30B+ reasoning) | precision over cost; still ≤$0.50/task-class |
| general (multi-workstream delegation) | mid-tier | Task-tool fan-out |

## 5. Session recipes (copy-paste prompts)

**Nightly gate:** "Load ai-verify-harness. Run the full `make ai-verify`
ladder on `wb_dma`, compare against §A2 gates, update the cost ledger, and
report pass/fail per gate. Do not modify RTL."
**Mutant campaign:** "Load ai-mutate. Run a 200-bug BugGen-style campaign on
`wb_ai_accel` with Verilator as oracle. Check in the mutation cache and the
blind-spot report; stop if functional accuracy <90%."
**Localize:** "Load ai-localize. Top-1 localize these 50 seeded bugs from
VCD slices only (never full dumps). Report Top-1 rate and $/bug."
**Close:** "Load ai-close. Drive GoGoTB-style closure on the pilot IP to
≥+15pp functional; every residual gap gets a root-cause disposition or the
run fails."
**Ensemble eval:** "Load ai-ensemble. Run `eval_harness.py` (100 tasks),
report system_accuracy by kind plus avg_rounds; flag any kind below its §6 band."

## 6. What OpenCode explicitly does NOT do here

- No weight training inside sessions; no GPU scheduling (cluster owns that).
- No auto-merge of repair diffs (human sign preserved — §A2/WS6).
- No confidential RTL to cloud endpoints (local models / redacted prompts;
  free-tier training-use caveat from the Zen docs applies).
