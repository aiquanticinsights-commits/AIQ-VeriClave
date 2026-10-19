# VeriClave Quick-Start Guide — Step-by-Step

> **Goal:** A test engineer with an FPGA block (Verilog/SV) can go from "zero" to "verified report + evidence ledger" in **one command**, using the VeriClave platform you just installed.

> **What this guide covers:**
> 1. Install / environment check (if not done yet)
> 2. Prepare your RTL + spec (or use the auto-detect fallback)
> 3. Run the one-command verification pipeline
> 4. Read the report + sign off
> 5. Two concrete test examples you can run today

---

## 0. Reality check (read first)

VeriClave is **not** a one-click "magic wand" that instantly proves any design — it runs **Verilator** (lint/sim), **Yosys** (synth-check), a **mutation campaign**, and **fault localization**, then records everything in a hash-chained evidence ledger.

If you already have **Verilator** installed (via `wsl verilator --version`), the pipeline will run automatically. If not, the assistant will report `NOT_EXECUTED` honestly and skip those stages.

---

## 1. Install & verify environment (one-time)

```powershell
# From an Admin PowerShell, from the repo root:
git clone https://github.com/aiquanticinsights-commits/AIQ-VeriClave.git
cd AIQ-VeriClave
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

**Verify Verilator reachable** (needed for the open-toolchain path):

```powershell
# Inside WSL (or if native on Linux):
wsl verilator --version
# Should print something like Verilator version 5.032

# Or on Windows with native Verilator:
verilator --version
```

If Verilator is **not** available, the pipeline will still run but report `kill_rate: 0%` and `NOT_EXECUTED` for lint stages. Install Verilator to get full value.

**Docker alternative** (skip venv, everything pre-bundled):

```bash
docker build -t aiq-vericlave .
docker run --rm -v $(pwd):/work aiq-vericlave python -m verify /work/test_rtl
```

---

## 2. Prepare your project directory

Create a directory with your RTL and (optionally) a spec file. The **lazy path** lets the assistant auto-detect; the **explicit path** uses a TOML spec.

### 2A. Lazy: auto-detect from RTL files

```
my_project/
  rtl/          <- put your .v or .sv files here
```

### 2B. Explicit: write a TOML spec file (recommended for reproducibility)

```toml
# my_project/vericlave.toml
[module.my_fifo]
name = "my_fifo"
clock = "clk"
period_ns = 10.0
reset = "active-low sync"
requirements = [
  "FIFO shall assert full when depth reached",
  "wr_en ignored while full asserted",
  "full deasserts within one cycle of a read when not refilled"
]
artifacts = ["sva", "checker"]   # generate SVA + checker skeletons
```

**Quick hand-written spec (minimum):**

```toml
[module.my_fifo]
name = "my_fifo"
clock = "clk"
period_ns = 10.0
reset = "active-low sync"
requirements = ["FIFO shall assert full when depth reached"]
```

---

## 3. Run the verification pipeline

From the repo root, with your project directory ready:

### 3A. Using the auto-detect path (no spec file needed)

```powershell
vericlave-verify-full my_project\rtl
```

### 3B. Using an explicit spec file

```powershell
vericlave-verify-full my_project\rtl --spec my_project\vericlave.toml
```

### 3C. First-run wizard (generates the spec for you)

```powershell
vericlave-verify-full my_project\rtl --wizard
```

> The wizard will ask 7 questions (block name, clock, reset, requirements) and write `vericlave.toml` for you. Then re-run step 3A or 3B.

---

## 4. Read the report + sign off

The pipeline prints a **one-page report** and then prompts for sign-off. Example output (abridged):

```
================================================================
  AIQ-VeriClave — VERIFICATION REPORT
================================================================

  Status: PASS
  Errors:   0
  Failures: 0
  Warnings: 2

  Mutation kill rate: 30%
  Mutation detail: top-20 candidates screened; 30% kill rate (Verilator available: True).

  Top localize suspects:
    - line 12 (signal=data): %Error: expression is true
    - line 23 (signal=valid): %Warning: simultaneous assignment

  Evidence: recorded

  (c) AIQ-VeriClave 0.9.1  |  BYO_RTL_GUIDE.md for full procedure
================================================================

Sign off? (Y/n): 
```

**To accept the sign-off:** just type `Y` or press Enter. This appends a row to `PROGRAM_LEDGER.md` with the engineer's name (from `%USER%`).

**To skip sign-off:** type `n` or `N`.

---

## 5. Two concrete test examples

### Example 1: Minimal test (auto-detect, no spec file)

```powershell
# 1. Create a tiny test RTL (you just did this):
mkdir test_minimal
echo 'module test_fifo (input clk, input rst_n, input data, output valid);' > test_minimal\test_fifo.v
echo 'endmodule' >> test_minimal\test_fifo.v

# 2. Run verification (auto-detects signals, builds minimal intent):
vericlave-verify-full test_minimal

