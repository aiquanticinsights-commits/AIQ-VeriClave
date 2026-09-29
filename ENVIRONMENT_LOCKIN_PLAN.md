# ---> DO NOT EDIT HERE; SOURCE: C:\Projects\ChipDesign\AIQ-VeriClave\ ---
# (mirror note: this file is the canonical environment lock-in for AIQ-VeriClave developers)

# AIQ-VeriClave — Environment Lock-in Plan (developer setup)

> Canonical platform: **OpenCode + GitHub + Ubuntu Linux + Python + Docker + Open-source Verification Stack + Local LLM (LMStudio) + Evidence Ledger + Optional Vivado Adapter**
> Verified: 2026-09-28. Status: locked. Gaps 1–4 closed 2026-09-29 (Docker image `aiq-vericlave:p0` 84 tests OK, CI workflow live). All versions below are measured, not assumed.

## 1. What lives where (do not duplicate)

| Function | Location | Verified version |
|---|---|---|
| Dev interface | OpenCode Desktop + CLI `1.18.33` | `AppData\Local\Programs\@opencode-aidesktop\OpenCode.exe`, `opencode --version` |
| Config | `C:\Users\satis\.config\opencode\opencode.jsonc` | model `freellmapi/auto:fast`, providers `freellmapi/omniroute/k3-local` |
| Skills | `~/.config/opencode/skills/` (Win + WSL) | `ai-verify-harness, ai-mutate, ai-localize, ai-close, ai-ensemble, ai-evidence` |
| Canonical OS | WSL2 `Ubuntu 26.04 LTS x86_64` | `wsl -d Ubuntu` |
| Truth layer (WSL) | `verilator / yosys / sby` | `5.032 / 0.52 / 0.68` |
| Python | WSL `3.14` system + venv `~/vericlave-venv` | `cocotb 2.1.0 / pytest 9.1.1` in venv only (PEP 668) |
| Local LLM | LMStudio server `:1234` | `gpt-oss-20b (Generator-01), deepseek-coder-6.7b, llama-3.1-8b, nomic-embed` |
| GitHub | `aiquanticinsights-commits/AIQ-VeriClave` (private) | `gh auth` as `aiquanticinsights-commits` |
| Contract | `python -m unittest discover -s . -p "test_*.py"` | 84 tests OK |
| Docker | `29.8.0` Desktop running + image `aiq-vericlave:p0` (Ubuntu 24.04, Verilator 5.020/Yosys 0.33 in-image, 84 tests OK) | `Dockerfile`, `requirements.txt`, `.dockerignore` |
| CI | `.github/workflows/vericlave.yml` (env → build → Verilator → Yosys → FRM/unittest → cocotb → SVA/sby non-blocking → ledger → artifact) | runs on push/PR to `main` |
| GitHub mgmt | Issues ON, Projects ON, Wiki OFF (intentional), Releases via `v0.1.0` | see `PUBLIC_PRIVATE_SPLIT.md` for mirror boundary |

Windows holds **no** EDA tools by design. WSL holds **no** OpenCode config duplication — skills are mirrored copies.

## 2. New-developer setup (15 min)

```powershell
# 1. Prereqs (Windows): LMStudio + Docker Desktop + gh + nodejs
lms ls                                   # must show gpt-oss-20b
lms server start                         # -> http://localhost:1234/v1/models
gh auth status                           # must be aiquanticinsights-commits
opencode --version                       # 1.18.33; if postinstall blocked:
npm install -g --allow-scripts=opencode-ai opencode-ai@1.18.33

# 2. Skills (this repo has no git worktree at ChipDesign level)
New-Item -ItemType Directory -Force -Path $env:USERPROFILE\.config\opencode\skills
Copy-Item -Recurse -Force C:\Projects\ChipDesign\AIQ-VeriClave\skills\* `
  -Destination $env:USERPROFILE\.config\opencode\skills\
wsl -d Ubuntu -- bash -lc 'mkdir -p ~/.config/opencode/skills && cp -r /mnt/c/Projects/ChipDesign/AIQ-VeriClave/skills/* ~/.config/opencode/skills/'

