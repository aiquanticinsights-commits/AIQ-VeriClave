"""Portability probe (frozen item 4, Gate E) — same checks, every environment.

Runs the deterministic, model-free subset everywhere and records versions +
outcomes for cross-env comparison:
  - python version, verilator/yosys/sby versions (or UNAVAILABLE)
  - unittest contract result
  - FRM fixed-vector traces (hashed — must match EXACTLY)
  - Verilator lint + Yosys synth of wb_dma (PASS/FAIL equivalence)
  - sby demo proof (or explicit UNAVAILABLE — itself a portability finding)

Comparison rule (frozen §4-5): metadata exact where deterministic;
functional/formal outcomes equivalent; otherwise a finding, never assumed.
Usage:  python portability.py --env NAME   -> PORTABILITY_NAME.json
        python portability.py --compare A B -> PORTABILITY.json
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def _mnt(path: str) -> str:
    if os.name == "nt":
        return "/mnt/" + path[0].lower() + path[2:].replace("\\", "/")
    return path


def _run(cmd: list[str], timeout_s: int = 300,
         nested: bool = False, cwd: str = "") -> tuple[int, str]:
    try:
        env = dict(os.environ)
        if nested:
            env["PORTABILITY_NESTED"] = "1"
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout_s, cwd=cwd or HERE, env=env)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, f"UNAVAILABLE: {exc}"


def _tool(name: str) -> list[str]:
    """Command prefix reaching `name`: via WSL on Windows, native elsewhere."""
    if os.name == "nt":
        return ["wsl", name]
    found = shutil.which(name)
    return [found] if found else [name]


def ver(cmd: list[str]) -> str:
    rc, log = _run(cmd, timeout_s=60)
    if rc == 127:
        return "UNAVAILABLE"
    for line in log.splitlines():
        if line.strip():
            return line.strip()[:80]
    return f"rc={rc}"


def collect(env: str) -> dict:
    """Run every portable check. Never raises — faults become findings."""
    import time as _time
    out: dict = {"env": env, "date": _time.strftime("%Y-%m-%d"),
                 "os": f"{platform.system()} {platform.release()}",
                 "python": platform.python_version(), "checks": {}}
    c = out["checks"]
    out["tools"] = {
        "verilator": ver(_tool("verilator") + ["--version"]),
        "yosys": ver(_tool("yosys") + ["-V"]),
        "sby": ver(_tool("sby") + ["--version"]),
    }
    rc, log = _run([sys.executable, "-m", "unittest", "discover", "-s", ".",
                    "-p", "test_*.py"], timeout_s=600, nested=True)
    c["unittest"] = {"pass": rc == 0,
                     "tests": re.findall(r"Ran (\d+) tests", log)}
    try:
        sys.path.insert(0, HERE)
        from sim_frm import WbDmaFrm
        vecs = [["rst", "w 0 00001000", "w 4 00002000", "w 8 00000002",
                 "w c 00000007", "w 14 00000001", "tick 10", "w c 00000006",
                 "tick 4", "r 10"],
                ["rst", "w 0 deadbeef", "r 0", "r 10"]]
        traces = [WbDmaFrm().run_stim(v) for v in vecs]
        blob = json.dumps(traces, sort_keys=True)
        c["frm_traces"] = {"pass": True,
                           "sha": hashlib.sha256(blob.encode()).hexdigest()[:16],
                           "events": sum(len(t) for t in traces)}
    except Exception as exc:  # noqa: BLE001 — finding, not crash
        c["frm_traces"] = {"pass": False, "error": str(exc)[:200]}
    rtl = os.path.join(os.path.dirname(HERE), "rideprotect-rv", "rtl",
                       "wb_dma.v")
    if os.name == "nt":
        toolchain_here = shutil.which("wsl") is not None
    else:
        toolchain_here = shutil.which("verilator") is not None
    if os.path.isfile(rtl) and toolchain_here:
        target, rtl_m, fixture = "wb_dma", _mnt(rtl), False
    elif toolchain_here:
        # Fixture mode: self-contained demo design already in the repo and
        # the image. Rows are labeled fixture:true — toolchain parity, not
        # DUT coverage.
        target = "cnt_formal"
        rtl_m = _mnt(os.path.join(HERE, "formal", "demo", "cnt_formal.sv"))
        fixture = True
    else:
        target, rtl_m, fixture = "", "", False
    if toolchain_here:
        rc, log = _run(_tool("verilator") + ["--lint-only", rtl_m])
        # Same rule as bakeoff.default_lint: the synthetic
        # "%Error: Exiting due to N warning(s)" exit line is noise;
        # genuine %Error-* diagnostics fail the check.
        sys.path.insert(0, HERE)
        from bakeoff import EXIT_NOISE
        c["verilator_lint"] = {"pass": "%Error" not in EXIT_NOISE.sub(
            "", log), "rc": rc, "fixture": fixture, "target": target}
        rc, log = _run(_tool("yosys") + ["-p", f"read_verilog -formal {rtl_m}; "
                         f"hierarchy -check -top {target}; "
                         f"synth -top {target}"])
        c["yosys_synth"] = {"pass": rc == 0 and "ERROR" not in log, "rc": rc,
                            "fixture": fixture, "target": target}
    else:
        c["verilator_lint"] = {"pass": None, "reason": "no toolchain here"}
        c["yosys_synth"] = {"pass": None, "reason": "no toolchain here"}
    demo = os.path.join(HERE, "formal", "demo", "cnt.sby")
    if os.name == "nt":
        sby_here = shutil.which("wsl") is not None
    else:
        sby_here = shutil.which("sby") is not None
    if sby_here and os.path.isfile(demo):
        # sby resolves [files] against CWD (version-dependent): run from the
        # demo dir so relative entries resolve portably. -d takes an abs path.
        work = tempfile.mkdtemp(prefix="port_sby_")
        demo_rel = os.path.relpath(demo, os.path.dirname(demo))
        cmd = _tool("sby") + ["-f", demo_rel, "-d",
                              _mnt(os.path.join(work, "out"))]
        rc, log = _run(cmd, timeout_s=600,
                       cwd=os.path.dirname(demo))
        done = re.search(r"DONE\s*\((PASS|FAIL|ERROR)[^)]*\)", log)
        c["sby_demo"] = {"pass": bool(done and done.group(1) == "PASS"),
                         "status": done.group(1) if done else "UNPROVEN"}
        shutil.rmtree(work, ignore_errors=True)
    else:
        c["sby_demo"] = {"pass": None, "reason": "UNAVAILABLE here"}
    return out


CATEGORIES = {
    "python": "metadata", "os": "metadata",
    "tools": "metadata",
    "unittest": "functional",
    "frm_traces": "functional",
    "verilator_lint": "functional",
    "yosys_synth": "functional",
    "sby_demo": "formal",
}


def compare(a: dict, b: dict) -> dict:
    """Two env records -> variance verdicts per frozen metric categories."""
    rows = {}
    ca, cb = a.get("checks", {}), b.get("checks", {})
    for key, cat in CATEGORIES.items():
        if key in ("python", "os", "tools"):
            va, vb = a.get(key), b.get(key)
            rows[key] = {"category": cat,
                         "variance": "none" if va == vb else "version-drift",
                         "detail": f"{a['env']}={va!r} {b['env']}={vb!r}"}
            continue
        va, vb = ca.get(key, {}), cb.get(key, {})
        pa, pb = va.get("pass"), vb.get("pass")
        if pa is None or pb is None:
            rows[key] = {"category": cat, "variance": "UNMEASURED",
                         "detail": f"{a['env']}={pa} {b['env']}={pb}"}
        elif key == "frm_traces":
            same = va.get("sha") == vb.get("sha")
            rows[key] = {"category": cat,
                         "variance": "none" if same else "DIVERGED",
                         "detail": f"sha {va.get('sha')} vs {vb.get('sha')}"}
        else:
            rows[key] = {"category": cat,
                         "variance": "none" if pa == pb else "DIVERGED",
                         "detail": f"{a['env']}={pa} {b['env']}={pb}"}
    return {"env_a": a["env"], "env_b": b["env"], "rows": rows,
            "signoff": "PENDING"}


def main() -> int:
    args = sys.argv[1:]
    if "--compare" in args:
        i = args.index("--compare")
        a = json.load(open(os.path.join(
            HERE, f"PORTABILITY_{args[i + 1]}.json"), encoding="utf-8"))
        b = json.load(open(os.path.join(
            HERE, f"PORTABILITY_{args[i + 2]}.json"), encoding="utf-8"))
        doc = compare(a, b)
        with open(os.path.join(HERE, "PORTABILITY.json"), "w",
                  encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
        for k, r in doc["rows"].items():
            print(f"  {k}: {r['variance']} ({r['detail'][:90]})", flush=True)
        return 0
    env = "dev"
    for i, x in enumerate(args):
        if x == "--env" and i + 1 < len(args):
            env = args[i + 1]
    doc = collect(env)
    with open(os.path.join(HERE, f"PORTABILITY_{env}.json"), "w",
              encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    print(json.dumps(doc, indent=1)[:1500], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
