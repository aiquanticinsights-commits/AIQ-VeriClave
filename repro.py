"""Reproducibility envelope (P4-13) — pinned environment record per run.

Complements portability.py (cross-env agreement) with a per-run envelope:
who ran what, where, with which tool versions and file hashes. Metric-category
tolerance policy from the architecture doc applies at comparison time; this
module only records honestly (missing tools recorded as UNAVAILABLE, never
assumed).
"""
from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import sys


def tool_version(cmd: list[str]) -> str:
    """Best-effort version string; UNAVAILABLE when the tool is absent."""
    if not shutil.which(cmd[0]):
        return "UNAVAILABLE"
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        text = (out.stdout + "\n" + out.stderr).strip().splitlines()
        return text[0][:120] if text else "present-unversioned"
    except Exception:
        return "UNAVAILABLE"


def git_sha(workdir: str = ".") -> str:
    try:
        out = subprocess.run(["git", "-C", workdir, "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=15)
        sha = out.stdout.strip()
        return sha if len(sha) == 40 else "not-a-git-tree"
    except Exception:
        return "git-unavailable"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def envelope(extra_files: tuple[str, ...] = ()) -> dict:
    """Emit the reproducibility envelope for the current environment."""
    return {
        "python": sys.version.split()[0],
        "platform": f"{platform.system()}-{platform.machine()}",
        "tools": {
            "verilator": tool_version(["verilator", "--version"]),
            "yosys": tool_version(["yosys", "-V"]),
            "sby": tool_version(["sby", "--version"]),
        },
        "git_sha": git_sha("."),
        "files": {p: sha256_file(p) for p in extra_files},
    }


def write_envelope(path: str, extra_files: tuple[str, ...] = ()) -> dict:
    env = envelope(extra_files)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(env, f, indent=2)
    return env
