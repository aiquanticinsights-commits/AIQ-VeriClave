"""Constrained generation — skeletons with LLM-filled slots (prescription 3).

Frozen-gate diagnosis: free-form codegen at 8B never produced lint-clean SVA
or width fixes (0/5 across P0-D v1+v2), while the verifiers caught everything.
Instead of a bigger model, shrink the generation surface: the harness owns a
verified skeleton, the model fills labeled slots, a deterministic assembler
builds the artifact, and the same lint judges it. Slot values are charset-
and keyword-gated BEFORE assembly — unparseable or hostile fills fail
deterministically, never reach the toolchain raw.

Slot protocol (v1): model replies with labeled lines, e.g.
  ANTECEDENT: s_wb_stb
  LOW: 1
  HIGH: 2
  CONSEQUENT: s_wb_ack
"""
from __future__ import annotations

import re

# Characters allowed inside expression slots. Semicolons, backticks, and
# compiler directives can never survive the gate below. `$` is allowed:
# sampled-value system functions ($rose/$fell/$stable/$past) are legitimate
# SVA — rejecting them rejects correct answers (measured P0-D skeleton v1).
SLOT_CHARSET = re.compile(r"^[A-Za-z0-9_ $&|!()=~'\s.\[\]:]+$")
# `$` itself is allowed (sampled-value functions); only I/O- and
# control-type system tasks are banned (no file access, no sim control).
BANNED = (";", "`", "assert", "property", "module", "endmodule", "initial",
          "always", "generate", "import",
          "$display", "$write", "$fopen", "$fwrite", "$fclose", "$readmem",
          "$readmemb", "$dumpvars", "$dumpfile", "$finish", "$stop",
          "$fatal", "$error", "$warning", "$info", "$system", "$psprintf")


def clean_slot(value: str) -> str | None:
    """A slot value is accepted only if it is short, charset-clean, and
    contains no statement/keyword smuggling. Returns stripped value or None."""
    v = value.strip()
    if not v or len(v) > 64:
        return None
    if not SLOT_CHARSET.match(v):
        return None
    low = v.lower()
    if any(b in low for b in BANNED):
        return None
    return v


def parse_slots(text: str, labels: tuple[str, ...]) -> dict | None:
    """Extract `LABEL: value` lines for every label. All-or-nothing."""
    found = {}
    for line in text.splitlines():
        m = re.match(r"^\s*([A-Za-z_]+)\s*:\s*(.+?)\s*$", line)
        if m and m.group(1).upper() in labels:
            found[m.group(1).upper()] = m.group(2)
    if any(label not in found for label in labels):
        return None
    cleaned = {}
    for label in labels:
        v = clean_slot(found[label])
        if v is None:
            return None
        cleaned[label] = v
    return cleaned


def parse_int_slot(value: str) -> str | None:
    v = value.strip()
    return v if re.fullmatch(r"\d{1,3}", v) else None


SVA_RANGE_SKELETON = """property {name};
  @(posedge clk) {ante} |-> ##[{lo}:{hi}] {cons};
endproperty
assert property ({name});
"""
# NOTE: Verilator --lint-only parses NO ## delays in any mode and this
# Yosys parses no concurrent |-> at all (both measured) — range-form SVA is
# therefore uncheckable outside a full formal run. Delay requirements use
# the past-form below, which sby proves directly (see formal_adapter).

SVA_SIMPLE_SKELETON = """property {name};
  @(posedge clk) {ante} |-> {cons};
endproperty
assert property ({name});
"""

# Past-form: exact-cycle reading of a delay requirement, provable by sby.
# Template placeholders: {past} = last-cycle condition, {now} = this-cycle.
SVA_PAST_SKELETON = """A_GEN: assert({now} == $past({past}));"""

