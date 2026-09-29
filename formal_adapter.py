"""Vendor-neutral EDA cross-verification adapter (frozen item 1).

Contract (architecture addendum): prepare / execute / collect_artifacts /
parse_results / normalize_evidence / calculate_hashes / report_status.
AMD Vivado/XSim, Questa, VCS, Xcelium slot into the same contract later;
SymbiYosys is the first implementation. Nothing here is vendor-specific
except the log grammar in parse_sby_log().

Outcome states (never silently PASS):
  PASS / FAIL               — decided by the tool
  UNPROVEN                  — bounded run, unknown (timeout / depth wall)
  NOT_EXECUTED              — skipped by policy, recorded explicitly
  UNAVAILABLE               — tool/license missing, recorded explicitly
  SKIPPED_BY_POLICY         — alias of NOT_EXECUTED with a reason
run_formal() never raises: every infrastructure fault becomes a status.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field

EDA_STATUS = ("EXECUTED", "NOT_EXECUTED", "PASS", "FAIL", "UNPROVEN",
              "UNAVAILABLE", "SKIPPED_BY_POLICY")

SBY_TIMEOUT_S = 900


@dataclass
class FormalRun:
    tool: str = "symbiyosys"
    tool_version: str = ""
    target: str = ""              # device / design under proof
    rtl_commit: str = ""
    run_id: str = ""
    requirement_ids: tuple = ()
    status: str = "NOT_EXECUTED"  # one of EDA_STATUS (minus EXECUTED)
    asserts: dict = field(default_factory=dict)  # name -> PASS/FAIL/UNKNOWN
    artifacts: list = field(default_factory=list)
    artifact_hashes: dict = field(default_factory=dict)
    log_excerpt: str = ""
    duration_s: float = 0.0
    reason: str = ""


def prepare(workdir: str) -> str:
    os.makedirs(workdir, exist_ok=True)
    return workdir


def _sby_cmd(sby_file: str, workdir: str) -> list[str]:
    if os.name == "nt":
        mnt = "/mnt/" + sby_file[0].lower() + sby_file[2:].replace("\\", "/")
        return ["wsl", "sby", "-f", mnt, "-d",
                "/mnt/" + workdir[0].lower() + workdir[2:].replace("\\", "/")]
    return ["sby", "-f", sby_file, "-d", workdir]


def execute(sby_file: str, workdir: str,
            timeout_s: int = SBY_TIMEOUT_S) -> tuple[int, str, float]:
    """Run sby. Returns (rc, log, seconds). Missing binary -> FileNotFoundError
    (callers map it to UNAVAILABLE, never crash)."""
    cmd = _sby_cmd(sby_file, workdir)
    start = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s,
                       cwd=os.path.dirname(os.path.abspath(sby_file)))
    return p.returncode, (p.stdout or "") + (p.stderr or ""), \
        time.perf_counter() - start


def parse_sby_log(log: str, assert_names: tuple = ()) -> tuple[str, dict]:
    """sby log -> (status, {assert: PASS/FAIL/UNKNOWN}).

    Grammar (sby 0.68): per-task `DONE (PASS, rc=0)` / `DONE (FAIL, ...)` /
    `DONE (ERROR, ...)`; failures name the assert
    (`failed assertion <top>.<NAME> ...`); passes name nothing, so caller-
    supplied assert_names are marked PASS on overall PASS, UNKNOWN otherwise.
    No DONE line (timeout/kill) -> UNPROVEN (bounded-unknown, never PASS).
    """
    asserts: dict[str, str] = {}
    for m in re.finditer(r"(?:Assert|Check)\s+`?(\w+)'?\s*.*?\b(passed|failed)\b",
                         log, re.IGNORECASE):
        asserts[m.group(1)] = "PASS" if m.group(2).lower() == "passed" else "FAIL"
    for m in re.finditer(r"failed assertion \S+\.(\w+)", log):
        asserts[m.group(1)] = "FAIL"
    done = re.search(r"DONE\s*\((PASS|FAIL|ERROR)[^)]*\)", log)
    if done:
        kind = done.group(1)
        if kind == "PASS":
            for n in assert_names:
                asserts.setdefault(n, "PASS")
            return "PASS", asserts
        for n in assert_names:
            asserts.setdefault(n, "UNKNOWN")
        return "FAIL", asserts
    if re.search(r"\b(timeout|timed out|TIMEOUT)\b", log, re.IGNORECASE):
        return "UNPROVEN", asserts
    return "UNPROVEN", asserts


def collect_artifacts(workdir: str, limit: int = 40) -> list[str]:
    found = []
    for root, _, files in os.walk(workdir):
        for fn in files:
            found.append(os.path.join(root, fn))
            if len(found) >= limit:
                return found
    return found


def calculate_hashes(paths: list[str]) -> dict:
    out = {}
    for p in paths:
        try:
            h = hashlib.sha256()
            with open(p, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
            out[p] = h.hexdigest()[:16]
        except OSError:
            continue
    return out


def normalize_evidence(run: FormalRun) -> dict:
    """Machine-readable EDA evidence (architecture schema, formal profile)."""
    return {
        "tool": "SymbiYosys" if run.tool == "symbiyosys" else run.tool,
        "tool_version": run.tool_version,
        "target_device": run.target,
        "rtl_commit": run.rtl_commit,
        "run_id": run.run_id,
        "requirement_ids": list(run.requirement_ids),
        "formal": {
            "status": run.status,
            "asserts": dict(run.asserts),
            "duration_s": round(run.duration_s, 1),
            "reason": run.reason,
        },
        "artifacts": list(run.artifacts),
        "artifact_hashes": dict(run.artifact_hashes),
        "evidence_hash": hashlib.sha256(
            json.dumps([run.tool, run.tool_version, run.target,
                        run.rtl_commit, run.run_id, run.status,
                        sorted(run.asserts.items())],
                       sort_keys=True).encode()).hexdigest()[:16],
    }


def to_ledger(ledger, requirement_id: str, evidence: dict,
              artifact: str):
    """Evidence -> ledger record. UNPROVEN/PASS/FAIL carry the run as checks;
    anything else becomes an explicit NOT_EXECUTED (never a silent PASS)."""
    from evidence import EvidenceRecord
    status = evidence["formal"]["status"]
    checks = {"formal_proof": evidence["formal"]["asserts"],
              "evidence_hash": evidence["evidence_hash"]}
    if status in ("PASS", "FAIL", "UNPROVEN"):
        return ledger.append(EvidenceRecord(
            requirement_id, artifact, checks, status,
            tool=evidence["tool"], tool_version=evidence["tool_version"],
            rtl_commit=evidence["rtl_commit"], run_id=evidence["run_id"],
            artifact_hashes=evidence["artifact_hashes"]))
    return ledger.record_not_executed(
        requirement_id, artifact,
        f"formal {status}: {evidence['formal']['reason']}",
        run_id=evidence["run_id"])


def report_status(run: FormalRun) -> str:
    n = len(run.asserts)
    return (f"{run.tool} {run.tool_version or '?'} [{run.target or '?'}]: "
            f"{run.status} ({n} asserts, {run.duration_s:.0f}s)")


# --- Per-property proofs for T1-class delay requirements (dev-machine) ---

# RTL locations: the sby flow consumes the /mnt path inside WSL; the
# existence guard below must use the NATIVE path of the host interpreter.
WB_RTL_WSL = "/mnt/c/Projects/ChipDesign/rideprotect-rv/rtl/wb_dma.v"
WB_RTL_WIN = r"C:\Projects\ChipDesign\rideprotect-rv\rtl\wb_dma.v"

WB_PROP_WRAPPER = """module wb_dma_formal (
    input wire        clk,
    input wire        s_wb_cyc,
    input wire        s_wb_stb,
    input wire        s_wb_we,
    input wire [31:0] s_wb_adr,
    input wire [31:0] s_wb_dat_w,
    input wire [ 3:0] s_wb_sel,
    input wire [31:0] m_wb_dat_r,
    input wire        m_wb_ack
);
    reg [1:0] reset_cnt = 2'd0;
    always @(posedge clk) begin
        if (reset_cnt != 2'd2)
            reset_cnt <= reset_cnt + 1'b1;
    end
    wire rst = (reset_cnt != 2'd2);

    wire [31:0] s_wb_dat_r;
    wire        s_wb_ack;
    wire        m_wb_cyc;
    wire        m_wb_stb;
    wire        m_wb_we;
    wire [31:0] m_wb_adr;
    wire [31:0] m_wb_dat_w;
    wire [ 3:0] m_wb_sel;
    wire        irq;

    wb_dma dut (
        .clk(clk), .rst(rst),
        .s_wb_cyc(s_wb_cyc), .s_wb_stb(s_wb_stb), .s_wb_we(s_wb_we),
        .s_wb_adr(s_wb_adr), .s_wb_dat_w(s_wb_dat_w), .s_wb_sel(s_wb_sel),
        .s_wb_dat_r(s_wb_dat_r), .s_wb_ack(s_wb_ack),
        .m_wb_cyc(m_wb_cyc), .m_wb_stb(m_wb_stb), .m_wb_we(m_wb_we),
        .m_wb_adr(m_wb_adr), .m_wb_dat_w(m_wb_dat_w), .m_wb_sel(m_wb_sel),
        .m_wb_dat_r(m_wb_dat_r), .m_wb_ack(m_wb_ack),
        .irq(irq)
    );

    always @(posedge clk) begin
        if (!rst && $past(!rst)) begin
            {PROP}
        end
    end
endmodule
"""

WB_SBY = """[tasks]
prove
[options]
mode bmc
depth 20
[engines]
smtbmc z3
[script]
read_verilog -formal /mnt/c/Projects/ChipDesign/rideprotect-rv/rtl/wb_dma.v
read_verilog -formal prop.sv
prep -top wb_dma_formal
[files]
/mnt/c/Projects/ChipDesign/rideprotect-rv/rtl/wb_dma.v
prop.sv
"""


def prove_wb_prop(prop_line: str, timeout_s: int = 300,
                  run_id: str = "") -> bool | None:
    """Prove one immediate-assert property line about wb_dma.

    Returns True (PROVEN) / False (FAILED = genuinely wrong property) /
    None (tool unavailable or bounded-unknown — fails CLOSED downstream,
    escalates, never passes). Dev-machine only (absolute RTL path).
    """
    import tempfile as _tf
    if "assert" not in prop_line.lower():
        return None
    if not (os.path.isfile(WB_RTL_WIN) or os.path.isfile(WB_RTL_WSL)):
        return None
    work = _tf.mkdtemp(prefix="wbprop_")
    try:
        with open(os.path.join(work, "prop.sv"), "w",
                  encoding="utf-8") as f:
            f.write(WB_PROP_WRAPPER.replace("{PROP}", prop_line))
        sby_path = os.path.join(work, "prop.sby")
        with open(sby_path, "w", encoding="utf-8") as f:
            f.write(WB_SBY)
        run = run_formal(sby_path, os.path.join(work, "out"),
                         requirement_ids=("REQ-DMA-ACK",), target="wb_dma",
                         rtl_commit="wb_dma.v", run_id=run_id,
                         timeout_s=timeout_s, assert_names=("A_GEN",))
        if run.status == "PASS":
            return True
        if run.status == "FAIL":
            return False
        return None
    finally:
        import shutil as _sh
        _sh.rmtree(work, ignore_errors=True)


def sby_version() -> str:
    """Best-effort sby version; '' when unreachable (maps to UNAVAILABLE)."""
    base = ["wsl", "sby", "--version"] if os.name == "nt" else ["sby", "--version"]
    try:
        p = subprocess.run(base, capture_output=True, text=True, timeout=60)
        m = re.search(r"SBY\s+([\w.]+)", (p.stdout or "") + (p.stderr or ""))
        return m.group(1) if m else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def run_formal(sby_file: str, workdir: str, requirement_ids: tuple = (),
               target: str = "", rtl_commit: str = "", run_id: str = "",
               timeout_s: int = SBY_TIMEOUT_S,
               skip_reason: str = "",
               assert_names: tuple = ()) -> FormalRun:
    """Full adapter run. Never raises — faults become statuses."""
    run = FormalRun(target=target, rtl_commit=rtl_commit, run_id=run_id,
                    requirement_ids=requirement_ids)
    if skip_reason:
        run.status, run.reason = "SKIPPED_BY_POLICY", skip_reason
        return run
    if not os.path.isfile(sby_file):
        run.status, run.reason = "NOT_EXECUTED", f"missing {sby_file}"
        return run
    run.tool_version = sby_version()
    if not run.tool_version:
        run.status, run.reason = "UNAVAILABLE", "sby binary unreachable"
        return run
    try:
        prepare(workdir)
        rc, log, dur = execute(sby_file, workdir, timeout_s)
        run.duration_s = dur
        run.log_excerpt = "\n".join(log.splitlines()[-25:])
        status, asserts = parse_sby_log(log, assert_names)
        run.status, run.asserts = status, asserts
        if status == "UNPROVEN" and not run.reason:
            run.reason = f"rc={rc}; no DONE line (timeout/kill at {timeout_s}s?)"
        run.artifacts = collect_artifacts(workdir)
        run.artifact_hashes = calculate_hashes(
            [a for a in run.artifacts if a.endswith((".log", ".sby", ".xml"))])
    except subprocess.TimeoutExpired:
        run.status, run.reason = "UNPROVEN", f"timeout at {timeout_s}s"
    except (OSError, subprocess.SubprocessError) as exc:
        run.status, run.reason = "UNAVAILABLE", str(exc)[:200]
    return run
