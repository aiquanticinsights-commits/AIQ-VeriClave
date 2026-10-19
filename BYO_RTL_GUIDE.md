# Bring Your Own RTL — Verifying Your FPGA Project with VeriClave

> Audience: a test/verification engineer who has an FPGA block (Verilog/SystemVerilog)
> and has never used VeriClave before.
>
> This guide tells you exactly what runs today, what does **not** run, and the
> commands to type. It contains no aspirational commands.

---

## 0. Read this first — what VeriClave is and is not

VeriClave is a **verification-research platform**, not a one-click "point it at
your project" product. There is **no `Makefile`** in the repo.

> **Do not run `make ai-verify` / `make ai-gen` / `make ai-localize`.** Those
> targets are documented architecture intent in `OPENCODE_WORKFLOW.md` and the
> skill descriptions. They are **not implemented**. This guide only uses entry
> points that exist.

What actually runs on a real design is a set of **qualified tool adapters**, a
set of **deterministic generators**, and a **Python stage pipeline**. Support is
uneven, and the platform is honest about it (`adapter_registry.py`):

| Tool | Function | Level | Meaning for you |
|---|---|---|---|
| Verilator | lint + sim | **L4** | real execution validated — safe to rely on |
| Yosys | synth-check | **L4** | real execution validated — safe to rely on |
| SymbiYosys | bounded formal | **L4** | bounded proofs only (see `formal_policy.py`) |
| Vivado xsim | block-run | **L4** | qualified functions only |
| VCS | log-parse | **L1** | parses your log; **never executes VCS** |
| Questa | log-parse | **L1** | parses your log; **never executes Questa** |
| Xcelium | log-parse | **L1** | parses your log; **never executes Xcelium** |
| uvm-gen | TLM skeleton | **L1** | generates templates; unexecuted in-simulator |

**Bottom line:** the open toolchain (Verilator + Yosys + SymbiYosys) is the
fully-supported path. If your flow is vendor-only (Vivado/VCS/Questa/Xcelium),
the platform can parse your logs and reason about them, but it will not drive
those tools for you.

Throughout, this guide assumes:

- Your RTL lives in `rtl/` and is treated as **read-only** by the platform.
- Each requirement has a stable ID (`REQ-001`, `REQ-002`, ...). Every generated
  artifact and every evidence row carries that ID — it is the backbone of the
  whole flow.

---

## 1. Install and verify the environment

```powershell
git clone https://github.com/aiquanticinsights-commits/AIQ-VeriClave.git
cd AIQ-VeriClave
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

Install the open EDA tools **inside WSL2** (the repo shells out via `wsl`):

```bash
wsl -d Ubuntu
sudo apt update && sudo apt install -y verilator yosys
# SymbiYosys: install per its upstream instructions; a missing sby is
# non-blocking by design (that stage reports NOT_EXECUTED, never a pass).
```

Verify what is reachable:

```powershell
python portability.py
```

This writes `PORTABILITY_dev.json` with tool versions and a lint smoke check.
Read it before trusting any later result. A tool marked `UNAVAILABLE` means its
stage will honestly report `NOT_EXECUTED` rather than silently passing.

Docker alternative (pinned, reproducible):

```bash
docker build -t aiq-vericlave .
docker run --rm aiq-vericlave
```

---

## 2. Lay out your project

```
your_block/
  rtl/            <- your synthesizable RTL (read-only to VeriClave)
  spec/reqs.md    <- requirements, one per line, each with an ID
  tb/             <- your testbench / checkers
  evidence/       <- created by the platform (ledger, reports)
```

Write your requirements explicitly, one line each, e.g.:

```
REQ-001  FIFO shall assert `full` when the depth is reached.
REQ-002  `wr_en` shall be ignored while `full` is asserted.
REQ-003  `full` shall deassert within one cycle of a read when not refilled.
```

Vague requirements produce vague intents, and the generator will **refuse**
underspecified input (`intent.py` fails closed by design).

---

## 3. Turn each requirement into a typed "intent" and generate artifacts

The typed intermediate representation (`intent.py`) makes widths, clocks, reset
polarity, module and artifact type **explicit**, so generation never guesses.
`sva` / `test` / `coverage` / `checker` are all supported.

```python
from intent import VerificationIntent, Signal, Clock, Reset
from generate import generate

