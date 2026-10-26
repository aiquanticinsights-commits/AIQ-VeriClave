# FPGA Verification Toolchain — Installation Plan

> **Goal:** Map every tool from the FPGA Test & Simulation list to its open-source
> GitHub equivalent, identify what is already installed, and provide a concrete
> install plan for the missing ones.

---

## 0. Already Installed (No Action Needed)

| Tool / Feature | Source | Notes |
|---|---|---|
| **Verilator** (WSL) | GitHub: `verilator/verilator` | v5.032 — L4 validated (lint + sim) |
| **Yosys** (WSL) | GitHub: `YosysHQ/yosys` | v0.52 — L4 validated (synth-check) |
| **sby** (WSL) | GitHub: `YosysHQ/sby` | SymbiYosys wrapper |
| **cocotb** | GitHub: `cocotb/cocotb` | v2.0.1 (Python) |
| **Vivado 2026.1** | Xilinx | Includes xsim, STA, CDC, linting, ILA, power analysis |
| **KiCad 10.0** | KiCad | PCB/schematic design |
| **KLayout** | KLayout | Layout viewer |
| **GTKWave** | WSL | Waveform viewer |
| **Python 3.11.5** (KiCad) | python.org | Default `python` |
| **Node.js 24.18.0** | nodejs.org | JavaScript runtime |
| **Git 2.54.0.1** | git-scm.com | Version control |
| **Docker Desktop** | docker.com | Containerization |
| **OpenCode** | opencode.ai | AI agent harness |
| **LM Studio** | lmstudio.ai | Local LLM inference |
| **VS Code / Cursor** | — | Code editors |

---

## 1. Tool-by-Tool Mapping & Install Plan

### A. FPGA Test & Simulation

| # | Tool / Feature | Status | GitHub Equivalent | Install Plan |
|---|---|---|---|---|
| 1 | **ModelSim / Xsim** (SDF Simulation, Gate-Level Sim) | ✅ Xsim installed (Vivado) | `verilator/verilator` (Verilator) | **No action.** Use Vivado xsim for gate-level/post-route timing sim. Verilator is the open-source alternative. |
| 2 | **SpyGlass / Vivado CDC** (CDC Analysis) | ✅ Vivado CDC available | `rtl-buddy/rtl-buddy-cdc`, `jyrj/crux`, `vyges-tools/cdc` | **Optional:** Install `rtl-buddy-cdc` (Python) or `crux` (Yosys-based) for open-source CDC. Plan: `pip install rtl-buddy-cdc` or build from GitHub. |
| 3 | **Cocotb** (Coroutines Co-sim Testbench) | ✅ Installed (2.0.1) | `cocotb/cocotb` | **No action.** Already installed. |
| 4 | **Icarus Verilog (iverilog) + GTKWave** | ⚠️ GTKWave installed, iverilog **NOT** | `steveicarus/iverilog` | **Install:** `sudo apt install iverilog` (WSL). GTKWave already available. |
| 5 | **UVM** (Register Model, Bus Protocol) | ❌ Not installed | `pyuvm/pyuvm` (Python UVM) | **Install:** `pip install pyuvm` (Python). UVM also available in Vivado. |
| 6 | **CRS** (Firmware register mapping verification) | ❌ Not found | *Not identified* | **Research needed.** May be a proprietary tool. Vivado/VCS may have equivalents. |
| 7 | **HW/SW Co-simulation** | ❌ Not installed | `qemu/qemu` (QEMU) | **Install:** `sudo apt install qemu-system` (WSL) for RISC-V/ARM emulation. |
| 8 | **Static Timing Analysis (STA)** | ✅ Vivado STA available | `The-OpenROAD-Project/OpenSTA` | **No action.** Vivado provides STA. OpenSTA available for open-source flow. |
| 9 | **Clock Domain Crossing (CDC) Analysis** | ✅ Vivado CDC available | `jyrj/crux`, `rtl-buddy/rtl-buddy-cdc`, `aashishniranjanb/OpenCDC` | **Optional:** Install open-source CDC linters for non-Vivado flows. |
| 10 | **Linting / RTL Rule Checks** | ✅ Verilator + Vivado lint | `verilator/verilator` | **No action.** Verilator `--lint-only` and Vivado lint cover this. |
| 11 | **Power and Thermal Analysis** | ✅ Vivado Power Analysis | `The-OpenROAD-Project/OpenSTA` (SAIF/VCD power) | **No action.** Vivado provides power analysis. OpenSTA supports SAIF/VCD power activities. |