# task id -> skeleton spec. Ports mirror the free-form wrappers in p0d.py so
# the same Verilator lint judges both strategies identically.
SKELETONS = {
    "T1-sva-ack": {
        "kind": "sva-past",
        # Exact-cycle reading of "ack within 2 of stb": the RTL registers
        # ack in exactly one cycle, so ack == past(cyc&&stb) is faithful
        # (and stronger). Uncheckable by lint — proved by sby (formal_fn).
        "labels": ("PAST_EXPR", "NOW_EXPR"),
        "mention": {"PAST_EXPR": ("stb",), "NOW_EXPR": ("ack",)},
        "ports": "input wire clk, input wire s_wb_stb, input wire s_wb_ack",
        "name": "p_sva_ack",
        "prompt": (
            "A Wishbone slave registers its ack: s_wb_ack is 1 exactly when "
            "s_wb_cyc && s_wb_stb held on the previous cycle (signals: clk, "
            "s_wb_stb, s_wb_ack). Reply with EXACTLY these two lines and "
            "nothing else:\n"
            "PAST_EXPR: <previous-cycle boolean condition over s_wb_stb>\n"
            "NOW_EXPR: <this-cycle boolean expression over s_wb_ack>\n"
            "They will be checked as NOW_EXPR == $past(PAST_EXPR) by formal "
            "proof. Write PLAIN conditions: do NOT wrap anything in $past "
            "yourself and do NOT invent functions like sampled/past — the "
            "harness adds the single $past. No extra text."),
    },
    "T2-sva-irq": {
        "kind": "sva-simple",
        "labels": ("ANTECEDENT", "CONSEQUENT"),
        "ports": "input wire clk, input wire irq, input wire irq_en",
        "name": "p_sva_irq",
        "prompt": (
            "Fill the blanks of this SystemVerilog assertion skeleton for a "
            "DMA engine where `assign irq = irq_flag & irq_en;` (signals: "
            "clk, irq, irq_en). Reply with EXACTLY these two lines and "
            "nothing else:\n"
            "ANTECEDENT: <boolean expression over irq>\n"
            "CONSEQUENT: <boolean expression over irq_en>\n"
            "Meaning: whenever ANTECEDENT holds, CONSEQUENT must hold. "
            "Plain expressions only, no extra text."),
    },
    "T7-sva-cyc": {
        "kind": "sva-simple",
        "labels": ("ANTECEDENT", "CONSEQUENT"),
        "ports": "input wire clk, input wire m_wb_stb, input wire m_wb_cyc",
        "name": "p_sva_cyc",
        "prompt": (
            "Fill the blanks of this SystemVerilog assertion skeleton for a "
            "Wishbone DMA master (signals: clk, m_wb_stb, m_wb_cyc). Reply "
            "with EXACTLY these two lines and nothing else:\n"
            "ANTECEDENT: <boolean expression over m_wb_stb>\n"
            "CONSEQUENT: <boolean expression over m_wb_cyc>\n"
            "Meaning: whenever ANTECEDENT holds, CONSEQUENT must hold. "
            "Plain expressions only, no extra text."),
    },
}

WIDTH_FRAMES = {
    "T6-width-fix": {
        "frame": ("module m(input wire [3:0] a, output wire [3:0] y);\n"
                  "{line}\nendmodule\n"),
        "bad": "4'b11111",
        "good": "4'b1111",
        "prompt": (
            "This Verilog has a width bug (5-bit literal on a 4-bit "
            "signal): `assign y = 4'b11111;`. Reply with ONLY the corrected "
            "assign line and nothing else."),
    },
    "T9-status-fix": {
        "frame": ("module s(input wire clk, output reg [2:0] status);\n"
                  "always @(posedge clk) status <= {expr};\nendmodule\n"),
        "bad": "4'b1000",
        "good": "3'b000",
        "line_is_expr": True,
        "prompt": (
            "This Verilog has a width bug (4-bit literal on a 3-bit "
            "signal): `status <= 4'b1000;`. This is a RESET value: after "
            "reset the register must read 0, so the replacement literal "
            "must be all zeros. Reply with ONLY the corrected "
            "right-hand-side expression (e.g. 3'b000) and nothing else."),
    },
}

ASSIGN_LINE = re.compile(r"^\s*assign\b[^;]*;", re.MULTILINE)


def extract_assign_line(text: str) -> str | None:
    """First assign statement, or a bare expression promoted to one.

    Tolerant of markdown inline-code backticks and leading LABEL: prefixes
    (ASSIGN:) around the statement (measured); strict about everything
    else — the Verilator lint behind this decides, not the extractor.
    """
    for raw in text.splitlines():
        core = re.sub(r"^[A-Za-z_]+:\s*", "", raw)
        line = core.strip().strip("`'\"~").strip()
        if re.match(r"^assign\b", line) and line.rstrip().endswith(";"):
            return line[:line.index(";") + 1]
    m = re.search(r"^\s*4'b[01]+\s*$", text, re.MULTILINE)
    if m:
        return f"assign y = {m.group(0).strip()};"
    return None


