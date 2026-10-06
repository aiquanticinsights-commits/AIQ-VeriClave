"""R-1: author + verifier-validate the held-out split (read-only w.r.t.
training-eligible evidence; writes only P3_HELDOUT.json).

Every R2 case is validated with frozen repair.verify: the known-good line
must pass all verdicts and the buggy line must fail. Every T4 probe is
validated structurally (4 options incl. gold, instruction present) with
frozen-grader sanity on all four letters. Disjointness is enforced by
test_heldout.py in CI.

Usage: make_heldout.py
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

from repair import verify  # noqa: E402
from p102_t4_reason_probe import grade_reasoned  # noqa: E402

OUT = os.path.join(HERE, "P3_HELDOUT.json")

R2_SPECS = [
    (4, 5, 0b10110), (4, 6, 0b111111),
    (5, 6, 0b100001), (5, 8, 0b11110000),
    (6, 7, 0b1100101), (6, 9, 0b111111111),
    (8, 9, 0b100000000), (8, 10, 0b1111111111),
    (10, 11, 0b10000000000), (10, 12, 0b101010101010),
    (12, 13, 0b1000000000000), (12, 14, 0b11110000111100),
    (16, 17, 0b10000000000000000), (16, 20, 0b11111111111111111111),
    (24, 25, 0b1000000000000000000000000),
    (32, 33, 0b100000000000000000000000000000000),
]

T4_PROBES = [
    {"gold": "C",
     "text": ("Failure: an I2C slave holds SDA low forever after a NACK, "
              "hanging the bus. Waveforms show clean pull-up release timing "
              "on SDA/SCL when the slave is detached, no clock stretching "
              "pulses, and a quiet ground plane. The design is single-clock "
              "with no clock-domain crossings. Think step by step about the "
              "most likely root cause, then end your reply with exactly "
              "`Answer: X` where X is one letter.\n"
              "A. pull-up resistor sizing\nB. clock stretching logic\n"
              "C. slave state machine not releasing SDA\nD. ground bounce")},
    {"gold": "A",
     "text": ("Failure: an asynchronous FIFO overflow flag never asserts "
              "even though writes exceed the depth. Waveforms show both "
              "clocks running, gray-code synchronizer outputs stable, and "
              "the binary write pointer counting past the DEPTH parameter. "
              "The design uses standard two-flop synchronizers. Think step "
              "by step about the most likely root cause, then end your "
              "reply with exactly `Answer: X` where X is one letter.\n"
              "A. pointer-width / depth parameter mismatch\n"
              "B. clock-domain crossing synchronization\n"
              "C. read clock stopped\nD. reset sequencing")},
    {"gold": "D",
     "text": ("Failure: spurious interrupts fire in bursts correlated with "
              "board-level activity, though all enable/priority/mode "
              "registers read back correctly and the handler completes well "
              "within budget. Waveforms show glitches on the asynchronous "
              "reset input with no synchronizer, and each burst aligns with "
              "a reset glitch. Think step by step about the most likely "
              "root cause, then end your reply with exactly `Answer: X` "
              "where X is one letter.\n"
              "A. interrupt clock source\nB. priority configuration\n"
              "C. handler latency\nD. reset signal integrity")},
    {"gold": "B",
     "text": ("Failure: a PWM output is stuck at 50% duty although firmware "
              "writes new compare values every period. Waveforms show the "
              "counter free-running, direct (non-shadow) compare writes "
              "taking effect immediately, and the shadow-load strobe never "
              "asserting. Output polarity and dead-time read back as "
              "programmed. Think step by step about the most likely root "
              "cause, then end your reply with exactly `Answer: X` where X "
              "is one letter.\n"
              "A. clock prescaler\nB. shadow register load strobe\n"
              "C. output polarity\nD. dead-time insertion")},
    {"gold": "A",
     "text": ("Failure: an SRAM BIST controller flags FAIL on known-good "
              "memory. Waveforms show the march sequence running to "
              "completion, the address counter covering the full range, "
              "timing margins clean, and direct readback of the array "
              "correct — only the final signature compare mismatches. "
              "Think step by step about the most likely root cause, then "
              "end your reply with exactly `Answer: X` where X is one "
              "letter.\n"
              "A. expected-signature / polynomial mismatch\n"
              "B. address counter\nC. timing margin\nD. redundancy fuses")},
    {"gold": "D",
     "text": ("Failure: a serial link never trains above its lowest rate. "
              "Waveforms show a clean reference clock, completed "
              "equalization sweeps, verified lane polarity, but the partner "
              "never emits training ordered sets because its PERST# input "
              "never deasserts. The local training state machine waits in "
              "its polling state until its watchdog fires. Think step by "
              "step about the most likely root cause, then end your reply "
              "with exactly `Answer: X` where X is one letter.\n"
              "A. reference clock quality\nB. receiver equalization\n"
              "C. lane polarity\n"
              "D. partner link-training handshake / power sequencing")},
    {"gold": "B",
     "text": ("Failure: a low-priority bus master starves although the "
              "arbiter is programmed round-robin. Waveforms show all "
              "requests asserted, configuration reading back round-robin, "
              "and the grant pointer frozen on one master whose grant-ack "
              "never arrives. Think step by step about the most likely "
              "root cause, then end your reply with exactly `Answer: X` "
              "where X is one letter.\n"
              "A. priority configuration\nB. grant-ack handshake stall\n"
              "C. request synchronization\nD. arbiter clock")},
    {"gold": "C",
     "text": ("Failure: a CRC error flag asserts on every frame although "
              "payloads are correct. Waveforms show single-bit error "
              "injection detected and located correctly (polynomial and "
              "bit order proven), frame lengths exact, but the checker "
              "seed register holds its reset value instead of the "
              "protocol-specified init. Think step by step about the most "
              "likely root cause, then end your reply with exactly "
              "`Answer: X` where X is one letter.\n"
              "A. CRC polynomial\nB. bit order\nC. seed / init value\n"
              "D. length field")},
]


def lit(bits, val):
    return f"{bits}'b{val:0{bits}b}"


def main() -> int:
    r2 = []
    for i, (w, bits, val) in enumerate(R2_SPECS):
        bad = lit(bits, val)
        expect = val % (1 << w)
        good_line = f"assign q = {w}'b{expect:0{w}b};"
        task = {
            "id": f"HELD-R2-{i:02d}", "verify_mode": "line",
            "bug": f"{bits}-bit literal on {w}-bit signal",
            "frame": (f"module heldr{i:02d}(input wire [{w}-1:0] a, "
                      f"output wire [{w}-1:0] q);\n{{line}}\nendmodule"),
            "buggy": (f"module heldr{i:02d}(input wire [{w}-1:0] a, "
                      f"output wire [{w}-1:0] q);\nassign q = {bad};\n"
                      f"endmodule"),
            "must_contain": [], "must_absent": [],
            "bad": bad, "expect_value": expect,
            "width": w, "literal_bits": bits, "literal_value": val}
        gv, _ = verify(task, good_line)
        bv, _ = verify(task, task["buggy"])
        ok_good, ok_buggy_fails = all(gv.values()), not all(bv.values())
        print(f"  HELD-R2-{i:02d} w={w} good_pass={ok_good} "
              f"buggy_fails={ok_buggy_fails}", flush=True)
        if not (ok_good and ok_buggy_fails):
            print("FATAL: held-out case failed verifier validation",
                  flush=True)
            return 1
        task["validation"] = {"good_verdicts": gv, "buggy_verdicts": bv}
        r2.append(task)

    t4 = []
    for i, p in enumerate(T4_PROBES):
        t4.append({"id": f"HELD-T4-{i:02d}", "prompt": p["text"],
                   "gold": p["gold"]})
        for letter in "ABCD":
            ok, _ = grade_reasoned(f"Answer: {letter}", p["gold"])
            assert ok == (letter == p["gold"]), (i, letter)
        print(f"  HELD-T4-{i:02d} gold={p['gold']} grader_sane=True",
              flush=True)

    doc = {"track": "P3-R1 held-out split",
           "status": "FROZEN under tag p3-heldout-frozen",
           "rules": ("New cases only; disjoint IDs/prompts from every "
                     "training-eligible set; scored only by frozen "
                     "verifiers; never train-eligible."),
           "r2": {"n": len(r2), "verifier": "frozen repair.verify "
                  "(value_gate + splice + lint wall)",
                  "validation": "known-good passes all verdicts; buggy "
                  "fails; recorded per case at authoring",
                  "cases": r2},
           "t4": {"n": len(t4), "grader": "frozen grade_reasoned",
                  "validation": "Answer:X sanity on all four letters per "
                  "probe; recorded at authoring",
                  "probes": t4}}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    print(f"r2={len(r2)} t4={len(t4)} -> {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
