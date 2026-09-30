"""BugGen-style mutation seeder (frozen V6 objective, Gate A/C1).

Line/text operators over synthesizable Verilog — no parser, every mutant
is an auditable (file, line, operator, original -> mutated) record:

  RELATIONAL  > <-> >= | < <-> <= | == <-> !=          (real fault class)
  ARITHMETIC  numeric literal N -> N+1 / N-1 (N < 65536, keeps addresses sane)
  BIT         bit-select index +-1 ([4:2] -> [4:3]/[4:1]); single ~ insert/remove
  CONTROL     condition invert (if/while (X) -> (X) with ! toggling);
              statement deletion (one nonblocking <= line dropped)
  SEQUENTIAL  reset value flip (<= 1'b0 <-> <= 1'b1 inside reset branches);
              enable mask (&& en -> && 1'b1)
  TEMPORAL    ##1 <-> ##2 inside assertion lines (lint-unchecked by Verilator,
              so these MUST be killed by formal or sim to count)
  CDC         sync[1] -> sync[0] use (single-flop collapse, gates_demo only)

Seeding is deterministic (seeded RNG over candidate sites). Invalid mutants
(empty result, parse-destroyed files) are the RUNNER's classification, not
the seeder's — the catalog records intent; classify.py disposes.
"""
from __future__ import annotations

import json
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))

OPERATORS = ("REL_GT_GE", "REL_LT_LE", "REL_EQ_NE",
             "ARITH_PLUS1", "ARITH_MINUS1",
             "BIT_IDX_P1", "BIT_IDX_M1", "BIT_NEG_TOGGLE",
             "CTRL_COND_INVERT", "CTRL_STMT_DELETE",
             "SEQ_RESET_FLIP", "SEQ_ENABLE_REMOVE",
             "TEMPORAL_DELAY_P1", "TEMPORAL_DELAY_M1",
             "CDC_STAGE_REMOVE")


def _literal_spans(line: str):
    """Yield (digits, index) for each mutable number: the digit run of a
    sized literal (`4'd10` -> `10`) or a standalone integer. Index k selects
    the k-th numeric match, so seeding and application agree exactly."""
    for k, m in enumerate(re.finditer(r"\d+", line)):
        yield m.group(0), k

def _nth_number(line: str, digits: str, index: int, new: str) -> str | None:
    """Replace the index-th `\d+` match with `new` iff that match's digits
    equal `digits`. Returns None on any mismatch (fail-closed seeding)."""
    seen = -1

    def repl(m):
        nonlocal seen
        seen += 1
        return new if (seen == index and m.group(0) == digits) else m.group(0)

    out = re.sub(r"\d+", repl, line)
    return out if seen >= index and out != line else None


def candidates(path: str) -> list[dict]:
    """All seedable sites in a file: [{line, op, detail}]."""
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    out = []
    for i, raw in enumerate(lines):
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            continue
        if re.search(r"(?<![<>=!])>(?![>=])", line):
            out.append({"line": i, "op": "REL_GT_GE"})
        if re.search(r"(?<![<>=!])<(?![<=])", line):
            out.append({"line": i, "op": "REL_LT_LE"})
        if "==" in line:
            out.append({"line": i, "op": "REL_EQ_NE"})
        for digits, k in _literal_spans(line):
            if int(digits) >= 65536:
                continue
            out.append({"line": i, "op": "ARITH_PLUS1",
                        "detail": "%s@%d" % (digits, k)})
            if int(digits) > 0:
                out.append({"line": i, "op": "ARITH_MINUS1",
                            "detail": "%s@%d" % (digits, k)})
        m = re.search(r"\[(\d+):(\d+)\]", line)
        if m:
            out.append({"line": i, "op": "BIT_IDX_P1"})
            out.append({"line": i, "op": "BIT_IDX_M1"})
        if re.search(r"(?<![\w$])~(?![\w$])|~\s*\(", line) or \
                re.search(r"\bassign\b.*=", line):
            out.append({"line": i, "op": "BIT_NEG_TOGGLE"})
        if re.match(r"\s*if\s*\(", line):
            out.append({"line": i, "op": "CTRL_COND_INVERT"})
        if "<=" in line and not line.strip().startswith(("if", "else",
                                                          "case", "for",
                                                          "while", "module",
                                                          "assign")):
            out.append({"line": i, "op": "CTRL_STMT_DELETE"})
        if re.search(r"<=\s*1'b[01]", line):
            out.append({"line": i, "op": "SEQ_RESET_FLIP"})
        if re.search(r"&&\s*[a-z_][\w$]*", line):
            out.append({"line": i, "op": "SEQ_ENABLE_REMOVE"})
        m = re.search(r"##(\d+)", line)
        if m:
            out.append({"line": i, "op": "TEMPORAL_DELAY_P1"})
            if int(m.group(1)) > 1:
                out.append({"line": i, "op": "TEMPORAL_DELAY_M1"})
        if "sync[1]" in line:
            out.append({"line": i, "op": "CDC_STAGE_REMOVE"})
    return out


