"""P1-04 driver: portability extensions beyond the P0 smoke benchmark.

EXT-A (mutation/full): full 100-mutant seed-7 campaign on WSL vs inside
  aiq-vericlave:p0; per-mutant classification agreement (spot was 5).
EXT-B (image/rebuild): no-cache rebuild of the sby-smoke image + rerun;
  formal_result must reproduce SBY_SMOKE.json (Dockerfile reproducibility).

Frozen P0 artifacts untouched: WSL campaign uses an isolated partial file
and temp workdir; outputs go to P1_04_PORTABILITY_EXT.json only.
Out of scope (stated, not silent): cross-host portability — both legs run
on the same machine (WSL vs Docker), as in P0 E2.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

from run_portability_benchmark import sh  # noqa: E402


def wsl_full() -> dict:
    import unittest.mock
    import mutate
    import run_mutants
    from run_mutants import campaign
    from sim_frm import DEFAULT_RTL
    pool = mutate.seed_catalog([DEFAULT_RTL], 100000, seed=7)
    catalog = mutate.stratify(pool, 100, seed=7)
    workdir = tempfile.mkdtemp(prefix="p104wsl_")
    partial = os.path.join(workdir, "partial.json")
    with unittest.mock.patch.object(run_mutants, "partial_path",
                                    return_value=partial):
        results = campaign(catalog, workdir=workdir)
    return {"classifications": {mid: r["status"] for mid, r in
                                results.items()}}


def docker_full(rtl_host: str) -> dict:
    # Rebuild first (same as E2 docker_leg): the container script is new
    # repo content and must be baked into the image before running.
    rc, log = sh(["docker", "build", "-t", "aiq-vericlave:p0", "."],
                 timeout_s=1200)
    if rc != 0:
        return {"error": "image build failed: " + log[-1000:]}
    rtl_mnt = os.path.dirname(os.path.dirname(rtl_host)).replace("\\", "/")
    cmd = ("/opt/vericlave-venv/bin/python "
           "/work/AIQ-VeriClave/scripts/e2_docker_full.py --stdout")
    rc, log = sh(["docker", "run", "--rm",
                  "-v", f"{rtl_mnt}:/work/rideprotect-rv:ro",
                  "aiq-vericlave:p0", "sh", "-c", cmd],
                 timeout_s=1800)
    if rc != 0:
        return {"error": "docker full leg failed: " + log[-2000:]}
    seg = log.split("@@MUTFULL@@")
    if len(seg) < 2:
        return {"error": "missing @@MUTFULL@@ marker: " + log[-2000:]}
    doc, _ = json.JSONDecoder().raw_decode(seg[1].strip())
    return doc


def image_rebuild() -> dict:
    ctx = os.path.join(HERE, "docker", "sby-smoke")
    tag = "aiq-sby-smoke:p104-rebuild"
    rc, log = sh(["docker", "build", "--no-cache", "-t", tag, "."],
                 timeout_s=1800, cwd=ctx)
    if rc != 0:
        return {"reproduced": False, "detail": "rebuild failed: "
                + log[-1000:]}
    cname = "p104-smoke-rebuild"
    sh(["docker", "rm", "-f", cname], 60)
    rc, log = sh(["docker", "run", "--name", cname, tag], timeout_s=900)
    got = None
    try:
        if rc == 0:
            tmp = tempfile.mkdtemp(prefix="p104smoke_")
            got = os.path.join(tmp, "SBY_SMOKE.json")
            rcc, _ = sh(["docker", "cp",
                         f"{cname}:/smoke/SBY_SMOKE.json", got], 120)
            if rcc == 0 and os.path.isfile(got):
                with open(got, encoding="utf-8") as f:
                    doc = json.load(f)
                with open(os.path.join(HERE, "SBY_SMOKE.json"),
                          encoding="utf-8") as f:
                    frozen = json.load(f)
                same = (doc.get("formal_result")
                        == frozen.get("formal_result") == "PASS")
                return {"reproduced": same,
                        "detail": f"rebuild formal={doc.get('formal_result')} "
                        f"frozen={frozen.get('formal_result')}"}
    finally:
        sh(["docker", "rm", "-f", cname], 60)
    return {"reproduced": False,
            "detail": "rebuild ran but payload unreadable: " + log[-500:]}


def _row(name, category, ok: bool, detail: str) -> dict:
    return {"category": category,
            "variance": "none" if ok else "DIVERGED",
            "detail": detail[:160]}


def main() -> int:
    t0 = time.perf_counter()
    rtl_host = os.path.join(os.path.dirname(HERE), "rideprotect-rv", "rtl",
                            "wb_dma.v")
    if not os.path.isfile(rtl_host):
        print("FATAL: rideprotect RTL sibling missing", flush=True)
        return 2
    rows = {}
    print("== EXT-A: WSL full campaign ==", flush=True)
    wsl = wsl_full()
    print(f"wsl: {len(wsl['classifications'])} verdicts", flush=True)
    print("== EXT-A: docker full campaign ==", flush=True)
    dock = docker_full(rtl_host)
    if "error" in dock:
        rows["mutation/full"] = {"category": "mutation",
                                 "variance": "UNMEASURED",
                                 "detail": dock["error"][:160]}
    elif dock.get("skipped"):
        rows["mutation/full"] = {"category": "mutation",
                                 "variance": "UNMEASURED",
                                 "detail": "docker leg: " + dock["skipped"]}
    else:
        wm, dm = wsl["classifications"], dock["classifications"]
        if wm == dm and len(wm) == 100:
            rows["mutation/full"] = _row(
                "mutation/full", "mutation", True,
                f"100/100 mutant verdicts agree cross-env")
        else:
            diff = sorted(set(wm) | set(dm), key=str)
            bad = [k for k in diff if wm.get(k) != dm.get(k)]
            rows["mutation/full"] = _row(
                "mutation/full", "mutation", False,
                f"{100 - len(bad)}/100 agree; differ={bad[:10]}")
    print("mutation/full:", rows["mutation/full"]["variance"],
          rows["mutation/full"]["detail"][:100], flush=True)
    print("== EXT-B: no-cache image rebuild ==", flush=True)
    reb = image_rebuild()
    rows["image/rebuild"] = _row("image/rebuild", "reproducibility",
                                 reb["reproduced"], reb["detail"])
    print("image/rebuild:", rows["image/rebuild"]["variance"],
          reb["detail"][:100], flush=True)
    ok = all(r["variance"] == "none" for r in rows.values())
    doc = {"extension": "P1-04-EXT", "date": time.strftime("%Y-%m-%d"),
           "elapsed_s": round(time.perf_counter() - t0, 1),
           "rows": rows, "overall": "PASS" if ok else "FAIL",
           "scope_note": ("Same-machine legs (WSL vs Docker); cross-host "
                          "portability out of scope. Frozen E2 report "
                          "untouched.")}
    out = os.path.join(HERE, "P1_04_PORTABILITY_EXT.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    print(f"overall: {doc['overall']} -> {out}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
