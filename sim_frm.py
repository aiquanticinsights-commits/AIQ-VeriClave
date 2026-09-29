"""wb_dma simulation + Python FRM co-simulation harness (frozen item 2).

Two independent executors run the SAME constrained stimulus and their event
traces must match exactly:

  RTL side : Verilator --cc + handwritten C++ driver (sim/tb_wb_dma.cpp),
             built once per RTL hash, driven by the stim DSL below.
  FRM side : WbDmaFrm — statement-by-statement transliteration of the
             wb_dma.v synchronous always block (reset values, register file,
             ack timing, transfer engine, irq equation).

Harness rule (both sides, identically): each cycle the slave inputs are
presented, the design is evaluated, the master stub answers m_ack=1 with
pattern data while m_stb is up (combinational settle + second eval), then
the clock advances. The FRM mirrors this order exactly — equivalence is
timing-exact by construction, so ANY trace mismatch is a real defect in
either the RTL or the FRM (diagnose, never average away).

Stimulus DSL (constrained, LLM-fillable; validated by STIM_RE before use):
  RST                  reset pulse (2 cycles high, then low)
  W <adr> <dat>        wishbone write transaction (byte hex, sel=0xF)
  R <adr>              wishbone read transaction (captures dat_r)
  TICK <n>             idle cycles (1..1000)

Trace line format (both sides, compared verbatim):
  W <adr8> <dat8> ack=<0/1>
  R <adr8> <dat8>
  IRQ <0/1>            (emitted after any event that changes irq)
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RTL = os.path.join(os.path.dirname(HERE), "rideprotect-rv", "rtl",
                           "wb_dma.v")
TB_CPP = os.path.join(HERE, "sim", "tb_wb_dma.cpp")
BUILD_TIMEOUT_S = 600
RUN_TIMEOUT_S = 300

STIM_RE = re.compile(r"^(rst|tick ([1-9][0-9]{0,2}|1000)|"
                     r"w [0-9a-f]{1,8} [0-9a-f]{1,8}|"
                     r"r [0-9a-f]{1,8})$")

S_IDLE, S_READ, S_WRITE = 0, 1, 2


def validate_stim(lines: list[str]) -> list[str]:
    """Constrained DSL gate: every line must match exactly (case-insensitive
    hex accepted, normalized to lower). Anything else is rejected whole —
    the LLM never drives the simulator with unparsed text."""
    clean = []
    for ln in lines:
        s = ln.strip().lower()
        if not STIM_RE.match(s):
            raise ValueError(f"stimulus rejected: {ln!r}")
        clean.append(s)
    return clean


class WbDmaFrm:
    """Cycle model of wb_dma. All updates are nonblocking-style: the next
    state is computed purely from the pre-cycle state, then committed."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.src_addr = 0
        self.dst_addr = 0
        self.word_count = 0
        self.ctrl = 0
        self.status = 0
        self.src_shdw = 0
        self.dst_shdw = 0
        self.cnt_shdw = 0
        self.data_buf = 0
        self.dma_state = S_IDLE
        self.irq_flag = False
        self.irq_en = False
        self.s_wb_ack = False
        self.s_wb_dat_r = 0
        self._xfers = 0  # completed master reads (m_dat pattern counter)

    # -- combinational helpers (mirror the assign statements) --
    @staticmethod
    def _reg_sel(adr: int) -> int:
        return (adr >> 2) & 0x1F

    def _start_xfer(self) -> bool:
        return bool(self.ctrl & 1) and not (self.status & 1) \
            and self.word_count > 0

    def _master(self) -> dict:
        st = self.dma_state
        return {
            "m_cyc": st != S_IDLE,
            "m_stb": st in (S_READ, S_WRITE),
            "m_we": st == S_WRITE,
            "m_adr": self.src_shdw if st == S_READ else self.dst_shdw,
            "m_sel": 0xF,
        }

    def irq(self) -> bool:
        return bool(self.irq_flag and self.irq_en)

    def step(self, rst: bool, cyc: bool, stb: bool, we: bool, adr: int,
             dat_w: int, sel: int, m_ack: bool, m_dat: int) -> dict:
        """Advance one clock. Returns post-cycle {ack, dat_r, irq}."""
        if rst:
            self.reset()
            return self._out()
        n = dict(
            src_addr=self.src_addr, dst_addr=self.dst_addr,
            word_count=self.word_count, ctrl=self.ctrl, status=self.status,
            src_shdw=self.src_shdw, dst_shdw=self.dst_shdw,
            cnt_shdw=self.cnt_shdw, data_buf=self.data_buf,
            dma_state=self.dma_state, irq_flag=self.irq_flag,
            irq_en=self.irq_en, s_wb_ack=False, s_wb_dat_r=0,
        )
        if self._start_xfer() and self.dma_state == S_IDLE:
            n["src_shdw"] = self.src_addr
            n["dst_shdw"] = self.dst_addr
            n["cnt_shdw"] = self.word_count
            n["status"] = self.status | 0x1
            n["dma_state"] = S_READ
        if self.dma_state == S_READ and m_ack:
            n["data_buf"] = m_dat
            n["dma_state"] = S_WRITE
        if self.dma_state == S_WRITE and m_ack:
            if self.ctrl & 0x2:
                n["src_shdw"] = (self.src_shdw + 4) & 0xFFFFFFFF
            if self.ctrl & 0x4:
                n["dst_shdw"] = (self.dst_shdw + 4) & 0xFFFFFFFF
            n["cnt_shdw"] = (self.cnt_shdw - 1) & 0xFFFF
            if self.cnt_shdw <= 1:
                n["dma_state"] = S_IDLE
                n["status"] = (self.status & ~0x1) | 0x2
                n["irq_flag"] = True
            else:
                n["dma_state"] = S_READ
        rs = self._reg_sel(adr)
        if cyc and stb and we and self.dma_state == S_IDLE:
            if rs == 0:
                for i in range(4):
                    if sel >> i & 1:
                        n["src_addr"] = (n["src_addr"] & ~(0xFF << 8 * i)) | \
                            ((dat_w >> 8 * i & 0xFF) << 8 * i)
            elif rs == 1:
                for i in range(4):
                    if sel >> i & 1:
                        n["dst_addr"] = (n["dst_addr"] & ~(0xFF << 8 * i)) | \
                            ((dat_w >> 8 * i & 0xFF) << 8 * i)
            elif rs == 2:
                for i in range(2):
                    if sel >> i & 1:
                        n["word_count"] = (n["word_count"] & ~(0xFF << 8 * i)) | \
                            ((dat_w >> 8 * i & 0xFF) << 8 * i)
            elif rs == 3:
                if sel & 1:
                    n["ctrl"] = dat_w & 0xF
        if cyc and stb and we:
            if rs == 4 and sel & 1:
                if dat_w & 1:
                    n["status"] &= ~0x1
                if dat_w & 2:
                    n["status"] &= ~0x2
                if dat_w & 4:
                    n["status"] &= ~0x4
                if dat_w & 8:
                    n["irq_flag"] = False
            if rs == 5 and sel & 1:
                n["irq_en"] = bool(dat_w & 1)
        if cyc and stb:
            # Nonblocking RHS: reads see PRE-cycle registers (self.*),
            # exactly like the Verilog (verified against held-sample flow).
            n["s_wb_dat_r"] = {
                0: self.src_addr, 1: self.dst_addr,
                2: self.word_count, 3: self.ctrl, 4: self.status,
                5: int(self.irq_en),
            }.get(rs, 0)
            n["s_wb_ack"] = True
        for k, v in n.items():
            setattr(self, k, v)
        return self._out()

    def _out(self) -> dict:
        return {"ack": self.s_wb_ack, "dat_r": self.s_wb_dat_r,
                "irq": self.irq()}

    def run_stim(self, lines: list[str]) -> list[str]:
        """Execute validated DSL, return event trace lines."""
        trace: list[str] = []
        last_irq = self.irq()

        def emit_irq():
            nonlocal last_irq
            if self.irq() != last_irq:
                last_irq = self.irq()
                trace.append(f"IRQ {int(last_irq)}")

        def cycle(rst=False, cyc=False, stb=False, we=False, adr=0,
                  dat_w=0, sel=0, m_ack=False, m_dat=0):
            # Harness order (mirrored by the C++ driver): present slave
            # inputs, settle master stub combinationally, then clock.
            m = self._master()
            if m["m_stb"]:
                m_ack, m_dat = True, 0xA5000000 + self._xfers
            out = self.step(rst, cyc, stb, we, adr, dat_w, sel,
                            m_ack, m_dat)
            if m["m_stb"] and m_ack and self.dma_state == S_WRITE:
                self._xfers += 1
            return out

        for ln in validate_stim(lines):
            parts = ln.split()
            if parts[0] == "rst":
                cycle(rst=True)
                cycle(rst=True)
                emit_irq()
            elif parts[0] == "tick":
                for _ in range(int(parts[1])):
                    cycle()
                emit_irq()
            elif parts[0] == "w":
                # Classic Wishbone: hold the request through the sample
                # cycle (slave ack is registered), then idle one cycle.
                adr, dat = int(parts[1], 16), int(parts[2], 16)
                cycle(cyc=True, stb=True, we=True, adr=adr, dat_w=dat,
                      sel=0xF)
                out = cycle(cyc=True, stb=True, we=True, adr=adr,
                            dat_w=dat, sel=0xF)
                trace.append(f"W {adr:08x} {dat:08x} ack={int(out['ack'])}")
                cycle()
                emit_irq()
            elif parts[0] == "r":
                adr = int(parts[1], 16)
                cycle(cyc=True, stb=True, adr=adr)
                out = cycle(cyc=True, stb=True, adr=adr)
                trace.append(f"R {adr:08x} {out['dat_r']:08x}")
                cycle()
                emit_irq()
        return trace