# 3. Expected output (your RTL is very small, so mutation kill rate reports N/A,
#    lint will run, and the report will show Status: PASS or FAIL depending on Verilator):
...
```

### Example 2: Semi-detailed test (with TOML spec)

```powershell
# 1. Create a slightly more realistic RTL + spec:
mkdir test_fifo_full
# Verilog: a tiny FIFO with reset and data width
@cat > test_fifo_full\fifo.v <<'EOF'
module fifo #(parameter W=8) (
    input clk, reset, wr, rd,
    input [W-1:0] d,
    output reg full, empty,
    output [W-1:0] q
);
    reg [W-1:0] mem [0:15];
    reg [3:0] wptr, rptr;
    always @(posedge clk) begin
        if (reset) begin wptr <= 0; rptr <= 0; end
        if (wr && !full) begin mem[wptr] <= d; wptr <= wptr + 1; end
        if (rd && !empty) begin q <= mem[rptr]; rptr <= rptr + 1; end
        full <= (wptr == rptr + 16) || (wptr == 0 && rptr == 15);
        empty <= (wptr == rptr) || (wptr == 0 && rptr == 15);
    end
endmodule
EOF

# TOML spec (feeds intent, gives the assistant real signals/clock/reset):
@cat > test_fifo_full\vericlave.toml <<'TOML'
[module.fifo]
name = "fifo"
clock = "clk"
period_ns = 10.0
reset = "active-low sync"
requirements = [
  "FIFO shall not overflow when wr & !full",
  "FIFO shall not underflow when rd & !empty",
  "Output q valid when !empty]"
artifacts = ["sva", "checker"]
TOML

# 2. Run:
vericlave-verify-full test_fifo_full --spec test_fifo_full\vericlave.toml

# 3. Expected report:
#   - Verilator lint on the FIFO (will find no %Error if syntax OK)
#   - Mutation kill rate ~30% (because the assistant injects ~30 plausible faults)
#   - Localize top suspects (file:line hints from Verilator log)
#   - Evidence ledger row auto-recorded
#   - Sign-off prompt at the end
```

---

## 6. Troubleshooting checklist

| Symptom | Likely cause | Fix |
|---|---|---|
| `vericlave-verify-full` not found | Package not re-installed after `verify.py` edit | `pip install -e .` again |
| `Error: no Verilog/SV files found` | `rtl/` dir empty or wrong path | Put `.v`/`.sv` files in `rtl/` |
| `VerificationIntent validation errors` | Spec TOML missing required fields | Use the wizard: `vericlave-verify-full --wizard` |
| `Verilator not available` | Verilator not in PATH/WSL | `wsl verilator --version` or install Verilator |
| Report says `Status: FAIL` but lint passed | Mutation kill rate 0% (no faults could be generated) | Install Verilator; the kill rate requires it |
| Sign-off prompt hangs / EOFError | Non-interactive session (redirected stdin) | Pass `--non-interactive` or pipe echo: `echo Y | vericlave-verify-full ...` |
| `audit_completeness() != 1.0` | Evidence record missing verdict or tool field | The orchestrator auto-fills; check the printed report |

---

## 7. What the pipeline actually does (under the hood)

If you're curious, here's the exact sequence for each `vericlave-verify-full` run:

1. **Scan** `rtl/` for `.v`/`.sv` files.
2. **If spec given:** read TOML → build `VerificationIntent` (widths, clocks, reset, requirements). **If no spec:** auto-detect signals/clocks from RTL text (fallback only).
3. **Verilator lint:** `wsl verilator --lint-only -Wall <first_rtl_file>` → normalized failure events → `summary: {errors, failures, warnings, total}`.
4. **Mutation campaign:** generate top-20 deterministic mutants (seed=42) of your RTL, re-run a lightweight lint check, compute **kill rate** (fraction of mutants your checks catch).
5. **Fault localization:** run `localize()` on the Verilator log → ranked `file:line` suspects + recurring identifier signals.
6. **Evidence ledger:** append a hash-chained `EvidenceRecord` with `requirement_id`, `artifact`, `checks: {lint, mutation}`, `verdict: PASS/FAIL`, `tool: verilator`, `signed_by: <your username>`.
7. **One-page report:** concise text table (status, errors, mutation kill rate, top suspects, evidence).
8. **Sign-off:** plain-English Agree/Disagree; if Agree, append to `PROGRAM_LEDGER.md`.

---

## 🎯 You're done when

- The one-page report prints `Status: PASS` (or FAIL with honest diagnostics).
- `audit_completeness()` is `1.0` (check `ledger verify_chain()` in the Python REPL if you want to verify).
- A named-human sign-off row exists in `PROGRAM_LEDGER.md`.
- You can read the report and say "my block has a 30% mutation kill rate, and the top suspect is at `fifo.v:42`" — that's the actionable verification output.

---

**Need help?** Check the troubleshooting table, re-run with `--wizard`, or ensure Verilator is reachable. The pipeline is deliberately verbose so you always know what stage succeeded/failed.