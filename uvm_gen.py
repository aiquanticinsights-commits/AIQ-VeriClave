"""Deterministic UVM TLM skeleton generator (templates, not LLM magic).

Gap closed: the flow spoke Python-FRM only; UVM shops need compilable
transaction-level components. This emits agent/driver/monitor/sequencer-item/
scoreboard skeletons from a small spec dict so generated structure is
reviewable and license-clean.

Honest boundary: SystemVerilog *constraint solving* happens inside the
simulator (VCS/Questa/Xcelium), not here. We generate `constraint` blocks and
`rand` fields for the solver to chew on; we never claim to solve constraints
in Python.
"""
from __future__ import annotations


def gen_agent(spec: dict) -> dict[str, str]:
    """spec: {name, vif, items: [{name, width, rand}], constraints: [str]}.

    Returns {filename: content} for item/driver/monitor/agent/scoreboard.
    """
    name = spec["name"]
    fields = "\n".join(
        f"  rand bit [{it['width'] - 1}:0] {it['name']};" if it.get("rand") else
        f"  bit [{it['width'] - 1}:0] {it['name']};"
        for it in spec.get("items", []))
    constr = "\n".join(f"  constraint {c};" for c in spec.get("constraints", ["c_valid { 1; }"]))
    vif = spec.get("vif", f"{name}_if")

    item = (f"class {name}_item extends uvm_sequence_item;\n"
            f"  `uvm_object_utils({name}_item)\n{fields}\n{constr}\n"
            f"  function new(string name = \"{name}_item\");\n"
            f"    super.new(name);\n  endfunction\nendclass\n")
    driver = (f"class {name}_driver extends uvm_driver #({name}_item);\n"
              f"  `uvm_component_utils({name}_driver)\n"
              f"  virtual {vif} vif;\n"
              f"  function new(string name, uvm_component parent);\n"
              f"    super.new(name, parent);\n  endfunction\n"
              f"  task run_phase(uvm_phase phase);\n"
              f"    {name}_item tr;\n    forever begin\n"
              f"      seq_item_port.get_next_item(tr);\n"
              f"      // drive tr onto vif (fill per protocol)\n"
              f"      seq_item_port.item_done();\n    end\n  endtask\nendclass\n")
    monitor = (f"class {name}_monitor extends uvm_monitor;\n"
               f"  `uvm_component_utils({name}_monitor)\n"
               f"  virtual {vif} vif;\n"
               f"  uvm_analysis_port #({name}_item) ap;\n"
               f"  function new(string name, uvm_component parent);\n"
               f"    super.new(name, parent); ap = new(\"ap\", this);\n  endfunction\n"
               f"  task run_phase(uvm_phase phase);\n"
               f"    // sample vif -> item -> ap.write(item) (fill per protocol)\n"
               f"  endtask\nendclass\n")
    agent = (f"class {name}_agent extends uvm_agent;\n"
             f"  `uvm_component_utils({name}_agent)\n"
             f"  {name}_driver drv; {name}_monitor mon;\n"
             f"  uvm_sequencer #({name}_item) sqr;\n"
             f"  function new(string name, uvm_component parent);\n"
             f"    super.new(name, parent);\n  endfunction\n"
             f"  function void build_phase(uvm_phase phase);\n"
             f"    mon = {name}_monitor::type_id::create(\"mon\", this);\n"
             f"    if (is_active == UVM_ACTIVE) begin\n"
             f"      drv = {name}_driver::type_id::create(\"drv\", this);\n"
             f"      sqr = uvm_sequencer #({name}_item)::type_id::create(\"sqr\", this);\n"
             f"    end\n  endfunction\n"
             f"  function void connect_phase(uvm_phase phase);\n"
             f"    if (is_active == UVM_ACTIVE) drv.seq_item_port.connect(sqr.seq_item_export);\n"
             f"  endfunction\nendclass\n")
    sb = (f"class {name}_scoreboard extends uvm_scoreboard;\n"
          f"  `uvm_component_utils({name}_scoreboard)\n"
          f"  uvm_analysis_imp #({name}_item, {name}_scoreboard) imp;\n"
          f"  function new(string name, uvm_component parent);\n"
          f"    super.new(name, parent); imp = new(\"imp\", this);\n  endfunction\n"
          f"  function void write({name}_item tr);\n"
          f"    // compare against FRM/reference (fill per DUT)\n"
          f"  endfunction\nendclass\n")
    return {f"{name}_item.sv": item, f"{name}_driver.sv": driver,
            f"{name}_monitor.sv": monitor, f"{name}_agent.sv": agent,
            f"{name}_scoreboard.sv": sb}
