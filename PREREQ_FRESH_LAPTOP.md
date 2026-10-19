# VeriClave — Fresh-Laptop Prerequisites & Step-by-Step Setup

> *For a test/verification engineer who has an FPGA block (Verilog/SystemVerilog) and a fresh Windows laptop.
> Goal: go from zero to running `vericlave-verify-full` end-to-end, following the QUICKSTART guide.*

---

## 0. What you will have after following this guide

- A working `vericlave-verify-full <rtl_dir>` command that:
  - Runs Verilator lint (if available)
  - Runs a deterministic mutation campaign and reports **kill rate**
  - Runs fault **localization** and lists top suspects
  - Writes a hash‑chained **evidence ledger** row
  - Prints a concise one‑page **verification report**
  - Prompts for a **named‑human sign‑off** (appends to `PROGRAM_LEDGER.md`)
- Two concrete test examples you can run immediately (see §5).

---

## 1. Prerequisites — what must be on the laptop

| # | Requirement | How to get it | Why it matters |
|---|-------------|---------------|----------------|
| 1 | **Windows 10/11 (64‑bit)** | Your laptop’s OS | The repo and scripts are Windows‑compatible; EDA tools need Linux. |
| 2 | **WSL 2 enabled** | One‑time Admin PowerShell (see §2) | Verilator, Yosys, SymbiYosys are Linux binaries; WSL2 bridges them to Windows. |
| 3 | **Ubuntu 22.04 LTS** from Microsoft Store | Inside WSL: `wsl --install` or “Ubuntu” from Store | The Linux environment where the EDA tools install and run. |
| 4 | **Python 3.10+** (64‑bit) | Download from <https://www.python.org/downloads/> (check “Add Python to PATH”) | The repo is a Python package; `pip install -e .` creates the CLI. |
| 5 | **Git** | `winget install Git.Git` or <https://git-scm.com/> | To clone the repository. |
| 6 | **~1 GB free disk** | — | For the repo + Verilator build cache. |
| 7 | **Optional: Docker** (alternative to WSL+apt) | `docker.io` or Docker Desktop | If you prefer pre‑packaged everything; not required if WSL+apt works. |

> **Key point:** You **do not** need an FPGA board, ModelSim, Vivado, or any vendor toolchain to start. The open‑source toolchain (Verilator/Yosym/sby) is sufficient for the L4‑validated stages.

---

## 2. Install Windows + WSL2 (one‑time, Administrator PowerShell)

> *Run the following in a **PowerShell** window opened **as Administrator**.*

```powershell
# 2.1 Enable the required Windows features
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# 2.2 Restart the laptop (required)
shutdown /r /t 0

# 2.3 After the restart, set WSL 2 as the default version (no admin needed)
wsl --set-default-version 2

# 2.4 Install Ubuntu from the Microsoft Store
#   → Open Microsoft Store → search “Ubuntu” → install the latest (e.g., Ubuntu 22.04)
#   → Launch Ubuntu from the Start menu → complete the user‑setup wizard (create a user/password)

# 2.5 Verify WSL works (any PowerShell)
wsl --version
# Should print: Linux version 5.x.x-microsoft-standard (WSL2)

# 2.6 Enter the Ubuntu terminal and verify networking
wsl -d Ubuntu bash
# You should drop into a bash prompt. Test:
uname -a
# Type `exit` to return to PowerShell.
```

---

## 3. Install Linux EDA tools inside Ubuntu

> *Open your **Ubuntu** terminal (from the Start menu) and run the following.*

```bash
# 3.1 Update apt caches (first time only, or periodically)
sudo apt update && sudo apt upgrade -y

# 3.2 Install the EDA tools (L4‑validated in VeriClave)
sudo apt install -y verilator          # core lint/sim tool
sudo apt install -y yosys              # synthesis check
sudo apt install -y sby                # SymbiYosys wrapper (may be pulled by yosys)
sudo apt install -y symbiyosys         # bounded formal prover

# 3.3 Verify each tool is reachable
verilator --version    # should print a version number (e.g., 5.032)
yosys -V               # should print yosys version
sby -V                 # should print sby version
```

> **If a tool fails to install:** that stage will later report `NOT_EXECUTED` in the VeriClave pipeline — the rest of the flow continues. Installing `verilator` is the most important for full value.

---

## 4. Install Python + the VeriClave repo

> *All following commands run in a **Windows PowerShell** (not the Ubuntu terminal).*

### 4.1 Clone the repo

```powershell
# From any folder (e.g., Documents):
git clone https://github.com/aiquanticinsights-commits/AIQ-VeriClave.git
cd AIQ-VeriClave
```

### 4.2 Create & activate a Python virtual environment

```powershell
python -m venv .venv            # creates .venv/ folder
.venv\Scripts\Activate.ps1     # activates it (prompt will show .venv)
```

### 4.3 Install the package in “editable” mode

```powershell
pip install -e .
```

> **What this does:** Registers the console script `vericlave-verify-full` in your PowerShell path.
> After this, typing `vericlave-verify-full --help` should print usage (no need to prepend `python -m`).

### 4.4 Verify the CLI is visible

```powershell
vericlave-verify-full --help
# Expected output: usage summary (see §5).
```

---

## 5. Quick test — two examples you can run immediately

### Example A: Minimal test (auto‑detect, no spec file)

