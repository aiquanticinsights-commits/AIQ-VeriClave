#!/bin/sh
# Smoke entrypoint: prove, collect versions + artifacts, write SBY_SMOKE.json.
# Any failure exits nonzero (CI-hostile to silent passes).
set -u
cd /smoke
echo "--- tool versions ---"
yosys -V
sby --version
boolector --version
echo "--- proof ---"
rm -rf /smoke/out
sby -f counter.sby -d /smoke/out
RC=$?
echo "--- record ---"
python3 - <<'EOF'
import json, subprocess, re, os

def sh(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    return ((p.stdout or "") + (p.stderr or "")).strip().splitlines()

def first(pattern, lines):
    for ln in lines:
        m = re.search(pattern, ln)
        if m:
            return m.group(0).strip()[:100]
    return ""

yosys_v = first(r"Yosys.*", sh("yosys -V"))
sby_v = first(r"SBY.*", sh("sby --version"))
boo_v = first(r"[0-9]+\.[0-9]+\.[0-9]+", sh("boolector --version"))
log = open("/smoke/out/logfile.txt", errors="replace").read() \
    if os.path.isfile("/smoke/out/logfile.txt") else ""
done_m = re.search(r"DONE \((PASS|FAIL|ERROR)[^)]*\)", log)
status = done_m.group(1) if done_m else "UNPROVEN"
digest = subprocess.run(["sha256sum", "/smoke/counter.sv"],
                        capture_output=True, text=True).stdout.split()[0][:16]
doc = {
    "environment": "docker-sby-smoke",
    "status": "PASS" if status == "PASS" else "FAIL",
    "os": "ubuntu:24.04",
    "python": subprocess.run(["python3", "--version"],
                             capture_output=True, text=True).stdout.strip(),
    "yosys": yosys_v, "sby": sby_v, "solver": "boolector " + boo_v,
    "git_commit": os.environ.get("GIT_COMMIT", ""),
    "image_digest": os.environ.get("IMAGE_DIGEST", ""),
    "test": "counter_sby_smoke",
    "formal_result": status,
    "artifacts": ["counter.sv", "counter.sby", "out/logfile.txt"],
    "rtl_sha16": digest,
    "excluded_with_reasons": {
        "full-oss-cad-suite": "745MB; rejected (size + version-mismatch risk)",
        "bundled-python": "sby imports stdlib only; system python3 used",
        "z3/yices/cvc5": "boolector suffices for the smoke proof",
        "ghdl/nextpnr/gui-libs": "out of scope for a formal smoke proof",
    },
}
open("/smoke/SBY_SMOKE.json", "w").write(json.dumps(doc, indent=2))
if os.path.isdir("/out-host"):
    import shutil as _sh
    _sh.copy("/smoke/SBY_SMOKE.json", "/out-host/SBY_SMOKE.json")
print(json.dumps(doc, indent=1))
sys_exit = 0 if doc["status"] == "PASS" else 1
raise SystemExit(sys_exit)
EOF
