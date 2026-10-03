"""P3-A amendment A1: T4 re-measurement for Qwen under a recorded 3600s
per-call timeout. Everything else is frozen-identical: same prompt
(byte-identical), same grader, same temperature, 20 FRESH samples.
bakeoff.py is untouched — the extended timeout lives only in this script.

Timeouts are recorded as timeouts, never scored as wrong.
Usage: p3a_t4_remeasure.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

from bakeoff import (ENDPOINT, LMS, lms_load, lms_unload,  # noqa: E402
                     require_server)
from p102_t4_reason_probe import (  # noqa: E402
    MAX_TOKENS as T4_TOKENS, PROMPT as T4_PROMPT,
    TEMPERATURE as T4_TEMP, grade_reasoned)

MODEL_ID = "qwen2.5-coder-14b-instruct"
GOLD = "C"
N = 20
TIMEOUT_S = 3600  # amendment A1: 600 -> 3600, T4 track only
PARTIAL_PATH = os.path.join(HERE, "P3_A_T4_REMEASURE_PARTIAL.json")
OUT = os.path.join(HERE, "P3_A_T4_REMEASURE.json")


def save(partial):
    with open(PARTIAL_PATH, "w", encoding="utf-8") as f:
        json.dump(partial, f, indent=2)


def one_call(prompt: str) -> tuple[str, dict, float, str | None]:
    body = json.dumps({"model": MODEL_ID,
                       "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": T4_TOKENS,
                       "temperature": T4_TEMP}).encode()
    req = urllib.request.Request(ENDPOINT, data=body,
                                 headers={"Content-Type": "application/json"})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            data = json.load(r)
    except Exception as exc:  # noqa: BLE001 — recorded as timeout, run goes on
        return "", {}, 0.0, f"timeout@{TIMEOUT_S}s: {str(exc)[:120]}"
    latency = time.perf_counter() - start
    msg = data["choices"][0]["message"]["content"] or ""
    return msg, data.get("usage", {}), latency, None


def main() -> int:
    try:
        with open(PARTIAL_PATH, encoding="utf-8") as f:
            partial = json.load(f)
    except (OSError, ValueError):
        partial = {}
    print(f"loading {MODEL_ID} ...", flush=True)
    ok, note = lms_load(MODEL_ID)
    if not ok:
        import subprocess as _sp
        ps = ""
        try:
            ps = _sp.run([LMS, "ps"], capture_output=True, text=True,
                         timeout=60).stdout or ""
        except Exception:  # noqa: BLE001
            pass
        if MODEL_ID not in ps:
            print(f"FATAL: cannot load model: {note}", flush=True)
            return 1
        print("model already resident, proceeding", flush=True)
    if not require_server():
        lms_unload(MODEL_ID)
        return 1
    try:
        rows = partial.setdefault("samples", {})
        for i in range(N):
            key = str(i)
            if key in rows:
                print(f"  t4[{i}]: recorded", flush=True)
                continue
            text, use, lat, err = one_call(T4_PROMPT)
            if err or not text.strip():
                rows[key] = {"i": i, "ok": False, "picked": None,
                             "latency_s": round(lat, 1),
                             "tokens": 0, "text": text,
                             "error": err or "empty"}
            else:
                ok, how = grade_reasoned(text)
                tok = (use.get("prompt_tokens", 0)
                       + use.get("completion_tokens", 0)) \
                    if isinstance(use, dict) else 0
                rows[key] = {"i": i, "ok": ok, "picked": how,
                             "latency_s": round(lat, 1), "tokens": tok,
                             "text": text}
            save(partial)
            r = rows[key]
            print(f"  t4[{i}]: {r.get('picked')} "
                  f"-> {'C' if r['ok'] else 'not-C'} "
                  f"{r['latency_s']}s {r.get('error', '')}", flush=True)
        vals = list(rows.values())
        done = [v for v in vals if "error" not in v]
        timed_out = [v for v in vals if "error" in v]
        hits = sum(1 for v in done if v["ok"])
        doc = {"track": "P3-A T4 re-measurement (amendment A1)",
               "spec_tag": "p3-a-spec-frozen",
               "amendment": "A1 (timeout 600 -> 3600s, T4 only)",
               "model": "qwen2.5-coder-14b",
               "model_id": MODEL_ID, "date": time.strftime("%Y-%m-%d"),
               "prompt": "byte-identical to frozen probe",
               "temperature": T4_TEMP, "max_tokens": T4_TOKENS, "gold": GOLD,
               "n": N, "completed": len(done), "timed_out": len(timed_out),
               "hits": hits,
               "accuracy": round(hits / N, 4) if not timed_out else None,
               "accuracy_note": "Computed over all 20 only if all 20 "
                                "complete; otherwise T4 remains UNMEASURED.",
               "samples": rows}
        with open(OUT, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
        print(f"completed={len(done)}/{N} timed_out={len(timed_out)} "
              f"hits={hits} -> {OUT}", flush=True)
        return 0
    finally:
        lms_unload(MODEL_ID)


if __name__ == "__main__":
    raise SystemExit(main())