# 3. Clone (private)
gh repo clone aiquanticinsights-commits/AIQ-VeriClave
# -- OR if working from existing C:\Projects\ChipDesign\AIQ-VeriClave, git init there --

# 4. WSL venv (never pip install to system python)
wsl -d Ubuntu -- python3 -m venv /home/satis/vericlave-venv
wsl -d Ubuntu -- /home/satis/vericlave-venv/bin/pip install cocotb pytest

# 5. Verify (must all pass before any code change)
wsl -d Ubuntu -- /home/satis/vericlave-venv/bin/python -m unittest discover -s /mnt/c/Projects/ChipDesign/AIQ-VeriClave -p "test_*.py"
wsl -d Ubuntu -- sby --version; wsl -d Ubuntu -- yosys -V; wsl -d Ubuntu -- verilator --version
curl.exe -s http://localhost:1234/v1/models
```

## 3. Daily workflow

```text
lms server start  ->  wsl truth tools  ->  opencode (load ai-verify-harness)  ->
run P0 (BoN=3, deterministic router, Judge, <=3 closure)  ->  evidence ledger  ->
human sign-off  ->  git commit + push ->  GitHub Actions (Verilator/Yosys/FRM/cocotb/SVA/mutation/coverage/ledger)
```

- P0 defaults: `p0.py:P0_PROFILE` (`generators=["selected-open-llm"]` bake-off winner alias; P0-A starts on `gpt-oss-20b` local, P0-B bakes off the LMStudio trio, `bon=3`, `train=nothing`, `inference=lmstudio-local`, `compute=local-cpu`). No foundation model is pinned (frozen architecture 2026-09-29).
- P0-B freeze 2026-09-28 (`P0B_BASELINE.json`, `bakeoff.py`, wb_dma-v1, deterministic scorers): winner **llama-3.1-8b** (pass 0.50 vs 0.33, 46.3s vs 77.5s, 1006 vs 1490 tokens); runner-up deepseek-coder-6.7b; gpt-oss-20b skipped (12.23 GB RAM guardrail — recorded, never silent). Alias priors mirror the winner; recalibration gate: P0-B v2 at n>=20/kind.
- P0-D loop 2026-09-28 (`P0D_REPORT.json`, `p0d.py`, 9 tasks, BoN=3, temp 0.7): accuracy 0.444 (4/9), closure-success 0.375, 5 escalations, audit 1.0, chain valid. Localization/coverage close; SVA/mutant-kill escalate (8B codegen below C1/C2 — generator layer, verifiers caught all). Ablation: n=1/3/5 identical outcomes → verification gain per cost = 0, do NOT widen BoN (frozen §7). Prescription: constrained generation next, not a blindly bigger model.
- P0-D v2 same day (elitist closure: incumbents carried free, closes need approvals>=2): accuracy 0.556 (5/9), T2/T7 backfire fixed, T4 weak-plurality honestly reclassified as escalation. First real Gate-C data: 2822s / 13,798 tok / $0.0017 total ($0.00018/task nominal local — wall-clock ~5 min/task is the true budget). Closure rescued 0 failing tasks — regen still never improves; constrained generation remains the prescription. V1 archived at `P0D_REPORT_V1.json`.
- Skeleton v1 2026-09-29 (`P0D_SKELETON.json`, `skeletons.py`, same 5 failing tasks): 3/5 close (T2/T6/T7 rescued, round 2). T1 fails on TOOL boundary (Verilator lint accepts no `##` delays in any mode — needs formal adapter, P1); T9 fails on genuine model error (3'b100 twice, correctly rejected). Probe attribution also fixed 4 harness bugs (module-named lint files, synthetic `%Error` noise-line strip, `$rose/$fell` + backtick acceptance, nested-module rewrap, reject-without-lint). With real temperature diversity, n=1 drops closeable tasks while n=3 closes everything n=5 does — production stays at 3, now evidence-backed. Also found+fixed: `query()` never passed temperature (BoN had zero diversity until now).
- Item 1 formal adapter (`formal_adapter.py`, `formal/`, `FORMAL_WB_DMA.json`): vendor-neutral contract (prepare/execute/collect/parse/normalize/hashes/report); sby proves A_ACK + A_CYC on real `wb_dma` (BMC-20, ~1s); A_IRQ NOT_EXECUTED with measured reason (toolchain resolves no hierarchical refs — proven by `formal/demo/hier.sby` probe; `bind` ignored too). T1 closed IN-LOOP via past-form skeleton + per-property sby (`P0D_T1FORMAL.json`: `ack == $past(cyc&&stb)` PROVEN round 2). Characterized toolchain limits: no concurrent `|->`/`##` parsing in Yosys 0.52 (any mode) — properties use immediate-assert + `$past` style.
- Item 2 sim/FRM (`sim_frm.py`, `sim/tb_wb_dma.cpp`, `SIM_FRM_WB_DMA.json`): Python FRM (statement-level transliteration) + Verilator --cc C++ driver, same DSL, same cycle order - fixed vectors match EXACTLY (transfer 8/8, regfile 10/10). Known-benign warnings waived explicitly; all others still fail builds. LLM slot round (`SIM_FRM_LLM.json`): 0/2 + 0/1 closure - start-bit near-miss then label collapse; prescription: fewer slots per turn or labeled few-shot.
- Evidence per run: `RTL commit + spec commit + version + BoN + Verilator/Yosys/SVA/mutation + closure rounds + evidence/run_* + sign-off`.
- Never auto-merge `rtl-merge/sign-off/tapeout-release/repair-merge` — `policy.py:HUMAN_SIGNOFF_ACTIONS`.