it = VerificationIntent(
    requirement_id="REQ-001",
    module="my_fifo",
    artifact="sva",
    signals=[Signal("full", 1, clock="clk"),
             Signal("wr_en", 1, clock="clk")],
    clocks=[Clock("clk", 10.0)],
    reset=Reset("rst_n", "active-low", "async"),
    temporal=["|->", "##1"],
)

errors = it.validate()          # []  -> the intent type-checks
if not errors:
    print(generate(it))         # SVA skeleton tagged with REQ-001
```

Write the result into `tb/` (or your artifacts directory). The output is a
**compilable skeleton** with machine-checkable structure; proving it is the
tools' job, never the generator's.

For each requirement you typically want several artifacts — a `sva`, a
`checker`, a `coverage`, a `test` — each its own `VerificationIntent`.

---

## 4. Run the machine checks (this is the actual proof)

```powershell
# Lint / syntax gate
wsl verilator --lint-only -Wall rtl/my_fifo.v

# Synthesizability check
wsl yosys -p "read_verilog rtl/my_fifo.v; synth; stat"

# Bounded formal property proof (if you have a property file)
wsl sby -f formal/my_fifo.sby
```

Normalize **any** tool's log into one failure model (this is how vendor logs
still add value):

```python
from sim_adapters import normalize, summarize

events = normalize(open("verilator.log").read())   # auto-detects the tool
print(summarize(events))   # {"errors": .., "failures": .., "warnings": .., "total": ..}
```

`sim_adapters.py` understands Verilator, VCS, Questa, Xcelium and Vivado-xsim
logs. Vendor logs are analyzed here; they are never executed by VeriClave.

---

## 4a. Assisted path (optional, recommended for a first run)

If you are using the OpenCode agent, load the skills and let it drive the loop
for you — it runs the same stages below. Load:

- `ai-verify-harness` — the stage ladder and gates
- `ai-mutate` — mutation campaign
- `ai-localize` — fault localization
- `ai-close` — bounded closure
- `ai-evidence` — evidence ledger

Then describe your block and paste your `spec/reqs.md`. The agent will build
intents, generate artifacts, run the open tools, mutate, localize, close, and
record evidence. Everything below is what it does under the hood — you can also
run it by hand.

---

## 5. Measure test quality with mutation

`mutate.py` injects real fault classes into copies of your RTL (relational,
arithmetic, bit, control, sequential, temporal, CDC) and the runner re-runs your
checks against each mutant. **A mutant your checks fail to catch is a hole in
your verification.**

Operator families (`mutate.py`):

- `REL_GT_GE`, `REL_LT_LE`, `REL_EQ_NE` — relational flips
- `ARITH_PLUS1`, `ARITH_MINUS1` — literal off-by-one
- `BIT_IDX_P1`, `BIT_IDX_M1`, `BIT_NEG_TOGGLE` — bit-select / inversion
- `CTRL_COND_INVERT`, `CTRL_STMT_DELETE` — condition/statement faults
- `SEQ_RESET_FLIP`, `SEQ_ENABLE_REMOVE` — sequential faults
- `TEMPORAL_DELAY_P1`, `TEMPORAL_DELAY_M1` — assertion timing (must be killed by
  formal or sim; lint will not catch these)
- `CDC_STAGE_REMOVE` — single-flop CDC collapse

The campaign writes a **mutation cache** and a **blind-spot report**. Read the
report: it is the honest list of what your verification does *not* cover.

---

## 6. Localize failures

When a check fails, rank where to look:

```python
from localize import localize

suspects = localize("rtl/my_fifo.v", open("verilator.log").read(), top_n=3)
for s in suspects:
    print(s["rank"], s["where"], s["signal"], s["reason"])
```

`localize.py` is deterministic: it surfaces `file:line` anchors the tool pointed
at, then identifiers recurring across diagnostics. It ranks *where to look*; it
never proposes a fix.

---

## 7. Bounded closure / repair

The repair loop is deliberately bounded (`closure.py`): at most **R0–R3**
automatic rounds, then `HUMAN_ESCALATION`. A failed round can **never** be
converted to PASS.

```python
from closure import ClosureBoundary