def compare_traces(frm_trace: list[str], rtl_trace: list[str]) -> dict:
    """Exact event-trace equivalence. First divergence reported with index."""
    n = min(len(frm_trace), len(rtl_trace))
    for i in range(n):
        if frm_trace[i] != rtl_trace[i]:
            return {"match": False, "first_diverge": i,
                    "frm": frm_trace[i], "rtl": rtl_trace[i]}
    if len(frm_trace) != len(rtl_trace):
        return {"match": False, "first_diverge": n,
                "frm": "<end>" if n == len(frm_trace) else frm_trace[n],
                "rtl": "<end>" if n == len(rtl_trace) else rtl_trace[n]}
    return {"match": True, "first_diverge": -1, "frm": "", "rtl": "",
            "events": len(frm_trace)}


# --------------------------------------------------------------------------
# RTL side: Verilator --cc build (cached by RTL hash) + execution.
# Windows reaches the toolchain via WSL; Linux runs natively (CI-safe).
# --------------------------------------------------------------------------

def _mnt(path: str) -> str:
    if os.name == "nt":
        return "/mnt/" + path[0].lower() + path[2:].replace("\\", "/")
    return path


def _wsl(cmd: list[str]) -> list[str]:
    return ["wsl"] + cmd if os.name == "nt" else cmd


