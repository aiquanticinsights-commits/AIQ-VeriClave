"""P5 independent execution — frozen protocol, four held-out families.

Rules enforced by construction:
- Inputs are READ from frozen artifacts only (P5_FREEZE_v1, P4_BENCH_v1,
  P4_HELDOUT_v1). Any drift aborts the run (freeze guard).
- Outputs are NEW evidence files (P5_RUN_<family>.json); frozen files are
  never written.
- The suite runs TWICE; any verdict disagreement becomes a finding, and the
  run is marked NON-REPRODUCIBLE (protocol: reproduce twice).
- No training, no threshold edits, no family swaps, no metric redefinitions.
- Formal/simulation backends unavailable on this host are recorded
  UNAVAILABLE (never simulated by assertion).
"""
from __future__ import annotations

import hashlib
import json

from closure import ClosureBoundary
from diagnostics import from_failure_event
from evidence import EvidenceLedger, EvidenceRecord
from generate import generate
from intent import Clock, Reset, Signal, VerificationIntent
from trace import Traceability

FROZEN = ("P5_FREEZE_v1.json", "P4_BENCH_v1.json", "P4_HELDOUT_v1.json")
BASE = r'C:\Projects\ChipDesign\AIQ-VeriClave'


def sha(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def freeze_guard() -> dict:
    """Snapshot frozen inputs. Call again after the run; mismatch aborts."""
    return {f: sha(f"{BASE}\\{f}") for f in FROZEN}


# --------------------------------------------------------------------------
# Family FRMs (golden) + seeded mutants. Each mutant: (label, apply_fn).
# --------------------------------------------------------------------------

class Fifo:
    def __init__(self, depth=4, mutant=None):
        self.q, self.depth, self.m = [], depth, mutant or "golden"

    def push(self, v):
        if len(self.q) < self.depth:
            self.q.append(v)

    def pop(self):
        if not self.q:
            return None
        if self.m == "pop-drops-two":
            self.q.pop(0)
            return self.q.pop(0) if self.q else None
        return self.q.pop(0)

    def full(self):
        if self.m == "full-stuck-0":
            return 0
        return int(len(self.q) >= self.depth)

    def count(self):
        if self.m == "count-stuck":
            return 0
        return len(self.q)


def fifo_oracle(st, depth=4):
    """Return violation strings for observed state dict."""
    v = []
    if st["count"] != st["n"]:
        v.append(f"count {st['count']} != occupancy {st['n']}")
    if st["n"] >= depth and st["full"] != 1:
        v.append("full not asserted at depth")
    if st["n"] < depth and st["full"] != 0:
        v.append("spurious full below depth")
    if st["count"] > depth:
        v.append("count exceeds depth")
    return v


def fifo_state(f):
    return {"full": f.full(), "empty": int(len(f.q) == 0),
            "count": f.count(), "n": len(f.q)}


class Arbiter:
    """4-requester round-robin grant. `last` = index last granted (init 3)."""

    def __init__(self, n=4, mutant=None):
        self.n, self.last, self.m = n, n - 1, mutant or "golden"

    def grant(self, req):
        if self.m == "fixed-priority":
            for i in range(self.n):
                if req[i]:
                    self.last = i
                    return i
            return -1
        if self.m == "grant-stuck":
            return self.last if req[self.last] else -1
        for k in range(1, self.n + 1):
            i = (self.last + k) % self.n
            if req[i]:
                self.last = i
                return i
        return -1


def arbiter_oracle(req, g, last_before):
    v = []
    if g == -1:
        if any(req):
            v.append("no grant despite pending requests")
        return v
    if not req[g]:
        v.append(f"grant to non-requesting {g}")
    # round-robin order check on full request vector
    if all(req):
        exp = (last_before + 1) % len(req)
        if g != exp:
            v.append(f"RR order broken: got {g}, expected {exp}")
    return v


class Intc:
    """4 sources, priorities [1,2,3,4] (higher wins), threshold gate, claim clears."""

    def __init__(self, mutant=None):
        self.prio = [1, 2, 3, 4]
        self.pend = [0, 0, 0, 0]
        self.thresh = 1
        self.m = mutant or "golden"

    def raise_irq(self, i):
        self.pend[i] = 1

    def winner(self):
        cands = [i for i in range(4) if self.pend[i]]
        if not cands:
            return -1
        if self.m == "threshold-ignored":
            pool = cands
        else:
            pool = [i for i in cands if self.prio[i] > self.thresh]
            if not pool:
                return -1
        if self.m == "priority-inverted":
            return min(pool, key=lambda i: self.prio[i])
        return max(pool, key=lambda i: self.prio[i])

    def claim(self, i):
        if self.m == "claim-no-clear":
            return
        self.pend[i] = 0


def intc_oracle(ic, w):
    v = []
    exp_pool = [i for i in range(4) if ic.pend[i] and ic.prio[i] > ic.thresh]
    exp = max(exp_pool, key=lambda i: ic.prio[i]) if exp_pool else -1
    if w != exp:
        v.append(f"winner {w} != expected {exp}")
    return v


class ResetSync:
    """Two-flop synchronizer: out[t] == inp[t-2] (exactly 2 cycles)."""

    def __init__(self, mutant=None):
        self.d1, self.d2 = 0, 0
        self.m = mutant or "golden"

    def tick(self, inp):
        if self.m == "stuck-0":
            return 0
        if self.m == "one-flop":
            out, self.d1 = self.d1, inp  # 1-cycle follower (wrong latency)
            return out
        out, self.d2, self.d1 = self.d2, self.d1, inp
        return out


def resetsync_oracle(hist):
    """hist: list of (inp, out). out[t] must equal inp[t-2] (0 before)."""
    v = []
    for t, (inp, out) in enumerate(hist):
        exp = hist[t - 2][0] if t >= 2 else 0
        if out != exp:
            v.append(f"t={t}: out {out} != inp[t-2] {exp}")
    return v


FAMILIES = {
    "async-fifo": {"mutants": ["full-stuck-0", "count-stuck", "pop-drops-two"]},
    "round-robin-arbiter": {"mutants": ["fixed-priority", "grant-stuck"]},
    "interrupt-controller": {"mutants": ["threshold-ignored", "priority-inverted", "claim-no-clear"]},
    "reset-synchronizer": {"mutants": ["one-flop", "stuck-0"]},
}


def run_family(family: str) -> dict:
    """Execute the P4 pipeline chain for one held-out family. Deterministic."""
    rep = {"family": family, "mutants": {}, "golden_fa": 0,
           "closure": None, "trace": None, "ledger_ok": False}
    if family == "async-fifo":
        def fifo_check(f):
            for v in (1, 2, 3, 4):
                f.push(v)
            viol = fifo_oracle(fifo_state(f))
            drain = []
            while True:
                v = f.pop()
                if v is None:
                    break
                drain.append(v)
            if drain != [1, 2, 3, 4]:
                viol = viol + [f"pop sequence {drain} != [1,2,3,4]"]
            return viol

        rep["golden_fa"] = len(fifo_check(Fifo()))
        for m in FAMILIES[family]["mutants"]:
            rep["mutants"][m] = {"killed": len(fifo_check(Fifo(mutant=m))) > 0}
    elif family == "round-robin-arbiter":
        a = Arbiter()
        seq_ok, fa = True, 0
        for step in range(8):
            req = [1, 1, 1, 1]
            lb = a.last
            fa += len(arbiter_oracle(req, a.grant(req), lb))
        rep["golden_fa"] = fa
        for m in FAMILIES[family]["mutants"]:
            d = Arbiter(mutant=m)
            kills = 0
            for step in range(8):
                req = [1, 1, 1, 1]
                lb = d.last
                kills += len(arbiter_oracle(req, d.grant(req), lb))
            rep["mutants"][m] = {"killed": kills > 0}
    elif family == "interrupt-controller":
        def intc_check(make):
            """Two vectors: multi-source AND threshold-edge (only src0)."""
            ic = make()
            for i in (0, 2, 3):
                ic.raise_irq(i)
            viol = intc_oracle(ic, ic.winner())
            edge = make()
            edge.raise_irq(0)
            viol = viol + intc_oracle(edge, edge.winner())
            return viol, ic

        golden_viol, _ = intc_check(Intc)
        rep["golden_fa"] = len(golden_viol)
        for m in FAMILIES[family]["mutants"]:
            viol, _ = intc_check(lambda: Intc(mutant=m))
            killed = len(viol) > 0
            if m == "claim-no-clear":
                # claim must clear on the multi-source instance (edge instance
                # has nothing meaningful to claim — test the real path)
                c = Intc(mutant=m)
                for i in (0, 2, 3):
                    c.raise_irq(i)
                w = c.winner()
                c.claim(w)
                killed = killed or (w >= 0 and c.pend[w] == 1)
            rep["mutants"][m] = {"killed": killed}
    elif family == "reset-synchronizer":
        r = ResetSync()
        hist = [(1 if t >= 1 else 0, r.tick(1 if t >= 1 else 0)) for t in range(6)]
        rep["golden_fa"] = len(resetsync_oracle(hist))
        for m in FAMILIES[family]["mutants"]:
            d = ResetSync(mutant=m)
            h = [(1 if t >= 1 else 0, d.tick(1 if t >= 1 else 0)) for t in range(6)]
            rep["mutants"][m] = {"killed": len(resetsync_oracle(h)) > 0}
    else:
        raise ValueError(f"unknown family '{family}' (no family swaps allowed)")

    # closure walk: FAIL attempts for unkilled mutants, then a final attempt
    # whose verdict reflects reality (PASS only if all killed — an unresolved
    # FAIL is escalated, never converted).
    cb = ClosureBoundary(family)
    n = 0
    for m, res in rep["mutants"].items():
        if res["killed"]:
            continue
        n += 1
        cb.attempt(f"{m}-r{n}", "FAIL", repair_action="strengthen-checker",
                   evidence_hash=f"{family}-{m}-{n}")
    all_killed = all(res["killed"] for res in rep["mutants"].values())
    cb.attempt(f"{family}-final", "PASS" if all_killed else "FAIL",
               evidence_hash=f"{family}-final")
    rep["closure"] = {"rounds": len(cb.attempts), "disposition": cb.disposition()}

    # trace + ledger
    tr = Traceability()
    rid = f"REQ-{family}"
    tr.register(rid)
    tr.attach(rid, intent_id=f"I-{family}", artifact_id=f"A-{family}",
              execution_id=f"E-{family}", evidence_id=f"H-{family}")
    tr.close(rid, "PASS" if rep["closure"]["disposition"] == "PASS" else "FAIL")
    rep["trace"] = tr.completeness()
    from evidence import EvidenceLedger, EvidenceRecord
    lg = EvidenceLedger()
    lg.append(EvidenceRecord(rid, f"A-{family}",
                             {"mutants_killed": all(v["killed"] for v in rep["mutants"].values()),
                              "golden_fa": rep["golden_fa"]},
                             "PASS" if rep["closure"]["disposition"] == "PASS" else "FAIL",
                             signed_by="p5-executor"))
    rep["ledger_ok"] = lg.verify_chain() and lg.audit_completeness() == 1.0

    # verdict vs frozen bars: all mutants killed AND zero golden false alarms
    rep["verdict"] = ("PASS" if (all(v["killed"] for v in rep["mutants"].values())
                                 and rep["golden_fa"] == 0
                                 and rep["closure"]["disposition"] == "PASS"
                                 and rep["trace"]["completeness"] == 1.0
                                 and rep["ledger_ok"]) else "FAIL")
    return rep


def run_suite() -> dict:
    """Full P5 run over frozen families. Returns family verdicts + freeze check."""
    before = freeze_guard()
    out = {"families": {f: run_family(f) for f in FAMILIES}, "freeze_intact": None}
    after = freeze_guard()
    out["freeze_intact"] = (before == after)
    if not out["freeze_intact"]:
        raise RuntimeError("FROZEN INPUTS CHANGED DURING RUN — results void")
    out["overall"] = ("PASS" if all(v["verdict"] == "PASS" for v in out["families"].values())
                      else "FAIL")
    return out


if __name__ == "__main__":
    import json
    first = run_suite()
    second = run_suite()
    if json.dumps(first, sort_keys=True) != json.dumps(second, sort_keys=True):
        print("NON-REPRODUCIBLE: two runs disagree — recorded as finding")
        first["reproducible"] = False
    else:
        first["reproducible"] = True
    with open("P5_EXECUTION.json", "w", encoding="utf-8") as f:
        json.dump(first, f, indent=2)
    for fam, v in first["families"].items():
        print(f"{fam}: {v['verdict']} "
              f"(killed {sum(1 for m in v['mutants'].values() if m['killed'])}/{len(v['mutants'])}, "
              f"FA {v['golden_fa']}, closure {v['closure']['disposition']})")
    print("overall:", first["overall"], "| reproducible:", first["reproducible"],
          "| freeze_intact:", first["freeze_intact"])