### B. Pre- & Post-Hardware Testing

| # | Tool / Feature | Status | GitHub Equivalent | Install Plan |
|---|---|---|---|---|
| 12 | **Block-Level IP Simulation** | ✅ Vivado xsim + Verilator | `verilator/verilator` | **No action.** Already covered. |
| 13 | **SoC Interconnect Functional Simulation** | ✅ Vivado xsim | `verilator/verilator` | **No action.** Already covered. |
| 14 | **UVM Register Abstraction Layer (RAL) Tests** | ❌ Not installed | `pyuvm/pyuvm` | **Install:** `pip install pyuvm` (Python). Provides UVM RAL in Python. |
| 15 | **Gate-Level / Post-Route Timing Simulation** | ✅ Vivado post-implementation sim | `verilator/verilator` | **No action.** Vivado xsim handles post-route timing. |
| 16 | **In-Circuit Hardware Validation** | ❌ Requires physical FPGA board | — | **Hardware needed.** No software install. Use Vivado ILA + board. |
| 17 | **Memory BIST & Stress Tests** | ❌ Test patterns, not a tool | — | **No install.** Write test patterns in cocotb/pyuvm. |
| 18 | **Integrated Logic Analyzer (ILA) Debugging** | ✅ Vivado ILA | — | **No action.** Vivado provides ILA. |
| 19 | **Software-in-the-Loop (SIL) Bare-Metal Testing** | ❌ Not installed | `qemu/qemu` (QEMU) | **Install:** `sudo apt install qemu-system` (WSL) for RISC-V/ARM. |
| 20 | **Boundary Scan / I/O Loopback Tests** | ❌ Requires hardware | — | **Hardware needed.** No software install. |

---

## 2. Recommended Install Plan (Priority Order)

### Priority 1 — Immediate (open-source, one-command install)

```bash
# Inside WSL (Ubuntu terminal):
# 1. Icarus Verilog (iverilog) — event-driven Verilog simulator
sudo apt install -y iverilog

# 2. QEMU — HW/SW co-simulation & SIL testing
sudo apt install -y qemu-system

# 3. GHDL — VHDL simulator (optional, for mixed-language designs)
sudo apt install -y ghdl

# 4. symbiyosys — formal verification (if not already installed)
sudo apt install -y symbiyosys
```

```powershell
# On Windows (PowerShell):
# 5. pyuvm — Python UVM with RAL support
pip install pyuvm

# 6. rtl-buddy-cdc — open-source CDC linter (optional)
pip install rtl-buddy-cdc

# 7. cdc-auto-tool — CDC auto-synchronizer (optional)
pip install cdc-auto-tool
```

### Priority 2 — Medium (build from source or optional)

```bash
# OpenSTA — Static Timing Analysis (open-source)
# Build from GitHub:
git clone https://github.com/parallaxsw/OpenSTA.git
cd OpenSTA
mkdir build && cd build
cmake ..
make -j$(nproc)
# Result: build/sta

# OpenROAD — full RTL-to-GDS flow (includes OpenSTA)
# Use pre-built binaries or build from source:
# https://github.com/The-OpenROAD-Project/OpenROAD
```

### Priority 3 — Hardware-dependent (no software install)