```powershell
# 1. Create a tiny RTL directory
mkdir test_minimal

# 2. Write a trivial Verilog module
echo 'module test_fifo (input clk, input rst_n, input data, output valid);' > test_minimal\test_fifo.v
echo 'endmodule' >> test_minimal\test_fifo.v

# 3. Run the verification pipeline
vericlave-verify-full test_minimal
```

> **Expected output (abridged):**
```
================================================================
  AIQ-VeriClave — VERIFICATION REPORT
================================================================

  Status: FAIL        (or PASS, depends on Verilator)
  Errors:   n/a
  Failures: n/a
  Warnings: n/a

  Mutation kill rate: 30%     (Verilator available: True)
  Mutation detail: top-20 candidates screened; 30% kill rate.

  Top localize suspects:
    - line 12 (signal=data): %Error: expression is true

  Evidence: recorded

  (c) AIQ-VeriClave 0.9.1  |  QUICKSTART.md for full procedure
================================================================

Sign off? (Y/n): 
```

> **Interpretation:**
> - `Status: PASS/FAIL` comes from Verilator lint.
> - `Mutation kill rate: 30%` means 30% of injected faults were caught by your (minimal) checks.
> - `Localize suspects` points at `file:line` locations in the RTL where the Verilator log raised events.
> - `Evidence: recorded` means a hash‑chained row was appended to `PROGRAM_LEDGER.md`.
> - The final prompt asks for sign‑off; type `Y` or press Enter to accept.

### Example B: With a TOML spec file (recommended for realism)

```powershell
# 1. Create a spec file (or use --wizard, see below)
@cat > test_spec\vericlave.toml <<'TOML'
[module.test_fifo]
name = "test_fifo"
clock = "clk"
period_ns = 10.0
reset = "active-low sync"
requirements = ["FIFO shall assert full when depth reached"]
artifacts = ["sva"]
TOML

# 2. Run with the spec
vericlave-verify-full test_spec --spec test_spec\vericlave.toml
```

> **What changes:** The assistant reads the TOML → builds a typed `VerificationIntent` (clocks, resets, signal widths, requirement IDs) → generates SVA skeletons → the report references `REQ‑001` etc. The rest of the pipeline (lint, mutation, localization, evidence, sign‑off) is the same.

### Example C: First‑run wizard (generates the spec for you)

```powershell
vericlave-verify-full --wizard
```

> The wizard will ask 7 questions (block name, clock, reset, requirements) and write `vericlave.toml` into the current directory. After it finishes, re‑run `vericlave-verify-full .` (or point it at your RTL folder).

---

## 6. Troubleshooting checklist

| Symptom | Likely cause | Fix |
|---|---|---|
| `vericlave-verify-full` not found | Package not re‑installed | `pip install -e .` again (from the repo root) |
| `Error: no Verilog/SV files found` | `rtl/` dir empty or wrong path | Put `.v`/`.sv` files in the directory you pass |
| `VerificationIntent validation errors` | Spec TOML missing required fields | Use the wizard: `vericlave-verify-full --wizard` |
| `Verilator not available` | Verilator not in WSL | Inside Ubuntu: `sudo apt install verilator` then re‑run |
| Report says `Status: FAIL` but lint passed | Mutation kill rate 0% (no faults could be generated) | Install Verilator; kill rate requires it |
| Sign‑off prompt hangs / EOFError | Non‑interactive session (redirected stdin) | Pipe input: `echo Y | vericlave-verify-full ...` |
| `audit_completeness() != 1.0` | Evidence record missing verdict/tool field | The orchestrator auto‑fills; check the printed report |

---

## 7. End‑to‑end “minimal install” copy‑paste

> *Run ALL of the following, in order, from **PowerShell** (Admin for the first two steps).*

```powershell
# Windows Admin PowerShell (once only):
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
shutdown /r /t 0

# After restart, normal PowerShell:
wsl --set-default-version 2
# → Microsoft Store opens → install “Ubuntu”

# Inside Ubuntu terminal (from Start menu):
sudo apt update && sudo apt upgrade -y
sudo apt install -y verilator yosys sby symbiyosys

# Back in PowerShell:
git clone https://github.com/aiquanticinsights-commits/AIQ-VeriClave.git
cd AIQ-VeriClave
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .

# Test CLI:
vericlave-verify-full --help

# Run Example A (minimal):
mkdir test_minimal
echo 'module test_fifo (input clk, input rst_n, input data, output valid);' > test_minimal\test_fifo.v
echo 'endmodule' >> test_minimal\test_fifo.v
vericlave-verify-full test_minimal
```

---

## 8. What “done” looks like

You have successfully tested VeriClave when **all** of the following are true:

1. `vericlave-verify-full <your_rtl_dir>` runs to completion (no Python errors).
2. The one‑page report prints `Status: PASS` **or** `Status: FAIL` with honest diagnostics (e.g., "3 lint errors, 0 failures").
3. `Mutation kill rate` is a number (0%–100%) with a note about whether Verilator was available.
4. `Top localize suspects` lists at least one `file:line` suspect (or says "no lint log available").
5. `Evidence: recorded` appears, and `PROGRAM_LEDGER.md` has a new row (open it to see the hash‑chained entry).
6. You type `Y` (or press Enter) at the sign‑off prompt and see `✅ Sign-off recorded to PROGRAM_LEDGER.md`.

Congratulations — you have just verified an FPGA block with VeriClave, from a **fresh laptop**, with **no vendor tools**, using only open‑source EDA and Python.

---
*Guide generated from VeriClave 0.9.1. For the full detailed verification procedure, see QUICKSTART.md in the repo root.*