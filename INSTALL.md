# Install — AIQ-VeriClave (CPU-only, no GPU required)

## Option A — from source (2 minutes, any OS with Python 3.10+)

```powershell
git clone https://github.com/aiquanticinsights-commits/AIQ-VeriClave.git
cd AIQ-VeriClave
python -m venv .venv
# Windows:
.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate
pip install -r requirements.txt   # cocotb, pytest, pyyaml (optional but recommended)
```

Verify (stdlib-only contract — works with zero dependencies installed):

```powershell
python -m unittest test_router test_platform test_rewards test_datasets test_p4_bench test_p4_heldout
python eval_harness.py            # 100-task mock report with token/USD ledger
python p5_rerun.py                # independent re-run vs committed baseline
```

Full suite: `python -m unittest discover -s . -p "test_*.py"` (565 tests,
~80 s on a dev host; T-02 fixed — toolkit probes are now bounded so the suite
never stalls).

## Option B — Docker (pinned, reproducible)

```bash
docker build -t aiq-vericlave .
docker run --rm aiq-vericlave     # runs the full contract suite as CMD
```

Image: Ubuntu 24.04 + Verilator + Yosys + sby (best-effort) + venv.
sby missing from some apt pools is non-blocking by design.

## Option C — WSL2 (Windows, canonical Linux path)

```powershell
wsl -d Ubuntu
# inside WSL: same as Option A (Linux). SBY 0.68 reference runner lives here.
```

## Offline / air-gap
Core contract (`router`, `rewards`, `evidence`, `policy`, `closure`, `trace`,
`diagnostics`, adapters-parsers, registries) is **stdlib-only** — no `pip
install` needed to run the fast subsets. Only `cocotb`/`pytest`/`pyyaml`
extend it, and EDA tools (Verilator/Yosys/sby) degrade to recorded
UNAVAILABLE, never to silent skips.

## Evidence retention
Runs emit JSON evidence (`P5_EXECUTION.json`, `P5_RERUN.json`, gate verdicts).
Keep them versioned in git; partial/interrupted outputs stay git-ignored per
`.gitignore` (`*_PARTIAL*.json`, `*.vcd`, `*.log`). Retention default: keep
every signed gate artifact; prune scratch on release tags.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `discover` hangs | run focused subsets (above); see T-02 |
| `sby`/Verilator missing | expected on bare hosts; recorded UNAVAILABLE, non-blocking |
| `pip install` blocked (PEP 668) | always use a venv, never `--break-system-packages` |
| CRLF warnings on Windows git | harmless (repo normalizes on commit) |
