"""R-2b: derive real-design R2 cases from WIDTH-clean rideprotect blocks.

Deterministic authoring (no model): for each pre-listed target line, the
frame is the full module with brace-escaping + {line} slot (frozen
str.format path untouched), good = original line, buggy = injected
oversized literal. Each case validated with frozen repair.verify:
good -> all True, buggy -> not all True. Writes P3_R2B_REAL.json.

Usage: make_r2b_real.py
"""
from __future__ import annotations

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

from repair import verify  # noqa: E402

RTL = "/mnt/c/Projects/ChipDesign/rideprotect-rv/rtl"
OUT = os.path.join(HERE, "P3_R2B_REAL.json")

TARGETS = [
    ("wb_hslink.v", r"^\s*assign hstx_p = 1'b0;\s*$",
     "assign hstx_p = 2'b00;", "2'b00", 0, 1),
    ("wb_hslink.v", r"^\s*assign hstx_n = 1'b0;\s*$",
     "assign hstx_n = 2'b00;", "2'b00", 0, 1),
    ("wb_shared_bus.v", r"^\s*assign m0_wb_dat_r = .*;\s*$",
     None, "33'h000000000", 0, 32),
    ("wb_shared_bus.v", r"^\s*assign m1_wb_dat_r = .*;\s*$",
     None, "33'h000000000", 0, 32),
    ("wb_shared_bus.v", r"^\s*assign m0_wb_ack\s+= .*;\s*$",
     None, "2'b00", 0, 1),
    ("wb_shared_bus.v", r"^\s*assign m1_wb_ack\s+= .*;\s*$",
     None, "2'b00", 0, 1),
    ("wb_sram.v", r"^\s*assign s_wb_dat_r = .*;\s*$",
     None, "33'h000000000", 0, 32),
    ("wb_uart.v", r"^\s*assign uart_tx = .*;\s*$",
     None, "2'b01", 1, 1),
    ("jtag_tap.v", r"^\s*assign capture_data = .*;\s*$",
     None, "33'h000000000", 0, 32),
    ("hslink_phy_selectio.v", r"^\s*assign ser_tx = .*;\s*$",
     None, "2'b01", 1, 1),
    ("hslink_phy_selectio.v", r"^\s*assign ser_tx_p = .*;\s*$",
     None, "2'b01", 1, 1),
]

# For ternary lines (bad=None): oversize the fallback literal in place.
FALLBACK = [(r"1'b0\b", "2'b00"), (r"1'b1\b", "2'b01"),
            (r"32'h00000000\b", "33'h000000000")]


def main() -> int:
    cases = []
    for idx, (fname, pat, bad_line, bad, expect, w) in enumerate(TARGETS):
        code = open(os.path.join(RTL, fname), encoding="utf-8").read()
        m = re.search(pat, code, re.M)
        if not m:
            print(f"FATAL: target not found: {fname} {pat}", flush=True)
            return 1
        orig = m.group(0)
        ind = orig[:len(orig) - len(orig.lstrip())]
        if bad_line is not None:
            buggy_line = ind + bad_line
            good_line = orig.strip()
        else:
            buggy_line, n = orig, 0
            for old, new in FALLBACK:
                buggy_line, k = re.subn(old, new, buggy_line, count=1)
                n += k
                if n:
                    break
            if not n:
                print(f"FATAL: no fallback literal in {fname}: {orig[:80]}",
                      flush=True)
                return 1
            good_line = orig.strip()
            buggy_line = buggy_line.strip()
        assert bad in buggy_line and bad not in good_line, (fname, orig[:80])
        frame = (code.replace(orig, "\x00").replace("{", "{{")
                     .replace("}", "}}").replace("\x00", "{line}"))
        task = {"id": f"R2B-R-{idx:02d}", "verify_mode": "line",
                "bug": f"oversized literal on {w}-bit signal ({fname})",
                "frame": frame,
                "buggy": code.replace(orig, buggy_line),
                "must_contain": [], "must_absent": [],
                "bad": bad, "expect_value": expect, "width": w,
                "source_file": fname, "source_line": good_line}
        gv, _ = verify(task, good_line)
        bv, _ = verify(task, buggy_line)
        ok = all(gv.values()) and not all(bv.values())
        print(f"  R2B-R-{idx:02d} {fname} w={w} good={all(gv.values())} "
              f"buggy_fails={not all(bv.values())}", flush=True)
        if not ok:
            print("FATAL: validation failed", flush=True)
            return 1
        task["validation"] = {"good_verdicts": gv, "buggy_verdicts": bv}
        task["good_line"] = good_line
        task["buggy_line"] = buggy_line
        cases.append(task)
    doc = {"track": "P3-R-2b real-design R2 family (pre-registration)",
           "status": "UNFROZEN — awaits human freeze approval before any "
                     "model runs on these cases",
           "family": "rideprotect-rv real blocks (6 files)",
           "rules": ("Full-module frames from WIDTH-clean files; frozen "
                     "repair.verify; brace-escaped {line} slot; frozen "
                     "recipe untouched."),
           "n": len(cases), "cases": cases}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    print(f"n={len(cases)} -> {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