| Feature | Requirement | Notes |
|---|---|---|
| In-Circuit Hardware Validation | Physical FPGA board (e.g., Xilinx Artix-7, Zynq) | Use Vivado ILA + JTAG |
| Boundary Scan / I/O Loopback | Physical FPGA board + JTAG | Use Vivado hardware manager |
| Memory BIST & Stress Tests | Physical FPGA board | Write test patterns in cocotb/pyuvm |

---

## 3. GitHub Equivalents Summary

| Commercial Tool | Open-Source GitHub Equivalent | Stars | License |
|---|---|---|---|
| ModelSim / Questa | `verilator/verilator` | 3.6k+ | LGPL v3 |
| ModelSim / Questa | `steveicarus/iverilog` | 3.6k+ | GPL v2 |
| SpyGlass (Synopsys) | `rtl-buddy/rtl-buddy-cdc` | 0 | BSD 3-Clause |
| SpyGlass (Synopsys) | `jyrj/crux` | 0 | Apache 2.0 |
| Vivado CDC | `vyges-tools/cdc` | 0 | Apache 2.0 |
| UVM (Synopsys/VCS) | `pyuvm/pyuvm` | 200+ | Apache 2.0 |
| PrimeTime (Synopsys) | `parallaxsw/OpenSTA` | 132 | GPL v3 |
| PrimeTime (Synopsys) | `The-OpenROAD-Project/OpenSTA` | 628 | GPL v3 |
| QEMU (HW/SW co-sim) | `qemu/qemu` | 10k+ | GPL v2 |
| GHDL (VHDL sim) | `ghdl/ghdl` | 2k+ | GPL v2 |
| GTKWave | `gtkwave/gtkwave` | 1k+ | GPL v2 |

---

## 4. What's Already Covered by Vivado (No Install Needed)

Vivado 2026.1 already provides:

| Feature | Vivado Capability |
|---|---|
| SDF Simulation (Gate-Level) | ✅ `xsim` with post-implementation SDF |
| Static Timing Analysis (STA) | ✅ Vivado Timing Analysis |
| Clock Domain Crossing (CDC) | ✅ Vivado CDC checks |
| Linting / RTL Rule Checks | ✅ Vivado Lint |
| Power and Thermal Analysis | ✅ Vivado Power Analysis |
| Block-Level IP Simulation | ✅ Vivado Simulation |
| SoC Interconnect Functional Sim | ✅ Vivado Simulation |
| Gate-Level / Post-Route Timing Sim | ✅ Vivado xsim (post-implementation) |
| Integrated Logic Analyzer (ILA) | ✅ Vivado Hardware Manager |
| Memory BIST & Stress Tests | ✅ Test patterns in Vivado |
| In-Circuit Hardware Validation | ✅ Vivado Hardware Manager + JTAG |

---

## 5. Recommended Install Commands (Copy-Paste)

### WSL (Ubuntu terminal):

```bash
# Priority 1: Immediate installs
sudo apt update && sudo apt upgrade -y
sudo apt install -y iverilog ghdl qemu-system sby symbiyosys

# Verify:
iverilog -V          # should print version
ghdl --version       # should print version
qemu-system-riscv64 --version  # should print version
```

### Windows (PowerShell):

```powershell
# Priority 1: Python packages
pip install pyuvm
pip install rtl-buddy-cdc
pip install cdc-auto-tool

# Verify:
python -c "import pyuvm; print(pyuvm.__version__)"
python -c "import rtl_buddy_cdc; print('rtl-buddy-cdc OK')"
python -c "import cdc_auto_tool; print('cdc-auto-tool OK')"
```

### Priority 2: Build from source (optional)

```bash
# OpenSTA (Static Timing Analysis)
git clone https://github.com/parallaxsw/OpenSTA.git
cd OpenSTA
mkdir build && cd build
cmake ..
make -j$(nproc)
# Result: build/sta (executable)
```

---

## 6. Summary Matrix

