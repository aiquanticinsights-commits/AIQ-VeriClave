"""VCD-to-text event serializer + spec-drift pinpointer.

Gap closed: BluesFL/VCDiag reason over sliced waveforms, but nothing turned a
failing run into the sentence a developer needs: "signal X drifted from spec
at cycle N (expected A, got B)". This module does exactly that from plain VCD
(GTKWave-compatible output); FSDB users convert first (e.g. `fsdb2vcd`) since
FSDB is proprietary — parsing it here would need a vendor lib.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Transition:
    time: int
    signal: str
    old: str
    new: str


def parse_vcd(text: str) -> tuple[list[Transition], dict[str, str]]:
    """Minimal VCD subset: $var, $dumpvars, #t, 0/1/x/z + b-vectors.

    Returns (chronological transitions, final values keyed by signal name).
    """
    ids: dict[str, tuple[str, int]] = {}   # idcode -> (name, width)
    cur: dict[str, str] = {}               # idcode -> value
    events: list[Transition] = []
    t, in_dump = 0, False
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("$var "):
            parts = s.split()
            # $var <type> <width> <idcode> <reference> ...
            ids[parts[3]] = (parts[4], int(parts[2]))
        elif s.startswith("$dumpvars"):
            in_dump = True
        elif s.startswith("$end") and in_dump and t == 0:
            in_dump = False
        elif s.startswith("#") and s[1:].isdigit():
            t = int(s[1:])
            in_dump = False
        elif s and s[0] in "01xzXZ" and len(s) > 1 and not s.startswith("$"):
            idc, val = s[1:], s[0].lower()
            if idc in ids:
                name = ids[idc][0]
                if idc in cur and cur[idc] != val:
                    events.append(Transition(t, name, cur[idc], val))
                cur[idc] = val
        elif s.startswith("b") and " " in s:
            val, idc = s[1:].split(" ", 1)
            idc = idc.strip()
            if idc in ids:
                name = ids[idc][0]
                if idc in cur and cur[idc] != val:
                    events.append(Transition(t, name, cur[idc], val))
                cur[idc] = val
    final = {ids[i][0]: v for i, v in cur.items() if i in ids}
    return events, final


@dataclass
class Drift:
    signal: str
    time: int
    expected: str
    actual: str

    def sentence(self) -> str:
        return (f"signal {self.signal} drifted from spec at cycle {self.time} "
                f"(expected {self.expected}, got {self.actual})")


def drift_report(events: list[Transition],
                 expected: dict[str, list[tuple[int, str]]]) -> list[Drift]:
    """First-divergence cycle per signal vs a spec trace.

    expected: signal -> [(time, value), ...] sorted by time (the spec/FRM
    golden trace, e.g. exported from the Python FRM). Only the earliest
    mismatch per signal is reported — that is the pinpoint, not a dump.
    """
    actual: dict[str, list[tuple[int, str]]] = {}
    for e in events:
        actual.setdefault(e.signal, []).append((e.time, e.new))
    drifts = []
    for sig, exp in expected.items():
        for (te, ve) in exp:
            got = None
            for (ta, va) in actual.get(sig, []):
                if ta <= te:
                    got = va
                else:
                    break
            if got is not None and got != ve:
                drifts.append(Drift(sig, te, ve, got))
                break
    return sorted(drifts, key=lambda d: d.time)