def rtl_hash(rtl_path: str = DEFAULT_RTL) -> str:
    h = hashlib.sha256()
    with open(rtl_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def tool_ok() -> bool:
    """Verilator reachable (plus g++/make where needed for --cc builds)."""
    if os.name == "nt":
        return shutil.which("wsl") is not None
    return shutil.which("verilator") is not None


def build_sim(rtl_path: str = DEFAULT_RTL, workdir: str = "",
              timeout_s: int = BUILD_TIMEOUT_S) -> str:
    """Verilate + compile the C++ driver. Returns binary path. Rebuilds only
    when the RTL hash changes (obj dir keyed by hash). Raises on failure."""
    workdir = workdir or tempfile.mkdtemp(prefix="wbsim_")
    os.makedirs(workdir, exist_ok=True)
    tag = rtl_hash(rtl_path)
    obj = os.path.join(workdir, f"obj_{tag}")
    binary = os.path.join(obj, "Vwb_dma")
    if os.path.isfile(binary):
        return binary
    cmd = _wsl(["verilator", "--cc", "--exe", "--build", "-j", "4",
                "--top-module", "wb_dma", "-Mdir", _mnt(obj),
                # Known-benign RTL properties (recorded by lint, unchanged
                # here): WIDTHEXPAND on reg_sel slice, CASEINCOMPLETE on the
                # register case (default arm covers the rest). Every OTHER
                # warning still fails the build — fail-closed preserved.
                "-Wno-WIDTHEXPAND", "-Wno-CASEINCOMPLETE",
                _mnt(rtl_path), _mnt(TB_CPP)])
    p = subprocess.run(cmd, capture_output=True, text=True,
                       timeout=timeout_s, cwd=workdir)
    log = (p.stdout or "") + (p.stderr or "")
    if p.returncode != 0 or not os.path.isfile(binary):
        raise RuntimeError("verilator build failed:\n" + log[-3000:])
    return binary


def run_sim(binary: str, lines: list[str],
            timeout_s: int = RUN_TIMEOUT_S) -> list[str]:
    """Execute validated stimulus through the RTL sim. Returns trace lines."""
    clean = validate_stim(lines)
    with tempfile.NamedTemporaryFile("w", suffix=".stim", delete=False,
                                     encoding="utf-8") as f:
        f.write("\n".join(clean) + "\n")
        stim = f.name
    try:
        bin_run = binary if os.name != "nt" else _mnt(binary)
        stim_run = stim if os.name != "nt" else _mnt(stim)
        p = subprocess.run(_wsl([bin_run, stim_run]), capture_output=True,
                           text=True, timeout=timeout_s)
        if p.returncode != 0:
            raise RuntimeError("sim run failed:\n" + (p.stderr or "")[-2000:])
        return [ln.strip() for ln in (p.stdout or "").splitlines()
                if ln.strip()]
    finally:
        try:
            os.unlink(stim)
        except OSError:
            pass


def co_sim(lines: list[str], rtl_path: str = DEFAULT_RTL,
           workdir: str = "") -> dict:
    """Same stimulus through FRM and RTL sim. Verdict: exact trace match."""
    frm = WbDmaFrm()
    frm_trace = frm.run_stim(lines)
    binary = build_sim(rtl_path, workdir or tempfile.mkdtemp(prefix="wbsim_"))
    rtl_trace = run_sim(binary, lines)
    cmp = compare_traces(frm_trace, rtl_trace)
    cmp.update({"frm_trace": frm_trace, "rtl_trace": rtl_trace,
                "rtl_hash": rtl_hash(rtl_path)})
    return cmp


def grade_llm_stimulus(lines: list[str], must_complete_transfer: bool = True,
                       **kw) -> dict:
    """Constrained LLM stimulus round: DSL validated, co-simulated, and (for
    transfer programs) checked for completion. Returns a verdict dict for
    the ledger. DSL violations raise ValueError (rejected, never simulated).
    """
    res = co_sim(lines, **kw)
    completed = any("IRQ 1" in t for t in res["frm_trace"])
    verdict = res["match"] and (completed or not must_complete_transfer)
    return {"sim_equiv": res["match"], "transfer_completed": completed,
            "verdict": verdict, "events": len(res["frm_trace"]),
            "first_diverge": res["first_diverge"],
            "frm_only": res["frm"], "rtl_only": res["rtl"]}


STIM_SLOT_LABELS = ("SRC", "DST", "COUNT", "CTRL", "IRQEN", "WAIT")
STIM_SLOT_PROMPT = """Program a DMA transfer by filling EXACTLY these six lines
and nothing else (plain hex, no 0x prefix):
SRC: <source byte address>
DST: <destination byte address>
COUNT: <word count 1-4>
CTRL: <control byte: bit0=start, bit1=src-incr, bit2=dst-incr>
IRQEN: <1 to enable interrupt, else 0>
WAIT: <idle cycles to let the transfer finish, 10-200>
Example values (NOT the answer — compute your own): 1-word transfer from
0x1000 to 0x2000 is SRC 1000, DST 2000, COUNT 1, CTRL 7, IRQEN 1, WAIT 40."""


def assemble_stim(text: str) -> list[str] | None:
    """Slot fills -> validated DSL program (RST, register writes, wait,
    status read). Returns None on any malformed slot. All-or-nothing."""
    from skeletons import parse_slots
    slots = parse_slots(text, STIM_SLOT_LABELS)
    if slots is None:
        return None
    try:
        src, dst = int(slots["SRC"], 16), int(slots["DST"], 16)
        count, ctrl = int(slots["COUNT"], 16), int(slots["CTRL"], 16)
        irqen, wait = int(slots["IRQEN"], 16), int(slots["WAIT"], 16)
    except ValueError:
        return None
    if not (0 <= src <= 0xFFFFFFFF and 0 <= dst <= 0xFFFFFFFF):
        return None
    if not (1 <= count <= 4 and 0 <= ctrl <= 0xF and irqen in (0, 1)
            and 10 <= wait <= 200):
        return None
    if not (ctrl & 0x1):
        return None  # start bit required: a program that never starts
    return ["rst", f"w 0 {src:08x}", f"w 4 {dst:08x}", f"w 8 {count:x}",
            f"w c {ctrl:x}", f"w 14 {irqen:x}", f"tick {wait}", "r 10"]