## 4. Confidentiality (AIQI rule)

- Private repo = default. Public split (`framework/docs/benchmarks`) only after review.
- RTL/VCD/sim-logs/trajectories: local-only, tail of prompt, never cached. Cacheable: system prompts, specs (redacted), FRM templates, tool defs.
- Remote backends (`free-cloud/accelerated-external` in `compute.py:BACKENDS`) receive redacted prompts only.

## 5. Troubleshooting (hit during lock-in)

| Symptom | Fix |
|---|---|
| `opencode.exe is not compatible` | postinstall blocked: `npm install -g --allow-scripts=opencode-ai opencode-ai@1.18.33` |
| `externally-managed-environment (PEP 668)` | use `~/vericlave-venv`, never `--break-system-packages` |
| `lms: server is not running` | `lms server start`, check `:1234/v1/models` |
| `docker pipe not found` | start Docker Desktop; P0 does not need Docker |
| `not a git repository` at `C:\Projects\ChipDesign` | intentional — git lives in `AIQ-VeriClave/` only (vendor drops stay unversioned) |

## 6. LLM equivalence note (LMStudio vs llama.cpp/Ollama)

`dev_env.md` lists `llama.cpp` (core candidate) + `Ollama` (convenience). Per developer
approval 2026-09-28 this lock-in substitutes **LMStudio server (`:1234`, OpenAI-compatible)**
with `gpt-oss-20b` as Generator-01. Rationale: already installed, GGUF-local, zero duplicate
runtimes, same confidentiality posture (localhost, redacted-prefix only). Add `llama.cpp`
and/or `Ollama` only if a phase gate proves LMStudio insufficient (throughput, GGUF coverage,
or headless-server need). `p0.py:P0_PROFILE["inference"]` stays swappable — one-line change.

## 7. Version drift note

WSL reference (5.032/0.52/SBY 0.68) vs Docker image (5.020/0.33, sby pool-dependent) differ
by Ubuntu release. This is expected and caught by CI `*- --version` checks + the 84-test
contract — never assumed equal. Formal sign-off runs on WSL reference until the image pins SBY.

## 8. Next (not in lock-in)

Vivado/XSim adapter behind `sim_adapters.py` only. Held-out P0-C evaluation. PHASE 1 model bake-off.
