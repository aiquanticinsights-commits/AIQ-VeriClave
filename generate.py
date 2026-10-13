"""Typed generation interface (P4-06) — deterministic text from VALIDATED intent.

Refuses unvalidated intents outright (fail-closed: generation never guesses
widths, clocks, or reset polarity). Outputs are compilable skeletons carrying
the requirement ID and machine-checkable structure; semantic proof happens
downstream (SymbiYosys/JasperGold), never here.
"""
from __future__ import annotations

from intent import VerificationIntent

SUPPORTED = ("sva", "test", "coverage", "checker")


def _clocking(it: VerificationIntent) -> str:
    clk = it.clocks[0].name if it.clocks else "clk"
    if it.reset is not None:
        pol = "" if it.reset.polarity == "active-high" else "n"
        edge = "posedge" if it.reset.kind == "sync" else "posedge"
        rst = f" || ({edge} {pol}{it.reset.name})"
    else:
        clk0 = it.clocks[0].name if it.clocks else "clk"
        rst = ""
        clk = clk0
    base = it.clocks[0].name if it.clocks else "clk"
    return f"@(posedge {base}{rst})"


def generate_sva(it: VerificationIntent) -> str:
    """One width property per signal + one functional placeholder, all
    clocked/reset-bound from the intent. Requirement ID rides in comments."""
    _require_valid(it, "sva")
    clk_ev = _clocking(it)
    lines = [f"// generated from {it.requirement_id} :: {it.module} (P4-06, deterministic)"]
    for s in it.signals:
        lines.append(f"prop_{it.requirement_id}_{s.name}_width: assert property "
                     f"({clk_ev} $bits({s.name}) == {s.width});")
    lines.append(f"prop_{it.requirement_id}_func: assert property "
                 f"({clk_ev} 1'b1); // functional body: fill from intent.temporal {it.temporal}")
    return "\n".join(lines) + "\n"


def generate_covergroup(it: VerificationIntent) -> str:
    """Covergroup skeleton: one coverpoint per signal + requirement tag."""
    _require_valid(it, "coverage")
    clk_ev = _clocking(it)
    lines = [f"// generated from {it.requirement_id} :: {it.module} (P4-06, deterministic)",
             f"covergroup cg_{it.requirement_id} {clk_ev};"]
    for s in it.signals:
        lines.append(f"  cp_{s.name}: coverpoint {s.name} {{ bins lo[] = {{[0:{2 ** min(s.width, 4) - 1}]}}; }}")
    lines.append("endgroup")
    return "\n".join(lines) + "\n"


def generate_checker(it: VerificationIntent) -> str:
    """Python checker stub mirroring the intent (FRM-side oracle skeleton)."""
    _require_valid(it, "checker")
    return (f'"""Checker for {it.requirement_id} :: {it.module} (P4-06 skeleton)."""\n'
            f"SIGNALS = [{', '.join(repr(s.name) for s in it.signals)}]\n"
            f"WIDTHS = {{{', '.join(f'{s.name!r}: {s.width}' for s in it.signals)}}}\n"
            f"REQ = {it.requirement_id!r}\n\n"
            f"def check(state):\n"
            f"    \"\"\"Return list of violation strings (empty == pass). Fill per FRM.\"\"\"\n"
            f"    violations = []\n"
            f"    for name, width in WIDTHS.items():\n"
            f"        v = state.get(name, 0)\n"
            f"        if v.bit_length() > width:\n"
            f"            violations.append(f\"{{name}}={{v}} exceeds {{width}}b ({{REQ}})\")\n"
            f"    return violations\n")


def generate_test(it: VerificationIntent) -> str:
    """Directed-test outline: reset sequence + per-signal stimulus slots."""
    _require_valid(it, "test")
    rst = it.reset.name if it.reset is not None else "rst"
    lines = [f"// directed test for {it.requirement_id} :: {it.module} (P4-06 outline)",
             f"// 1. assert {rst}, hold 10 cycles, release",
             f"// 2. drive: {', '.join(s.name + f'[{s.width}b]' for s in it.signals)}"]
    if it.temporal:
        lines.append(f"// 3. temporal checks: {', '.join(it.temporal)}")
    lines.append("// 4. compare DUT vs FRM each cycle; log mismatches with cycle numbers")
    return "\n".join(lines) + "\n"


def _require_valid(it: VerificationIntent, artifact: str) -> None:
    errs = it.validate()
    if errs:
        raise ValueError(f"refusing {artifact} generation for invalid intent "
                         f"({it.requirement_id or '?'}): " + "; ".join(errs))


def generate(it: VerificationIntent) -> str:
    """Dispatch on intent.artifact; unknown kinds are refused, not guessed."""
    if it.artifact not in SUPPORTED:
        raise ValueError(f"unsupported artifact '{it.artifact}'; choose from {SUPPORTED}")
    return {"sva": generate_sva, "coverage": generate_covergroup,
            "checker": generate_checker, "test": generate_test}[it.artifact](it)
