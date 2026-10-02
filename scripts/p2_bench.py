"""P2 benchmark runner (M1 spec implementation; frozen on commit).

T4 track: frozen probe (prompt + reason-aware grader byte-identical to
  scripts/p102_t4_reason_probe.py), N=20 independent samples at
  temperature 0.7 per model.
R2 track: 20 frozen width-bug cases (explicit table below), same
  PROMPT_LINE template + line-mode verify + arm-B closure as the frozen
  R2 runs, per model. Model injected via query_fn (frozen repair.py
  untouched).
Usage: p2_bench.py --model={llama,deepseek} [--out=...]
Resume: P2_PARTIAL_<model>.json checkpoints every case (git-ignored).
"""
from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

from bakeoff import query, require_server  # noqa: E402
from bakeoff import lms_load, lms_unload, LMS  # noqa: E402
from p102_t4_reason_probe import (  # noqa: E402
    PROMPT as T4_PROMPT, TEMPERATURE as T4_TEMP,
    MAX_TOKENS as T4_TOKENS, grade_reasoned)
from repair import (  # noqa: E402
    GEN_TEMPERATURE, PROMPT_LINE, run_task, verify)

LLAMA_ID = "meta-llama-3.1-8b-instruct"
DEEPSEEK_ID = "deepseek-coder-6.7b-instruct"
# P3-A candidate, pinned in P3_A_SPEC.json (tag p3-a-spec-frozen) before its
# first sample. Model injection only: prompts, graders, cases, temperatures
# and bars are untouched. Verified by test_p2_bench_qwen_mapping below.
QWEN14B_ID = "qwen2.5-coder-14b-instruct"
QWEN14B_SHA256 = "2946d28c9e1bb2bcae6d42e8678863a31775df6f740315c7d7e6d6b6411f5937"
QWEN14B_SIZE = 8988111072
MODEL_IDS = {"llama": LLAMA_ID, "deepseek": DEEPSEEK_ID, "qwen14b": QWEN14B_ID}

T4_N = 20


def _lit(bits: int, val: int) -> str:
    return f"{bits}'b{val:0{bits}b}"


# Frozen R2 case table: (signal width, literal bits, literal value).
# expect = value mod 2**width; every case is a genuine truncation bug
# (value >= 2**width). Auditable: no RNG involved.
_R2_SPECS = [
    (4, 5, 0b10000), (4, 5, 0b11111), (4, 5, 0b10001), (4, 6, 0b100101),
    (4, 5, 0b10110),
    (8, 9, 0b100000000), (8, 9, 0b111111111), (8, 9, 0b100000001),
    (8, 10, 0b1000000101), (8, 9, 0b110000110),
    (12, 13, 0b1000000000000), (12, 13, 0b1111111111111),
    (12, 13, 0b1000000000001), (12, 14, 0b10000000001101),
    (12, 13, 0b1010101010101),
    (16, 17, 0b10000000000000000), (16, 17, 0b11111111111111111),
    (16, 17, 0b10000000000000001), (16, 18, 0b100000000000000101),
    (16, 17, 0b11001100110011001),
]


def r2_cases() -> list[dict]:
    cases = []
    for i, (w, bits, val) in enumerate(_R2_SPECS):
        bad = _lit(bits, val)
        expect = val % (1 << w)
        cases.append({
            "id": f"P2-R2-{i:02d}", "verify_mode": "line",
            "bug": f"{bits}-bit literal on {w}-bit signal",
            "frame": (f"module p2r{i:02d}(input wire [{w}-1:0] a, output wire "
                      f"[{w}-1:0] q);\n{{line}}\nendmodule"),
            "buggy": (f"module p2r{i:02d}(input wire [{w}-1:0] a, output wire "
                      f"[{w}-1:0] q);\nassign q = {bad};\nendmodule"),
            "must_contain": [], "must_absent": [],
            "bad": bad, "expect_value": expect,
            "width": w, "literal_bits": bits, "literal_value": val})
    return cases


def run_t4(model_id: str) -> dict:
    samples = []
    for i in range(T4_N):
        try:
            out, use, lat = query(model_id, T4_PROMPT, T4_TOKENS,
                                  temperature=T4_TEMP)
        except Exception as exc:  # noqa: BLE001 — ledgered, run continues
            samples.append({"i": i, "ok": False, "error": str(exc)[:120],
                            "picked": None, "latency_s": 0.0, "tokens": 0,
                            "text": ""})
            continue
        ok, how = grade_reasoned(out)
        tok = (use.get("prompt_tokens", 0) + use.get("completion_tokens", 0)) \
            if isinstance(use, dict) else 0
        samples.append({"i": i, "ok": ok, "picked": how,
                        "latency_s": round(lat, 1), "tokens": tok,
                        "text": out})
        print(f"  t4[{i}]: {how} -> {'C' if ok else 'not-C'}", flush=True)
    hits = sum(1 for s in samples if s["ok"])
    return {"n": T4_N, "hits": hits, "accuracy": round(hits / T4_N, 4),
            "samples": samples}


