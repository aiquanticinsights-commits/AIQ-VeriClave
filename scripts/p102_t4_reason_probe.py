"""P1-02 probe: T4 reason-then-letter grading (V4-authorized fallback).

Frozen P0 path untouched: this script queries the baseline 8B directly with
a reasoning-first T4 prompt and grades with a strict reason-aware grader
(final `Answer: X`, else last standalone A-D letter). Success bar (abort
criteria): >=3/5 samples select C (the correct option). Anything less and
the F1/T4 capability wall stands as documented.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from bakeoff import query, require_server  # noqa: E402

BASELINE_API_ID = "meta-llama-3.1-8b-instruct"
N_SAMPLES = 5
MAX_TOKENS = 256
TEMPERATURE = 0.7  # same diversity setting as P0-D BoN generation

PROMPT = ("Failure: after reset deasserts, dma_state stays S_READ "
          "forever although m_wb_ack pulses. Waveforms at the slave "
          "pads show m_wb_ack arriving cleanly every cycle, and the "
          "design is single-clock (no clock-domain crossings "
          "exist). Think step by step about the most likely root cause, "
          "then end your reply with exactly `Answer: X` where X is one "
          "letter.\n"
          "A. reset sequencing\nB. timeout counter\n"
          "C. state-machine ack handling\nD. clock-domain crossing")

ANS_RE = re.compile(r"Answer:\s*([A-D])", re.IGNORECASE)
LETTER_RE = re.compile(r"\b([A-D])\b")


def grade_reasoned(text: str, expected: str = "C") -> tuple[bool, str]:
    """Final marked answer wins; unmarked falls back to last letter (the
    conclusion, not the first mention — first-letter grading misgrades
    reasoning text, measured)."""
    m = ANS_RE.search(text)
    if m:
        return m.group(1).upper() == expected, "marked:" + m.group(1).upper()
    letters = LETTER_RE.findall(text)
    if not letters:
        return False, "no-letter"
    return letters[-1] == expected, "last:" + letters[-1]


def main() -> int:
    if not require_server():
        return 1
    samples = []
    for i in range(N_SAMPLES):
        try:
            out, use, lat = query(BASELINE_API_ID, PROMPT, MAX_TOKENS,
                                  temperature=TEMPERATURE)
        except Exception as e:  # noqa: BLE001 — infra fault, ledgered
            samples.append({"i": i, "ok": False, "error": str(e)[:120],
                            "picked": None, "latency_s": 0.0})
            continue
        ok, how = grade_reasoned(out)
        samples.append({"i": i, "ok": ok, "picked": how,
                        "latency_s": round(lat, 1),
                        "tokens": (use.get("prompt_tokens", 0)
                                   + use.get("completion_tokens", 0))
                        if isinstance(use, dict) else 0,
                        "text": out[:400]})
        print(f"sample {i}: {how} -> {'C' if ok else 'not-C'}", flush=True)
    hits = sum(1 for s in samples if s["ok"])
    moved = hits >= 3
    doc = {"probe": "P1-02-T4-reason-then-letter", "date": time.strftime("%Y-%m-%d"),
           "model": "llama-3.1-8b", "n": N_SAMPLES, "expected": "C",
           "hits": hits, "wall_moved": moved,
           "success_bar": ">=3/5 select C",
           "verdict": ("WALL MOVED — reason-then-letter rescues T4"
                       if moved else
                       "WALL STANDS — reasoning does not rescue T4 on 8B"),
           "samples": samples}
    out_path = os.path.join(HERE, "P1_02_T4_PROBE.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    print(f"hits={hits}/{N_SAMPLES} -> {doc['verdict']} -> {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