b = ClosureBoundary("REQ-001")
b.attempt("cand0", "FAIL", repair_action="tighten reset branch", evidence_hash="h0")
b.attempt("cand1", "PASS", evidence_hash="h1")
print(b.disposition())   # "PASS" | "HUMAN_ESCALATION" | "OPEN"
```

If it escalates, a human decides — that is a feature, not a failure.

---

## 8. Record evidence and sign off

Every accepted artifact becomes an append-only, hash-chained row:

```python
from evidence import EvidenceLedger, EvidenceRecord

led = EvidenceLedger()
led.append(EvidenceRecord(
    requirement_id="REQ-001",
    artifact="SVA/fifo_full",
    checks={"lint": True, "synth": True, "proof": False},
    verdict="UNPROVEN",              # explicit, never blank
    tool="verilator", tool_version="5.032",
    signed_by="",                    # a named human fills this
))

print(led.verify_chain())          # True  -> tamper-evident chain intact
print(led.audit_completeness())    # 1.0   -> C4 target met
```

Rules the ledger enforces for you:

- Verdicts come from a frozen set: `PASS`, `FAIL`, `DISPOSITIONED`, `EXECUTED`,
  `NOT_EXECUTED`, `UNPROVEN`, `UNAVAILABLE`, `SKIPPED_BY_POLICY`, `SIM_COVERED`,
  `NOT_APPLICABLE`.
- **`NOT_EXECUTED` must never become `PASS`.** An explicitly recorded
  `NOT_EXECUTED` is complete; a missing verdict is not.
- `audit_completeness()` must reach **1.0** — no record may sit verdict-less or
  evidence-less without an explicit disposition.

Sign-off is by a **named human**. Check the program gate table:

```powershell
python simple_signoff.py --check-gates
python simple_signoff.py --signoff      # interactive; appends to PROGRAM_LEDGER.md
```

---

## 9. What "done" looks like

You can call a block verified when **all** of these hold:

1. Every `REQ-xxx` has an evidence row with a **known verdict**.
2. `ledger.audit_completeness() == 1.0` and `verify_chain() == True`.
3. The mutation blind-spot report is reviewed; survivors are either killed or
   explicitly dispositioned (`NOT_APPLICABLE`, etc.).
4. Any escalated requirement has a named-human decision recorded.
5. A named human signs the ledger.

---

## 10. Do **not** claim

- **Do not** present `make ai-verify` (or any `make ai-*`) as runnable — there is
  no Makefile.
- **Do not** claim vendor-tool execution: VCS / Questa / Xcelium are **L1
  log-parse only**. Only Verilator, Yosys, SymbiYosys and Vivado-xsim block-run
  are execution-qualified (L4).
- **Do not** claim unbounded formal — proofs are bounded per `formal_policy.py`.
- **Do not** have AI author the checker for the **P7 human-control arm** — that
  voids the arm (see `PILOT_PROTOCOL.md`, `HUMAN_ARM_RUNBOOK.md`).

---

## Quick reference — real entry points

| Task | Command / API |
|---|---|
| Install (source) | `pip install -e .` |
| Environment check | `python portability.py` |
| Type + generate | `intent.VerificationIntent` → `generate.generate(it)` |
| Lint | `wsl verilator --lint-only -Wall rtl/<f>.v` |
| Synth-check | `wsl yosys -p "read_verilog <f>; synth; stat"` |
| Bounded formal | `wsl sby -f <file>.sby` |
| Normalize any log | `sim_adapters.normalize(text)` |
| Localize | `localize.localize(artifact, log)` |
| Bounded closure | `closure.ClosureBoundary` |
| Evidence ledger | `evidence.EvidenceLedger` / `EvidenceRecord` |
| Gates / sign-off | `python simple_signoff.py --check-gates` |

Reference: `adapter_registry.py` (support levels), `PRODUCTION_READINESS.md`
(gate status), `OPENCODE_WORKFLOW.md` (agent skills — *intent*, not `make`),
`INSTALL.md` (install options).
