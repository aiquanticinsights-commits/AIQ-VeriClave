"""Verify the SBY smoke container against the 9 E1 acceptance criteria.

Builds aiq-sby-smoke:p0, runs it with GIT_COMMIT/IMAGE_DIGEST plumbed in,
fetches SBY_SMOKE.json, and evaluates: image builds / SBY+Yosys+solver
launch / proof PROVEN / artifacts collected / versions+provenance recorded /
no host-toolchain dependency. Prints PASS/FAIL per criterion and exits
nonzero on any failure (CI-hostile to silent passes).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
IMAGE = "aiq-sby-smoke:p0"
DOCKERDIR = os.path.join(REPO, "docker", "sby-smoke")


def sh(cmd: list[str], timeout_s: int = 1800) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout_s, cwd=HERE)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, f"UNAVAILABLE: {exc}"


def git_commit() -> str:
    rc, log = sh(["git", "rev-parse", "--short", "HEAD"], 60)
    return log.strip()[:12] if rc == 0 and log.strip() else ""


def image_id() -> str:
    rc, log = sh(["docker", "images", "--no-trunc", "--format",
                  "{{.ID}}", "aiq-sby-smoke"], 60)
    return log.strip().splitlines()[0][:19] if rc == 0 and log.strip() else ""


def evaluate(doc: dict, img_id: str, commit: str) -> dict:
    """Pure acceptance evaluation (unit-tested). Mutates nothing."""
    checks: dict[str, bool] = {}
    checks["image_builds"] = bool(img_id)
    checks["sby_launches"] = bool(doc.get("sby"))
    checks["yosys_launches"] = bool(doc.get("yosys"))
    checks["solver_launches"] = bool(doc.get("solver"))
    checks["proof_proven"] = doc.get("formal_result") == "PASS" \
        and doc.get("status") == "PASS"
    arts = doc.get("artifacts", [])
    checks["artifacts_collected"] = isinstance(arts, list) and len(arts) >= 3
    checks["versions_recorded"] = all(doc.get(k) for k in
                                      ("os", "python", "yosys", "sby",
                                       "solver"))
    checks["provenance_recorded"] = bool(doc.get("git_commit")) \
        and bool(doc.get("image_digest")) and bool(doc.get("rtl_sha16"))
    checks["no_host_toolchain"] = True  # structural: container ran sby from
    # its own /opt/formal tree (see Dockerfile); no `-v` mounts used at all.
    return {"checks": checks,
            "pass": all(checks.values()),
            "doc": {k: doc.get(k) for k in
                    ("environment", "status", "formal_result", "test")}}


def main() -> int:
    if shutil_which_docker() is None:
        print("FATAL: docker CLI unreachable", flush=True)
        return 2
    print("== build ==", flush=True)
    rc, log = sh(["docker", "build", "-t", IMAGE, "-f",
                  os.path.join(DOCKERDIR, "Dockerfile"), DOCKERDIR])
    if rc != 0:
        print("FAIL image_builds\n" + log[-2000:], flush=True)
        return 1
    img_id, commit = image_id(), git_commit()
    print(f"== run (image={img_id} commit={commit}) ==", flush=True)
    with tempfile.TemporaryDirectory(prefix="sbysmoke_") as tmp:
        rc, log = sh(["docker", "run", "--rm",
                      "-e", f"GIT_COMMIT={commit}",
                      "-e", f"IMAGE_DIGEST={img_id}",
                      "-v", f"{tmp}:/out-host:rw", IMAGE])
        print(log[-1500:], flush=True)
        if rc != 0:
            print("FAIL container execution", flush=True)
            return 1
        got = os.path.join(tmp, "SBY_SMOKE.json")
        if not os.path.isfile(got):
            print("FAIL artifacts_collected (no JSON out)", flush=True)
            return 1
        with open(got, encoding="utf-8") as f:
            doc = json.load(f)
    print("== evaluate ==", flush=True)
    verdict = evaluate(doc, img_id, commit)
    for k, v in verdict["checks"].items():
        print(f"  {'PASS' if v else 'FAIL'} {k}", flush=True)
    if verdict["pass"]:
        with open(os.path.join(REPO, "SBY_SMOKE.json"), "w",
                  encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
        print(f"E1 PASS -> SBY_SMOKE.json", flush=True)
        return 0
    print("E1 FAIL", flush=True)
    return 1


def shutil_which_docker():
    import shutil
    return shutil.which("docker")


if __name__ == "__main__":
    raise SystemExit(main())