def assemble(task_id: str, text: str) -> str | None:
    """Model output -> complete artifact, or None if slots/line rejected."""
    if task_id in SKELETONS:
        spec = SKELETONS[task_id]
        slots = parse_slots(text, spec["labels"])
        if slots is None:
            return None
        if spec["kind"] == "sva-range":
            lo = parse_int_slot(slots["LOW"])
            hi = parse_int_slot(slots["HIGH"])
            if lo is None or hi is None or int(lo) > int(hi):
                return None
            prop = SVA_RANGE_SKELETON.format(
                name=spec["name"], ante=slots["ANTECEDENT"], lo=lo, hi=hi,
                cons=slots["CONSEQUENT"])
        elif spec["kind"] == "sva-past":
            # Requirement-trace gate: each slot must mention its required
            # signal (cheap intent check; formal proof checks truth).
            for label, needles in spec.get("mention", {}).items():
                if not any(n.lower() in slots[label].lower()
                           for n in needles):
                    return None
            prop = SVA_PAST_SKELETON.format(now=slots["NOW_EXPR"],
                                            past=slots["PAST_EXPR"])
            return prop  # proved directly by sby; no lint wrapper applies
        else:
            prop = SVA_SIMPLE_SKELETON.format(
                name=spec["name"], ante=slots["ANTECEDENT"],
                cons=slots["CONSEQUENT"])
        return f"module tb_sva({spec['ports']});\n{prop}endmodule\n"
    if task_id in WIDTH_FRAMES:
        spec = WIDTH_FRAMES[task_id]
        if spec.get("line_is_expr"):
            m = re.search(r"^\s*([73]'b[01]+)\s*$", text, re.MULTILINE)
            if m:
                return assemble_expr_frame(task_id, m.group(1))
            fence = re.search(r"```(?:\w+)?\s*\n(.*?)```", text, re.DOTALL)
            if fence:
                # accept full-module answers too: harvest the RHS literal
                m2 = re.search(r"([73]'b[01]+)", fence.group(1))
                if m2:
                    return assemble_expr_frame(task_id, m2.group(1))
            return None
        line = extract_assign_line(text)
        if line is None:
            return None
        if spec["bad"] in line or spec["good"] not in line:
            return None
        return spec["frame"].format(line=line)
    return None


def assemble_expr_frame(task_id: str, expr: str) -> str | None:
    spec = WIDTH_FRAMES[task_id]
    expr = expr.strip().strip(";").strip()
    if not re.fullmatch(r"[73]'b[01]+", expr):
        return None
    if spec["bad"] in expr or spec["good"] not in expr:
        return None
    return spec["frame"].format(expr=expr)


def constrained_prompt(task_id: str, fallback: str) -> str:
    """Skeleton prompt where one exists, else the task's own prompt."""
    if task_id in SKELETONS:
        return SKELETONS[task_id]["prompt"]
    if task_id in WIDTH_FRAMES:
        return WIDTH_FRAMES[task_id]["prompt"]
    return fallback


SAMPLED_RE = re.compile(r"\$(rose|fell)\(\s*([A-Za-z_][\w$]*)\s*\)")


def find_vacuity(text: str) -> list[str]:
    """Self-contradictory sampled-value usage (reviewer SSB's T2 catch,
    generalized deterministically): $rose(X) asserts X==1 this cycle, so a
    same-antecedent !X makes the antecedent unsatisfiable (vacuous PASS);
    symmetrically $fell(X) with bare X. Only the antecedent (left of |->)
    is examined, and identifiers inside other $functions ($past/$stable)
    are excluded — those refer to other cycles and are legitimate."""
    scope = text.split("|->")[0] if "|->" in text else text
    findings = []
    for func, sig in SAMPLED_RE.findall(scope):
        if func == "rose":
            if re.search(r"(?<![\w$])!\s*%s(?![\w$])" % re.escape(sig), scope):
                findings.append(f"$rose({sig}) with !{sig} in antecedent: "
                                "unsatisfiable antecedent (vacuous PASS)")
        else:
            bare = re.sub(r"\$[A-Za-z_]+\([^()]*\)", " ", scope)
            if re.search(r"(?<![\w$!])%s(?![\w$])" % re.escape(sig), bare):
                findings.append(f"$fell({sig}) with {sig} in antecedent: "
                                "unsatisfiable antecedent (vacuous PASS)")
    return findings