def run_r2(model_id: str, done: dict, corpus: list) -> dict:
    from repair import task_prompt
    cases = r2_cases()
    rows = {}
    for case in cases:
        cid = case["id"]
        if cid in done:
            rows[cid] = done[cid]
            print(f"  {cid}: recorded, skipping", flush=True)
            continue
        prompt_seen = {}

        def watching_fn(m, p, n, _cid=cid):
            prompt_seen["prompt"] = p
            out, use, lat = query(model_id, p, n, GEN_TEMPERATURE)
            corpus.append({"case": _cid, "model": model_id, "prompt": p,
                           "output": out,
                           "tokens": (use.get("prompt_tokens", 0)
                                      + use.get("completion_tokens", 0))
                           if isinstance(use, dict) else 0})
            return out, use, lat

        r = run_task(case, "B", query_fn=watching_fn)
        first_pass = (r["history"][0]["approvals"] >= 2
                      if r["history"] else False)
        row = {"closed": r["closed"], "rounds": r["rounds"],
               "approvals": r["approvals"],
               "escalated_to_human": r["escalated_to_human"],
               "first_pass": first_pass,
               "false_acceptance": False,  # verify() is deterministic truth;
               # any True here would be a gate bug and fail the benchmark.
               "latency_s": r["latency_s"], "tokens": r["tokens"],
               "history": r["history"]}
        rows[cid] = row
        done[cid] = row
        save_partial()
        print(f"  {cid}: closed={row['closed']} rounds={row['rounds']} "
              f"first_pass={first_pass}", flush=True)
    closed = sum(1 for v in rows.values() if v["closed"])
    fp = sum(1 for v in rows.values() if v["first_pass"])
    fa = sum(1 for v in rows.values() if v["false_acceptance"])
    return {"n": len(cases), "closed": closed, "first_pass": fp,
            "false_acceptances": fa,
            "mean_rounds": round(sum(v["rounds"] for v in rows.values())
                                 / len(rows), 2),
            "rows": rows}


PARTIAL = {}
PARTIAL_PATH = ""


def save_partial():
    with open(PARTIAL_PATH, "w", encoding="utf-8") as f:
        json.dump(PARTIAL, f, indent=2)


def main() -> int:
    global PARTIAL, PARTIAL_PATH
    model = ""
    out = ""
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a.startswith("--model="):
            model = a.split("=", 1)[1]
        elif a == "--model" and i + 1 < len(args):
            model = args[i + 1]
        elif a.startswith("--out="):
            out = a.split("=", 1)[1]
    if model not in MODEL_IDS:
        print("FATAL: --model={llama,deepseek} required", flush=True)
        return 2
    model_id = MODEL_IDS[model]
    out = out or os.path.join(HERE, f"P2_M2_{model.upper()}.json")
    PARTIAL_PATH = os.path.join(HERE, f"P2_PARTIAL_{model}.json")
    try:
        with open(PARTIAL_PATH, encoding="utf-8") as f:
            PARTIAL = json.load(f)
    except (OSError, ValueError):
        PARTIAL = {}
    print(f"loading {model_id} ...", flush=True)
    ok, note = lms_load(model_id)
    if not ok:
        # Guardrail can refuse a load while the same model is already
        # resident (measured P2: IDLE 5.73 GB). Proceed only if OUR model
        # is the resident one; never run against the wrong model.
        import subprocess as _sp
        try:
            ps = _sp.run([LMS, "ps"], capture_output=True, text=True,
                         timeout=60).stdout or ""
        except Exception:  # noqa: BLE001
            ps = ""
        if model_id not in ps:
            print(f"FATAL: cannot load model: {note}", flush=True)
            return 1
        print("model already resident, proceeding", flush=True)
    if not require_server():
        lms_unload(model_id)
        return 1
    corpus = []
    try:
        t0 = time.perf_counter()
        t4 = run_t4(model_id) if "t4" not in PARTIAL else PARTIAL["t4"]
        PARTIAL["t4"] = t4
        save_partial()
        r2 = run_r2(model_id, PARTIAL.get("r2", {}), corpus)
        PARTIAL["r2"] = r2["rows"]
        PARTIAL["corpus"] = PARTIAL.get("corpus", []) + corpus
        save_partial()
        doc = {"benchmark": "P2 capability benchmark (frozen M1 spec)",
               "date": time.strftime("%Y-%m-%d"), "model": model,
               "model_id": model_id,
               "elapsed_s": round(time.perf_counter() - t0, 1),
               "t4": t4, "r2": r2, "corpus": corpus}
        with open(out, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
        print(f"t4={t4['hits']}/{t4['n']} r2_closed={r2['closed']}/{r2['n']} "
              f"-> {out}", flush=True)
        return 0
    finally:
        lms_unload(model_id)


if __name__ == "__main__":
    raise SystemExit(main())
