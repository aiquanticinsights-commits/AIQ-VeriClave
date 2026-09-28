"""Unit tests for adoption-gap modules (deterministic, no simulators)."""
import unittest

from sim_adapters import (ADAPTERS, VivadoAdapter, detect_tool, normalize,
                          summarize)
from vcd_events import drift_report, parse_vcd
from formal_policy import PropertySpec, recommend, signoff_line
from uvm_gen import gen_agent

VCS_LOG = """Chronologic VCS simulator
Error-[SE] Syntax error in wb_dma.v, 42: unexpected token
Warning-LINT-LN net foo driven twice
UVM_ERROR @ 120ns: scoreboard mismatch, wb_dma.v: 88
TEST FAILED: dma_regression
"""
QUESTA_LOG = """vsim -c work.tb
** Error: (vsim-3033) wb_fifo.sv(17): Instantiation failed
** Warning: (vsim-3015) [PCDPC] - Port width mismatch
UVM_ERROR @ 45ns: prot_checker
# FAIL: fifo_test
"""
XCE_LOG = """xmsim: *E,TRUNIT: unbound instance in top.
xmsim: *W,DLNOHV: no hierarchy visible
UVM_FATAL axi_tb.sv: 203: fatal phase raised
TEST FAILED
"""
VIV_LOG = """ERROR: [XSIM 43-3322] wb_top.v: 55: syntax error
WARNING: [XSIM 43-3223] unconnected port
Failure: burst length mismatch
Test Failed: axi_stream_tb
"""
VCD = """$timescale 1ns $end
$scope module tb $end
$var wire 1 ! clk $end
$var wire 8 " data $end
$upscope $end
$enddefinitions $end
$dumpvars
0!
b00000000 "
$end
#5
1!
#10
0!
b00001111 "
#15
b00001110 "
"""


class TestAdapters(unittest.TestCase):
    def test_vcs(self):
        evs = normalize(VCS_LOG, "vcs")
        sev = [e.severity for e in evs]
        self.assertIn("error", sev)
        self.assertIn("failure", sev)
        self.assertTrue(any(e.file == "wb_dma.v" and e.line == 42 for e in evs))

    def test_questa(self):
        evs = normalize(QUESTA_LOG, "questa")
        self.assertTrue(any(e.severity == "error" and e.line == 17 for e in evs))
        self.assertTrue(any(e.severity == "failure" for e in evs))

    def test_xcelium(self):
        evs = normalize(XCE_LOG, "xcelium")
        self.assertTrue(any(e.severity == "error" for e in evs))
        self.assertTrue(any(e.file == "axi_tb.sv" and e.line == 203 for e in evs))

    def test_vivado(self):
        evs = normalize(VIV_LOG, "vivado-xsim")
        self.assertTrue(any(e.severity == "error" and e.line == 55 for e in evs))
        self.assertTrue(any(e.severity == "failure" for e in evs))

    def test_detect_and_summarize(self):
        self.assertEqual(detect_tool(VCS_LOG), "vcs")
        self.assertEqual(detect_tool(QUESTA_LOG), "questa")
        self.assertEqual(detect_tool(XCE_LOG), "xcelium")
        self.assertEqual(detect_tool(VIV_LOG), "vivado-xsim")
        s = summarize(normalize(VCS_LOG, "vcs"))
        self.assertEqual(s["errors"], 1)
        self.assertGreaterEqual(s["failures"], 2)
        self.assertEqual(set(ADAPTERS), {"verilator", "vcs", "questa", "xcelium", "vivado-xsim"})

    def test_verilator_adapter_present(self):
        self.assertIn("verilator", ADAPTERS)


class TestVcd(unittest.TestCase):
    def test_events(self):
        evs, final = parse_vcd(VCD)
        by = [(e.time, e.signal, e.old, e.new) for e in evs]
        self.assertIn((5, "clk", "0", "1"), by)
        self.assertIn((10, "data", "00000000", "00001111"), by)
        self.assertEqual(final["data"], "00001110")

    def test_drift_pinpoint(self):
        evs, _ = parse_vcd(VCD)
        drifts = drift_report(evs, {"data": [(10, "00001111"), (15, "00001111")]})
        self.assertEqual(len(drifts), 1)
        self.assertEqual((drifts[0].signal, drifts[0].time), ("data", 15))
        self.assertIn("cycle 15", drifts[0].sentence())

    def test_no_drift(self):
        evs, _ = parse_vcd(VCD)
        self.assertEqual(drift_report(evs, {"data": [(10, "00001111")]}), [])


class TestFormal(unittest.TestCase):
    def test_width_proves(self):
        p = recommend(PropertySpec("w", "width", 200))
        self.assertEqual(p.verdict, "PROVE")
        self.assertIn("PROVEN", signoff_line(p, "w"))

    def test_small_proves(self):
        p = recommend(PropertySpec("s", "safety", 32))
        self.assertEqual(p.verdict, "PROVE")

    def test_medium_bounds(self):
        p = recommend(PropertySpec("m", "safety", 80))
        self.assertEqual(p.verdict, "BOUND")
        self.assertIn("k=32", signoff_line(p, "m"))

    def test_protocol_abstracts(self):
        p = recommend(PropertySpec("p", "protocol", 500))
        self.assertEqual(p.verdict, "ABSTRACT")
        self.assertIn("assume-guarantee", signoff_line(p, "p"))

    def test_huge_short_budget_unprovable(self):
        p = recommend(PropertySpec("h", "safety", 500, time_budget_s=900))
        self.assertEqual(p.verdict, "UNPROVABLE-AT-BUDGET")
        self.assertIn("UNPROVABLE", signoff_line(p, "h"))


class TestUvm(unittest.TestCase):
    SPEC = {"name": "axi_stream", "vif": "axis_if",
            "items": [{"name": "data", "width": 32, "rand": True},
                      {"name": "last", "width": 1, "rand": False}],
            "constraints": ["c_len { data inside {[0:1023]}; }"]}

    def test_all_files(self):
        out = gen_agent(self.SPEC)
        self.assertEqual(set(out), {"axi_stream_item.sv", "axi_stream_driver.sv",
                                    "axi_stream_monitor.sv", "axi_stream_agent.sv",
                                    "axi_stream_scoreboard.sv"})

    def test_item_contents(self):
        item = gen_agent(self.SPEC)["axi_stream_item.sv"]
        self.assertIn("rand bit [31:0] data;", item)
        self.assertIn("constraint c_len", item)
        self.assertIn("uvm_sequence_item", item)

    def test_agent_wiring(self):
        agent = gen_agent(self.SPEC)["axi_stream_agent.sv"]
        self.assertIn("seq_item_port.connect(sqr.seq_item_export)", agent)
        self.assertIn("UVM_ACTIVE", agent)


if __name__ == "__main__":
    unittest.main(verbosity=2)
