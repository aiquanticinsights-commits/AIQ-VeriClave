"""E2 Docker leg (runs INSIDE the P0 image): portability collect + 5-mutant
spot campaign. RTL arrives via /work/rideprotect-rv mount (read-only);
results go to the out dir given on the command line."""
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


"""E2 Docker leg (runs INSIDE the P0 image): portability collect + 5-mutant
spot campaign. RTL arrives via /work/rideprotect-rv mount (read-only).
Results travel over stdout (--stdout): container writes into host Temp
mounts proved non-durable, while stdout capture is reliable."""

def main() -> int:
    outdir = sys.argv[1] if len(sys.argv) > 1 and not \
        sys.argv[1].startswith("--") else "/e2out"
    to_stdout = "--stdout" in sys.argv
    os.makedirs(outdir, exist_ok=True)
    from portability import collect
    doc = collect("e2docker")
    payload = json.dumps(doc)
    if to_stdout:
        print("@@PORTABILITY@@", flush=True)
        print(payload, flush=True)
    else:
        with open(os.path.join(outdir, "PORTABILITY_e2docker.json"), "w",
                  encoding="utf-8") as f:
            f.write(payload)
    print("portability done", flush=True)
    from run_portability_benchmark import mutant_spot
    spot = mutant_spot(outdir)
    payload = json.dumps(spot)
    if to_stdout:
        print("@@MUT@@", flush=True)
        print(payload, flush=True)
    else:
        with open(os.path.join(outdir, "MUT_E2DOCKER.json"), "w",
                  encoding="utf-8") as f:
            f.write(payload)
    print("mutant spot done:", spot["classifications"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