def apply_mutation(lines: list[str], site: dict) -> list[str] | None:
    """Apply one site. Returns new lines, or None if inapplicable."""
    out = list(lines)
    i, op = site["line"], site["op"]
    if not (0 <= i < len(out)):
        return None
    line = out[i]

    def sub_once(pattern, repl, count=1):
        new, n = re.subn(pattern, repl, line, count=count)
        return (new, True) if n else (line, False)

    if op == "REL_GT_GE":
        line, ok = sub_once(r"(?<![<>=!])>(?![>=])", ">=")
    elif op == "REL_LT_LE":
        line, ok = sub_once(r"(?<![<>=!])<(?![<=])", "<=")
    elif op == "REL_EQ_NE":
        line, ok = sub_once(r"==", "!=")
    elif op in ("ARITH_PLUS1", "ARITH_MINUS1"):
        try:
            digits, index = site.get("detail", "").split("@")
            index = int(index)
        except (ValueError, AttributeError):
            return None
        delta = 1 if op == "ARITH_PLUS1" else -1
        new = str(int(digits) + delta)
        line = _nth_number(line, digits, index, new)
        if line is None:
            return None
        ok = True
    elif op in ("BIT_IDX_P1", "BIT_IDX_M1"):
        m = re.search(r"\[(\d+):(\d+)\]", line)
        if not m:
            return None
        hi, lo = int(m.group(1)), int(m.group(2))
        if op == "BIT_IDX_P1":
            hi += 1
        else:
            lo -= 1
            if lo < 0:
                return None
        line, ok = sub_once(r"\[\d+:\d+\]", "[%d:%d]" % (hi, lo))
    elif op == "BIT_NEG_TOGGLE":
        if "~" in line.split("//")[0]:
            line = line.replace("~", "", 1)
            ok = True
        else:
            m = re.search(r"=\s*([a-z_][\w$]*)", line)
            if not m:
                return None
            line, ok = sub_once(r"=\s*([a-z_][\w$]*)", "= ~\\1")
    elif op == "CTRL_COND_INVERT":
        m = re.search(r"if\s*\((.*)\)(.*)$", line.rstrip("\n"))
        if not m:
            return None
        line = line[:m.start(1)] + "!(%s)" % m.group(1) + m.group(2) + "\n"
        ok = True
    elif op == "CTRL_STMT_DELETE":
        out = out[:i] + out[i + 1:]
        return out
    elif op == "SEQ_RESET_FLIP":
        if "<= 1'b0" in line:
            line, ok = sub_once(r"<=\s*1'b0", "<= 1'b1")
        elif "<= 1'b1" in line:
            line, ok = sub_once(r"<=\s*1'b1", "<= 1'b0")
        else:
            return None
    elif op == "SEQ_ENABLE_REMOVE":
        line, ok = sub_once(r"&&\s*[a-z_][\w$]*", "&& 1'b1")
    elif op in ("TEMPORAL_DELAY_P1", "TEMPORAL_DELAY_M1"):
        m = re.search(r"##(\d+)", line)
        if not m:
            return None
        d = int(m.group(1)) + (1 if op == "TEMPORAL_DELAY_P1" else -1)
        if d < 0:
            return None
        line, ok = sub_once(r"##\d+", "##%d" % d)
    elif op == "CDC_STAGE_REMOVE":
        line, ok = sub_once(r"sync\[1\]", "sync[0]")
    else:
        return None
    if not ok:
        return None
    out[i] = line
    if "".join(out).strip() == "".join(lines).strip():
        return None
    return out


def seed_catalog(files: list[str], n: int, seed: int = 7) -> list[dict]:
    """Deterministic catalog of n mutants across files (round-robin by op
    frequency would bias to common lines; uniform over sites instead)."""
    rng = random.Random(seed)
    pool = []
    for path in files:
        for site in candidates(path):
            pool.append((path, site))
    if not pool:
        return []
    catalog = []
    order = list(range(len(pool)))
    rng.shuffle(order)
    for idx in order:
        if len(catalog) >= n:
            break
        path, site = pool[idx]
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        if apply_mutation(lines, dict(site)) is None:
            continue
        mid = "M%03d" % (len(catalog) + 1)
        catalog.append({"id": mid, "file": os.path.basename(path),
                        "path": path, "line": site["line"],
                        "line_human": site["line"] + 1,
                        "op": site["op"],
                        "detail": site.get("detail", "")})
    return catalog


def write_catalog(catalog: list[dict], path: str) -> str:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)
    return path


def stratify(catalog: list[dict], n: int, seed: int = 7) -> list[dict]:
    """Balanced subsample: rare operators kept whole, abundant ones capped
    so no single family dominates the campaign (uniform sampling would be
    ~70% ARITH on wb_dma). Deterministic; re-ids M001.. sequentially."""
    import random as _random
    rng = _random.Random(seed)
    by_op: dict[str, list[dict]] = {}
    for m in catalog:
        by_op.setdefault(m["op"], []).append(m)
    for v in by_op.values():
        rng.shuffle(v)
    out = []
    families = sorted(by_op)
    while len(out) < n and any(by_op.values()):
        for op in families:
            if by_op[op] and len(out) < n:
                out.append(by_op[op].pop(0))
    for i, m in enumerate(out):
        m = dict(m)
        m["id"] = "M%03d" % (i + 1)
        out[i] = m
    return out
