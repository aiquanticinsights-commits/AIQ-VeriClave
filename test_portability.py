"""Unit tests for portability probe (compare() pure; collect() live)."""
import os
import unittest

from portability import CATEGORIES, _mnt, _tool, collect, compare


def rec(env, **kw):
    d = {"env": env, "os": "X", "python": "3.0",
         "tools": {"verilator": "V", "yosys": "Y", "sby": "S"},
         "checks": {
             "unittest": {"pass": True, "tests": ["1"]},
             "frm_traces": {"pass": True, "sha": "aaa", "events": 1},
             "verilator_lint": {"pass": True, "rc": 0},
             "yosys_synth": {"pass": True, "rc": 0},
             "sby_demo": {"pass": True, "status": "PASS"}}}
    d.update(kw)
    return d


class TestCompare(unittest.TestCase):
    def test_identical_is_clean(self):
        doc = compare(rec("a"), rec("b"))
        bad = {k: v for k, v in doc["rows"].items()
               if v["variance"] not in ("none",)}
        # tools/python/os legitimately differ across envs -> version-drift
        for k, v in bad.items():
            self.assertEqual(v["variance"], "version-drift", k)
        self.assertEqual(doc["rows"]["frm_traces"]["variance"], "none")

    def test_trace_divergence_flagged(self):
        b = rec("b")
        b["checks"]["frm_traces"] = {"pass": True, "sha": "zzz", "events": 1}
        self.assertEqual(compare(rec("a"), b)["rows"]["frm_traces"]
                         ["variance"], "DIVERGED")

    def test_unmeasured_stays_unmeasured(self):
        b = rec("b")
        b["checks"]["sby_demo"] = {"pass": None, "reason": "UNAVAILABLE here"}
        row = compare(rec("a"), b)["rows"]["sby_demo"]
        self.assertEqual(row["variance"], "UNMEASURED")

    def test_fixture_rows_compare_by_outcome(self):
        a, b = rec("a"), rec("b")
        a["checks"]["verilator_lint"] = {"pass": True, "rc": 1,
                                         "fixture": False, "target": "wb_dma"}
        b["checks"]["verilator_lint"] = {"pass": True, "rc": 0,
                                         "fixture": True, "target": "cnt_formal"}
        row = compare(a, b)["rows"]["verilator_lint"]
        self.assertEqual(row["variance"], "none")

    def test_categories_cover_all_keys(self):
        d = rec("a")
        for k in list(d.keys()) + list(d["checks"].keys()):
            if k not in ("env", "checks"):
                self.assertIn(k, CATEGORIES)


class TestHelpers(unittest.TestCase):
    def test_tool_prefix(self):
        import os
        cmd = _tool("verilator") + ["--version"]
        if os.name == "nt":
            self.assertEqual(cmd[:2], ["wsl", "verilator"])
        else:
            self.assertTrue(cmd[0].endswith("verilator"))

    def test_mnt_roundtrip(self):
        import os
        if os.name == "nt":
            self.assertEqual(_mnt(r"C:\x\y"), "/mnt/c/x/y")
        else:
            self.assertEqual(_mnt("/a/b"), "/a/b")


class TestCollect(unittest.TestCase):
    @unittest.skipIf(os.environ.get("PORTABILITY_NESTED"),
                     "nested probe run: no recursion")
    def test_collect_shape(self):
        doc = collect("test-env")
        for k in ("env", "os", "python", "tools", "checks"):
            self.assertIn(k, doc)
        for k in ("unittest", "frm_traces", "verilator_lint", "yosys_synth",
                  "sby_demo"):
            self.assertIn(k, doc["checks"])
        self.assertEqual(doc["env"], "test-env")
        self.assertIn("sha", doc["checks"]["frm_traces"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