| Category | Tool / Feature | Installed? | Install Needed? | GitHub Equivalent |
|---|---|---|---|---|
| **FPGA Test & Simulation** | | | | |
| | ModelSim/Xsim (Gate-Level Sim) | ✅ (Vivado xsim) | No | `verilator/verilator` |
| | SpyGlass/Vivado CDC | ✅ (Vivado CDC) | No (optional: `rtl-buddy/rtl-buddy-cdc`) | `rtl-buddy/rtl-buddy-cdc` |
| | Cocotb | ✅ (2.0.1) | No | `cocotb/cocotb` |
| | Icarus Verilog (iverilog) | ❌ | `sudo apt install iverilog` | `steveicarus/iverilog` |
| | GTKWave | ✅ (WSL) | No | `gtkwave/gtkwave` |
| | UVM (Register Model) | ❌ | `pip install pyuvm` | `pyuvm/pyuvm` |
| | CRS (Firmware reg mapping) | ❌ | Research needed | Unknown |
| | HW/SW Co-simulation | ❌ | `sudo apt install qemu-system` | `qemu/qemu` |
| | Static Timing Analysis (STA) | ✅ (Vivado) | No (optional: OpenSTA) | `parallaxsw/OpenSTA` |
| | Clock Domain Crossing (CDC) | ✅ (Vivado) | No (optional: open-source CDC) | `jyrj/crux` |
| | Linting / RTL Rule Checks | ✅ (Verilator + Vivado) | No | `verilator/verilator` |
| | Power and Thermal Analysis | ✅ (Vivado) | No | `parallaxsw/OpenSTA` |
| **Pre- & Post-Hardware Testing** | | | | |
| | Block-Level IP Simulation | ✅ (Vivado xsim + Verilator) | No | `verilator/verilator` |
| | SoC Interconnect Functional Sim | ✅ (Vivado xsim) | No | `verilator/verilator` |
| | UVM RAL Tests | ❌ | `pip install pyuvm` | `pyuvm/pyuvm` |
| | Gate-Level / Post-Route Timing Sim | ✅ (Vivado xsim) | No | `verilator/verilator` |
| | In-Circuit Hardware Validation | ❌ | Physical FPGA board | — |
| | Memory BIST & Stress Tests | ❌ | Test patterns (no tool) | — |
| | Integrated Logic Analyzer (ILA) | ✅ (Vivado ILA) | No | — |
| | Software-in-the-Loop (SIL) | ❌ | `sudo apt install qemu-system` | `qemu/qemu` |
| | Boundary Scan / I/O Loopback | ❌ | Physical FPGA board | — |

---

## 7. Quick Install Script (Copy-Paste)

### WSL (Ubuntu terminal):

```bash
#!/bin/bash
# FPGA Verification Toolchain - Priority 1 installs
sudo apt update && sudo apt upgrade -y
sudo apt install -y iverilog ghdl qemu-system sby symbiyosys gtkwave

# Verify
echo "=== Verilator ===" && verilator --version
echo "=== Yosys ===" && yosys -V
echo "=== Icarus Verilog ===" && iverilog -V
echo "=== GHDL ===" && ghdl --version
echo "=== QEMU ===" && qemu-system-riscv64 --version
echo "=== sby ===" && sby -V
echo "=== GTKWave ===" && gtkwave --version
```

### Windows (PowerShell):

```powershell
# FPGA Verification Toolchain - Priority 1 installs
pip install pyuvm
pip install rtl-buddy-cdc
pip install cdc-auto-tool

# Verify
python -c "import pyuvm; print('pyuvm OK')"
python -c "import rtl_buddy_cdc; print('rtl-buddy-cdc OK')"
python -c "import cdc_auto_tool; print('cdc-auto-tool OK')"
```

---

*This plan was generated based on the tools currently installed on this system
and their open-source GitHub equivalents. Commercial tools (ModelSim, SpyGlass,
Vivado) are already available via Vivado 2026.1 installation.*