"""R-3: collect R5 model trajectories (single-shot generation + frozen
verification per case per model). Writes R5_TRAJECTORIES.json — the exact
filename the frozen P3-D assessor checks for third-wall trajectories.

Checkpoints per case-model so the run is resumable. Timeouts recorded as
errors, never scored. No training, no training formatting.
Usage: r5_collect.py
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
from repair import task_prompt, verify  # noqa: E402

MODELS = {"llama": ("meta-llama-3.1-8b-instruct", 600),
          "qwen": ("qwen2.5-coder-14b-instruct", 3600)}
MAX_TOKENS = 128
TEMPERATURE = 0.7
PARTIAL_PATH = os.path.join(HERE, "R5_PARTIAL.json")
OUT = os.path.join(HERE, "R5_TRAJECTORIES.json")
SPEC_TAG = "p3-r5-bench-frozen"


def save(partial):
    with open(PARTIAL_PATH, "w", encoding="utf-8") as f:
        json.dump(partial, f, indent=2)


def one_call(model_id, prompt, timeout):
    body = json.dumps({"model": model_id,
                       "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": MAX_TOKENS,
                       "temperature": TEMPERATURE}).encode()
    req = urllib.request.Request(ENDPOINT, data=body,
                                 headers={"Content-Type": "application/json"})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except Exception as exc:  # noqa: BLE001
        return "", {}, 0.0, f"timeout@{timeout}s: {str(exc)[:120]}"
    latency = time.perf_counter() - start
    msg = data["choices"][0]["message"]["content"] or ""
    return msg, data.get("usage", {}), latency, None


def run_model(short, model_id, timeout, cases, rows):
    print(f"loading {model_id} ...", flush=True)
    ok, note = lms_load(model_id)
    if not ok:
        import subprocess as _sp
        ps = ""
        try:
            ps = _sp.run([LMS, "ps"], capture_output=True, text=True,
                         timeout=60).stdout or ""
        except Exception:  # noqa: BLE001
            pass
        if model_id not in ps:
            print(f"FATAL: cannot load model: {note}", flush=True)
            return False
        print("model already resident, proceeding", flush=True)
    if not require_server():
        lms_unload(model_id)
        return False
    try:
        for case in cases:
            key = f"{short}:{case['id']}"
            if key in rows:
                print(f"  {key}: recorded", flush=True)
                continue
            prompt = task_prompt(case)
            text, use, lat, err = one_call(model_id, prompt, timeout)
            if err or not text.strip():
                rows[key] = {"case": case["id"], "model": short,
                             "prompt": prompt, "output": text,
                             "passed": False, "latency_s": round(lat, 1),
                             "tokens": 0, "error": err or "empty"}
            else:
                verdicts, _ = verify(case, text)
                tok = (use.get("prompt_tokens", 0)
                       + use.get("completion_tokens", 0)) \
                    if isinstance(use, dict) else 0
                rows[key] = {"case": case["id"], "model": short,
                             "prompt": prompt, "output": text,
                             "verdicts": verdicts,
                             "passed": bool(all(verdicts.values())),
                             "latency_s": round(lat, 1), "tokens": tok}
            save({"spec_tag": SPEC_TAG, "rows": rows})
            r = rows[key]
            print(f"  {key}: passed={r['passed']} {r['latency_s']}s "
                  f"{r.get('error', '')}", flush=True)
        return True
    finally:
        lms_unload(model_id)


def main() -> int:
    with open(os.path.join(HERE, "P3_R5_FAMILY.json"),
              encoding="utf-8") as f:
        bench = json.load(f)
    if bench.get("status", "").find("p3-r5-bench-frozen") < 0:
        print("FATAL: bench not frozen; refusing to run models on it",
              flush=True)
        return 1
    try:
        with open(PARTIAL_PATH, encoding="utf-8") as f:
            partial = json.load(f)
    except (OSError, ValueError):
        partial = {}
    if partial.get("spec_tag") != SPEC_TAG:
        partial = {"spec_tag": SPEC_TAG, "rows": {}}
    rows = partial.get("rows", {})
    cases = bench["cases"]
    for short, (mid, tout) in MODELS.items():
        if not run_model(short, mid, tout, cases, rows):
            return 1
        save({"spec_tag": SPEC_TAG, "rows": rows})
    vals = list(rows.values())
    doc = {"track": "P3-R-3 R5 trajectories (model generations + frozen "
                    "verification)",
           "spec_tag": SPEC_TAG, "n": len(vals),
           "passed": sum(1 for v in vals if v.get("passed")),
           "failed": sum(1 for v in vals if not v.get("passed")),
           "errors": sum(1 for v in vals if "error" in v),
           "trajectories": rows}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    print(f"n={len(vals)} passed={doc['passed']} failed={doc['failed']} "
          f"errors={doc['errors']} -> {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
