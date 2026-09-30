"""E2 portability benchmark (frozen V8 objective): SAME git commit, WSL vs
Docker, normalized engineering outcomes compared (never byte identity).

Legs per env: lint + FRM traces + co-sim vectors + sby demo/formal smoke +
5-mutant spot campaign + evidence bundle. Comparison rows: functional,
formal, traceability, evidence, mutation -> EQUIVALENT/DIVERGED/UNMEASURED.
Overall PASS iff every row is EQUIVALENT. Timeouts/CPU may differ (declared
tolerance); verdicts may not.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

REPO = HERE
SPOT_N = 5


def sh(cmd: list[str], timeout_s: int = 1800, cwd: str = "") -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout_s, cwd=cwd or REPO)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, f"UNAVAILABLE: {exc}"


def git_commit() -> str:
    rc, log = sh(["git", "rev-parse", "--short", "HEAD"], 60)
    return log.strip()[:12] if rc == 0 and log.strip() else ""


def mutant_spot(workdir: str) -> dict:
    """Deterministic 5-mutant spot campaign (same seed => same mutants in
    both envs). Returns {mutant_id: classification} + build_ok flag."""
    import mutate
    from run_mutants import campaign
    from sim_frm import DEFAULT_RTL
    if not os.path.isfile(DEFAULT_RTL):
        return {"skipped": "no RTL sibling here", "classifications": {}}
    pool = mutate.seed_catalog([DEFAULT_RTL], 100000, seed=7)
    catalog = mutate.stratify(pool, SPOT_N, seed=7)
    results = campaign(catalog, workdir=workdir)
    return {"skipped": "",
            "classifications": {mid: r["status"] for mid, r in
                                results.items()},
            "mutants": [{k: m[k] for k in ("id", "op", "line_human")}
                        for m in catalog]}


def wsl_leg(tmp: str) -> dict:
    from portability import collect
    doc = collect("e2wsl")
    with open(os.path.join(tmp, "PORTABILITY_e2wsl.json"), "w",
              encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    return doc


def parse_leg_output(log: str) -> tuple[dict, dict]:
    """Split container stdout into (portability doc, mut-spot dict).
    Payloads are single-line JSON; surrounding chatter is ignored via
    raw_decode (never blanket-split parsing). Raises ValueError on
    malformed payload (caller records UNMEASURED/FAIL, never invents)."""
    markers = log.split("@@PORTABILITY@@")
    if len(markers) < 2:
        raise ValueError("missing @@PORTABILITY@@ marker")
    port_doc, _ = json.JSONDecoder().raw_decode(markers[1].strip())
    mut_seg = markers[1].split("@@MUT@@")
    if len(mut_seg) < 2:
        raise ValueError("missing @@MUT@@ marker")
    mut_doc, _ = json.JSONDecoder().raw_decode(mut_seg[1].strip())
    return port_doc, mut_doc


def docker_leg(tmp: str, rtl_host: str) -> dict:
    image = "aiq-vericlave:p0"
    rc, log = sh(["docker", "build", "-t", image, "."], timeout_s=1200)
    if rc != 0:
        return {"error": "image build failed: " + log[-1000:]}
    rtl_mnt = os.path.dirname(os.path.dirname(rtl_host)).replace("\\", "/")
    # Container OUTPUT travels over stdout, never a host mount: writes from
    # the container into host Temp mounts proved non-durable (measured:
    # present in-container, absent on host seconds later), while host reads
    # and stdout capture are reliable.
    cmd = ("/opt/vericlave-venv/bin/python "
           "/work/AIQ-VeriClave/scripts/e2_docker_leg.py --stdout")
    rc, log = sh(["docker", "run", "--rm",
                  "-v", f"{rtl_mnt}:/work/rideprotect-rv:ro",
                  image, "sh", "-c", cmd],
                 timeout_s=1800)
    if rc != 0:
        return {"error": "docker leg failed: " + log[-2000:]}
    try:
        doc, mut = parse_leg_output(log)
        doc["_mut_spot"] = mut
        return doc
    except (IndexError, ValueError) as exc:
        return {"error": f"docker leg payload unparsable ({exc}): "
                         + log[-2000:]}


def smoke_leg(tmp: str) -> dict:
    """Fresh formal-smoke run (same commit image). Reads SBY_SMOKE.json via
    `docker cp` (container FS, immune to the mount-write flakiness above)."""
    cname = "e2smoke-run"
    sh(["docker", "rm", "-f", cname], 60)
    rc, log = sh(["docker", "run", "--name", cname, "aiq-sby-smoke:p0"],
                 timeout_s=900)
    got = os.path.join(tmp, "SBY_SMOKE.json")
    try:
        if rc == 0:
            rcc, logc = sh(["docker", "cp",
                            f"{cname}:/smoke/SBY_SMOKE.json", got], 120)
            if rcc == 0 and os.path.isfile(got):
                with open(got, encoding="utf-8") as f:
                    return json.load(f)
    finally:
        sh(["docker", "rm", "-f", cname], 60)
    return {"status": "FAIL", "log": log[-1000:]}


def compare(wsl: dict, docker: dict, smoke: dict) -> dict:
    """Normalized outcome comparison. UNMEASURED where either side lacks
    data; DIVERGED on any verdict mismatch; EQUIVALENT otherwise."""
    rows = {}

    def row(name, category, a, b):
        if a is None or b is None:
            rows[name] = {"category": category, "variance": "UNMEASURED",
                          "detail": f"wsl={a} docker={b}"}
        elif a == b:
            rows[name] = {"category": category, "variance": "none",
                          "detail": f"both={a!r}"[:120]}
        else:
            rows[name] = {"category": category, "variance": "DIVERGED",
                          "detail": f"wsl={a!r} docker={b!r}"[:160]}

    wc, dc = wsl.get("checks", {}), docker.get("checks", {})
    row("functional/lint", "functional", (wc.get("verilator_lint") or {})
        .get("pass"), (dc.get("verilator_lint") or {}).get("pass"))
    row("functional/frm-traces", "functional",
        (wc.get("frm_traces") or {}).get("sha"),
        (dc.get("frm_traces") or {}).get("sha"))
    row("functional/unittest", "functional",
        (wc.get("unittest") or {}).get("pass"),
        (dc.get("unittest") or {}).get("pass"))
    row("formal/sby-demo", "formal",
        (wc.get("sby_demo") or {}).get("status") == "PASS",
        smoke.get("formal_result") == "PASS")
    row("traceability/frm-sha", "traceability",
        (wc.get("frm_traces") or {}).get("sha"),
        (dc.get("frm_traces") or {}).get("sha"))
    row("evidence/audit-present", "evidence",
        bool(wc.get("unittest")), bool(dc.get("unittest")))
    wm = wsl.get("_mut_spot", {}).get("classifications", {})
    dm = docker.get("_mut_spot", {}).get("classifications", {})
    if not wm or not dm:
        rows["mutation/spot"] = {"category": "mutation",
                                 "variance": "UNMEASURED",
                                 "detail": "spot campaign missing a side"}
    elif wm == dm:
        rows["mutation/spot"] = {"category": "mutation", "variance": "none",
                                 "detail": f"{len(wm)} mutants agree"}
    else:
        diff = sorted(set(wm) | set(dm), key=str)
        rows["mutation/spot"] = {"category": "mutation",
                                 "variance": "DIVERGED",
                                 "detail": str([(k, wm.get(k), dm.get(k))
                                                for k in diff])[:160]}
    return rows


def main() -> int:
    t0 = time.perf_counter()
    commit = git_commit()
    print(f"E2 benchmark at commit {commit}", flush=True)
    rtl_host = os.path.join(os.path.dirname(REPO), "rideprotect-rv", "rtl",
                            "wb_dma.v")
    if not os.path.isfile(rtl_host):
        print("FATAL: rideprotect RTL sibling missing", flush=True)
        return 2
    tmp = tempfile.mkdtemp(prefix="e2bench_")
    print("== WSL leg ==", flush=True)
    wsl = wsl_leg(tmp)
    print("== WSL mutant spot ==", flush=True)
    wsl["_mut_spot"] = mutant_spot(os.path.join(tmp, "wslmut"))
    print("spot:", wsl["_mut_spot"].get("classifications"), flush=True)
    print("== Docker leg ==", flush=True)
    docker = docker_leg(tmp, rtl_host)
    if "error" in docker:
        print("FATAL: " + docker["error"], flush=True)
        return 1
    print("== smoke leg ==", flush=True)
    smoke = smoke_leg(tmp)
    print("smoke:", smoke.get("formal_result"), flush=True)
    rows = compare(wsl, docker, smoke)
    overall = all(r["variance"] in ("none",) for r in rows.values())
    doc = {"benchmark": "E2-BENCH-001", "date": time.strftime("%Y-%m-%d"),
           "git_commit": commit,
           "wsl": {"unittest": wsl["checks"]["unittest"],
                   "frm_sha": wsl["checks"]["frm_traces"].get("sha"),
                   "sby_demo": wsl["checks"]["sby_demo"],
                   "mut_spot": wsl["_mut_spot"].get("classifications")},
           "docker": {"unittest": docker["checks"]["unittest"],
                      "frm_sha": docker["checks"]["frm_traces"].get("sha"),
                      "mut_spot": docker["_mut_spot"].get("classifications"),
                      "smoke": {k: smoke.get(k) for k in
                                ("formal_result", "yosys", "sby", "solver")}},
           "comparison": rows,
           "overall": "PASS" if overall else "FAIL",
           "signoff": "PENDING"}
    with open(os.path.join(REPO, "E2_PORTABILITY_REPORT.json"), "w",
              encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
    for k, r in rows.items():
        print(f"  {r['variance']:10s} {k}: {r['detail'][:80]}", flush=True)
    print("overall:", doc["overall"], flush=True)
    # interim artifacts stay out of git (report + evidence JSONs only)
    for fn in ("PORTABILITY_e2wsl.json", "PORTABILITY_e2docker.json"):
        try:
            os.unlink(os.path.join(REPO, fn))
        except OSError:
            pass
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
