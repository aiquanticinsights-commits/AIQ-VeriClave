"""E2 Docker FULL leg (runs INSIDE the P0 image): full 100-mutant seed-7
campaign classifications over stdout. Same seed/catalog as the frozen V6
campaign, so per-mutant verdicts are directly comparable cross-env.
Kill verdicts are deterministic (lint+sim+fuzz ladder, no LLM)."""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)


def main() -> int:
    import mutate
    from run_mutants import campaign
    from sim_frm import DEFAULT_RTL
    if not os.path.isfile(DEFAULT_RTL):
        print("@@MUTFULL@@", flush=True)
        print(json.dumps({"skipped": "no RTL sibling here",
                          "classifications": {}}), flush=True)
        return 0
    pool = mutate.seed_catalog([DEFAULT_RTL], 100000, seed=7)
    catalog = mutate.stratify(pool, 100, seed=7)
    workdir = tempfile.mkdtemp(prefix="e2full_")
    results = campaign(catalog, workdir=workdir)
    print("@@MUTFULL@@", flush=True)
    print(json.dumps({"skipped": "",
                      "classifications": {mid: r["status"] for mid, r in
                                          results.items()}}), flush=True)
    print("mutant full done", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
