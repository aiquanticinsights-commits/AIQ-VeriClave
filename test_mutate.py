"""Unit tests for the mutation seeder (pure — no tools, no RTL needed)."""
import os
import tempfile
import unittest

from mutate import OPERATORS, apply_mutation, candidates, seed_catalog

SRC = """module m(input wire clk, input wire rst, input wire [3:0] a,
output wire [3:0] y, output wire irq);
reg [3:0] cnt;
wire big = (cnt >= 4'd10);
always @(posedge clk) begin
if (rst) begin
cnt <= 4'b0000;
end else if (big && a != 4'd0) begin
cnt <= cnt + 1'b1;
end
end
assign y = ~cnt;
assign irq = cnt[1:0] == 2'b11 ? 1'b1 : 1'b0;
endmodule
"""


def _lines():
    return SRC.splitlines(keepends=True)


def _write_src():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "m.sv")
    with open(p, "w", encoding="utf-8") as f:
        f.write(SRC)
    return p


class TestOperators(unittest.TestCase):
    def test_registry(self):
        for op in ("REL_GT_GE", "ARITH_PLUS1", "BIT_IDX_P1",
                   "CTRL_COND_INVERT", "CTRL_STMT_DELETE", "SEQ_RESET_FLIP",
                   "SEQ_ENABLE_REMOVE", "CDC_STAGE_REMOVE"):
            self.assertIn(op, OPERATORS)

    def test_relational(self):
        lines = _lines()
        i = next(n for n, l in enumerate(lines) if ">=" in l and "4'd10" in l)
        out = apply_mutation(lines, {"line": i, "op": "REL_GT_GE"})
        self.assertIsNone(out)  # >= has no bare > to widen (guard holds)
        j = next(n for n, l in enumerate(lines) if "!=" in l)
        out = apply_mutation(lines, {"line": j, "op": "REL_EQ_NE"})
        self.assertIsNone(out)  # == absent: inapplicable, not forced

    def test_arith(self):
        lines = _lines()
        i = next(n for n, l in enumerate(lines) if "4'd10" in l)
        out = apply_mutation(lines, {"line": i, "op": "ARITH_PLUS1",
                                     "detail": "10@1"})
        self.assertIn("4'd11", "".join(out))
        out = apply_mutation(lines, {"line": i, "op": "ARITH_MINUS1",
                                     "detail": "10@1"})
        self.assertIn("4'd9", "".join(out))

    def test_bit_index(self):
        lines = _lines()
        i = next(n for n, l in enumerate(lines) if "[1:0]" in l)
        out = apply_mutation(lines, {"line": i, "op": "BIT_IDX_P1"})
        self.assertIn("[2:0]", "".join(out))

    def test_bit_index_lo_guard(self):
        # lo=0 minus-1 would invent a negative index: seeder refuses,
        # runner never sees it (documented construction guard).
        lines = ["wire [1:0] x;\n"]
        self.assertIsNone(apply_mutation(lines, {"line": 0,
                                                 "op": "BIT_IDX_M1"}))
        lines = ["wire [5:2] x;\n"]
        out = apply_mutation(lines, {"line": 0, "op": "BIT_IDX_M1"})
        self.assertIn("[5:1]", "".join(out))

    def test_neg_toggle(self):
        lines = _lines()
        i = next(n for n, l in enumerate(lines) if "assign y" in l)
        out = apply_mutation(lines, {"line": i, "op": "BIT_NEG_TOGGLE"})
        self.assertNotIn("~cnt", "".join(out))

    def test_cond_invert(self):
        lines = _lines()
        i = next(n for n, l in enumerate(lines) if l.strip() == "if (rst) begin")
        out = apply_mutation(lines, {"line": i, "op": "CTRL_COND_INVERT"})
        self.assertIn("!(rst)", "".join(out))

    def test_stmt_delete(self):
        lines = _lines()
        i = next(n for n, l in enumerate(lines) if "cnt <=" in l and "0000" in l)
        out = apply_mutation(lines, {"line": i, "op": "CTRL_STMT_DELETE"})
        self.assertEqual(len(out), len(lines) - 1)

    def test_reset_flip(self):
        lines = ["cnt <= 1'b0;\n", "flag <= 1'b1;\n"]
        out = apply_mutation(lines, {"line": 0, "op": "SEQ_RESET_FLIP"})
        self.assertIn("1'b1", "".join(out))
        out = apply_mutation(lines, {"line": 1, "op": "SEQ_RESET_FLIP"})
        self.assertIn("1'b0", "".join(out))

    def test_enable_remove(self):
        lines = _lines()
        i = next(n for n, l in enumerate(lines) if "big &&" in l)
        out = apply_mutation(lines, {"line": i, "op": "SEQ_ENABLE_REMOVE"})
        self.assertIn("&& 1'b1", "".join(out))

    def test_unknown_op(self):
        self.assertIsNone(apply_mutation(_lines(), {"line": 0, "op": "NOPE"}))
        self.assertIsNone(apply_mutation(_lines(), {"line": 9999,
                                                    "op": "REL_GT_GE"}))


class TestCatalog(unittest.TestCase):
    def test_deterministic(self):
        p = _write_src()
        a = seed_catalog([p], 10, seed=7)
        b = seed_catalog([p], 10, seed=7)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 10)
        ids = [m["id"] for m in a]
        self.assertEqual(ids, sorted(ids))

    def test_covers_operator_families(self):
        p = _write_src()
        ops = {m["op"] for m in seed_catalog([p], 200, seed=7)}
        for fam in ("REL_", "ARITH_", "BIT_", "CTRL_", "SEQ_"):
            self.assertTrue(any(o.startswith(fam) for o in ops), fam)

    def test_empty_file(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "e.sv")
        open(p, "w").write("// nothing\n")
        self.assertEqual(seed_catalog([p], 5), [])


class TestStratify(unittest.TestCase):
    def test_balanced(self):
        from mutate import stratify
        big = ([{"id": "x", "op": "ARITH_PLUS1", "file": "a"}] * 50
               + [{"id": "y", "op": "REL_EQ_NE", "file": "a"}] * 3
               + [{"id": "z", "op": "CDC_STAGE_REMOVE", "file": "b"}] * 2)
        out = stratify(big, 10, seed=7)
        self.assertEqual(len(out), 10)
        self.assertEqual([m["id"] for m in out],
                         ["M%03d" % (i + 1) for i in range(10)])
        ops = [m["op"] for m in out]
        self.assertIn("REL_EQ_NE", ops)
        self.assertIn("CDC_STAGE_REMOVE", ops)
        self.assertLess(ops.count("ARITH_PLUS1"), 8)

    def test_deterministic(self):
        from mutate import stratify
        big = [{"id": str(i), "op": "ARITH_PLUS1", "file": "a"}
               for i in range(20)]
        self.assertEqual(stratify(big, 10, seed=7),
                         stratify(big, 10, seed=7))


if __name__ == "__main__":
    unittest.main(verbosity=2)
