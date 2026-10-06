"""R-2a: author + verifier-validate the frozen R5 family (declline).

Shape mirrors frozen REPAIR_TASKS R5-double exactly: buggy module with an
undeclared signal + one oversized literal; model replies DECL: + ASSIGN:.
Each case validated with frozen repair.verify: known-good pair passes all
verdicts, buggy module fails. Writes P3_R5_FAMILY.json (bench only — no
model outputs; trajectories are collected separately by r5_collect.py).

Usage: make_r5_family.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

from repair import verify  # noqa: E402

OUT = os.path.join(HERE, "P3_R5_FAMILY.json")

# (width, op, signal, bad_value): bad is (width+1)-bit, expect = bad - 2**w.
# Signals must all contain "c": frozen verify calls extract_decl(text)
# with its default signal="c" (repair.py:127,158), a property of the frozen
# R5-double recipe. Names stay distinct per case.
SPECS = [
    (4, "+", "c", 0b10000), (4, "-", "sc", 0b11111),
    (4, "&", "ec", 0b10101), (4, "|", "ic", 0b11011),
    (6, "+", "oc", 0b1000000), (6, "^", "uc", 0b1111111),
    (6, "-", "ac", 0b1000010),
    (8, "+", "bc", 0b100000000), (8, "&", "dc", 0b111111111),
    (8, "|", "fc", 0b101010101),
    (10, "+", "gc", 0b10000000000), (10, "-", "hc", 0b11111111111),
    (12, "+", "jc", 0b1000000000000), (12, "^", "kc", 0b1111000011111),
    (12, "&", "lc", 0b1010101010101),
    (16, "+", "mc", 0b10000000000000000),
    (16, "|", "nc", 0b11111111111111111),
    (16, "-", "pc", 0b10000000000000001),
    (8, "^", "qc", 0b100110011),
    (12, "|", "rc", 0b1100110011001),
]


def lit(bits, val):
    return f"{bits}'b{val:0{bits}b}"


def main() -> int:
    cases = []
    for i, (w, op, sig, badval) in enumerate(SPECS):
        bad = lit(w + 1, badval)
        expect = badval % (1 << w)
        good_lit = lit(w, expect)
        decl = f"wire [{w - 1}:0] {sig};"
        good = (f"DECL: {decl}\n"
                f"ASSIGN: assign y = a {op} {sig} + {good_lit};")
        buggy = (f"module r5h{i:02d}(input wire [{w}-1:0] a, "
                 f"output wire [{w}-1:0] y);\n"
                 f"assign y = a {op} {sig} + {bad};\nendmodule")
        task = {"id": f"R5H-{i:02d}", "verify_mode": "declline",
                "bug": f"undeclared signal {sig} AND {w + 1}-bit literal "
                       f"on {w}-bit signal",
                "frame": (f"module r5h{i:02d}(input wire [{w}-1:0] a, "
                          f"output wire [{w}-1:0] y);\n"
                          f"{{decl}}\n{{line}}\nendmodule"),
                "buggy": buggy, "must_contain": [], "must_absent": [],
                "bad": bad, "expect_value": expect,
                "decl_must": ["wire", f"[{w - 1}:0]", sig],
                "decl_must_absent": ["input", "output"],
                "width": w, "signal": sig}
        gv, _ = verify(task, good)
        bv, _ = verify(task, buggy)
        ok = all(gv.values()) and not all(bv.values())
        print(f"  R5H-{i:02d} w={w} op={op} good={all(gv.values())} "
              f"buggy_fails={not all(bv.values())}", flush=True)
        if not ok:
            print("FATAL: validation failed", flush=True)
            return 1
        task["validation"] = {"good_verdicts": gv, "buggy_verdicts": bv}
        task["good_text"] = good
        cases.append(task)
    doc = {"track": "P3-R-2a R5 family bench (frozen cases, no model runs)",
           "status": "FROZEN under tag p3-r5-bench-frozen",
           "shape": "mirrors frozen REPAIR_TASKS R5-double (declline); "
                    "frozen repair.verify; frozen recipe untouched",
           "prompt": "repair.PROMPT_DECLLINE template via task_prompt",
           "temperature": 0.7,
           "n": len(cases), "cases": cases}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    print(f"n={len(cases)} -> {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
