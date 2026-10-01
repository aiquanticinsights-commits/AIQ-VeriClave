"""Unit tests for the E2 portability benchmark (pure compare + skip paths)."""
import unittest

from scripts.run_portability_benchmark import compare, mutant_spot


def _side(unitt=True, sha="aaa", lint=True, sby="PASS", mut=None):
    return {"checks": {
        "unittest": {"pass": unitt, "tests": ["1"]},
        "frm_traces": {"pass": True, "sha": sha, "events": 1},
        "verilator_lint": {"pass": lint, "rc": 0},
        "yosys_synth": {"pass": True, "rc": 0},
        "sby_demo": {"pass": True, "status": sby}},
        "_mut_spot": {"classifications": mut if mut is not None else {}}}


class TestCompare(unittest.TestCase):
    def test_all_equivalent(self):
        m = {"M001": "KILLED", "M002": "SURVIVED"}
        rows = compare(_side(mut=m), _side(mut=dict(m)),
                       {"formal_result": "PASS"})
        bad = {k: v for k, v in rows.items() if v["variance"] not in ("none",)}
        self.assertEqual(bad, {})

    def test_diverged(self):
        rows = compare(_side(mut={"M001": "KILLED"}),
                       _side(mut={"M001": "SURVIVED"}),
                       {"formal_result": "PASS"})
        self.assertEqual(rows["mutation/spot"]["variance"], "DIVERGED")

    def test_unmeasured(self):
        rows = compare(_side(), _side(), {"formal_result": "PASS"})
        # empty mutant spots on both sides -> UNMEASURED, never EQUIVALENT
        self.assertEqual(rows["mutation/spot"]["variance"], "UNMEASURED")

    def test_formal_fail(self):
        rows = compare(_side(), _side(), {"formal_result": "FAIL"})
        self.assertEqual(rows["formal/sby-demo"]["variance"], "DIVERGED")


class TestLegParsing(unittest.TestCase):
    def test_markers(self):
        from scripts.run_portability_benchmark import parse_leg_output
        log = ('noise\n@@PORTABILITY@@\n{"a": 1}\n@@MUT@@\n{"b": 2}\n'
               'mutant spot done: x\ntail')
        doc, mut = parse_leg_output(log)
        self.assertEqual((doc, mut), ({"a": 1}, {"b": 2}))

    def test_malformed_raises(self):
        from scripts.run_portability_benchmark import parse_leg_output
        with self.assertRaises((IndexError, ValueError)):
            parse_leg_output("no markers here")
        with self.assertRaises((IndexError, ValueError)):
            parse_leg_output("@@PORTABILITY@@\n{bad\n@@MUT@@\n{}")


class TestOverall(unittest.TestCase):
    def test_pass_requires_all_clean(self):
        from scripts.run_portability_benchmark import overall_pass
        good = {"a": {"variance": "none"}, "b": {"variance": "none"}}
        self.assertTrue(overall_pass(good))

    def test_unmeasured_fails(self):
        from scripts.run_portability_benchmark import overall_pass
        self.assertFalse(overall_pass({"a": {"variance": "none"},
                                       "b": {"variance": "UNMEASURED"}}))

    def test_diverged_fails(self):
        from scripts.run_portability_benchmark import overall_pass
        self.assertFalse(overall_pass({"a": {"variance": "DIVERGED"}}))

    def test_drift_fails(self):
        from scripts.run_portability_benchmark import overall_pass
        self.assertFalse(overall_pass({"a": {"variance": "version-drift"}}))

    def test_empty_fails(self):
        from scripts.run_portability_benchmark import overall_pass
        self.assertFalse(overall_pass({}))


class TestDockerMountContract(unittest.TestCase):
    def test_mounts_parent_not_rtl_dir(self):
        # Regression for the wrong-tree mount: docker_leg must mount the
        # rideprotect-rv PARENT (so /work/rideprotect-rv/rtl/... resolves),
        # never a deeper dir. Captured from the sh() call args.
        import unittest.mock
        import scripts.run_portability_benchmark as bench
        seen = {}

        def fake_sh(cmd, timeout_s=0, cwd=""):
            seen["cmd"] = cmd
            if cmd[0] == "docker" and "build" in cmd:
                return 0, ""
            if cmd[0] == "docker" and "run" in cmd:
                vols = [cmd[i + 1] for i, c in enumerate(cmd)
                        if c == "-v"]
                seen["vols"] = vols
                return 0, ("@@PORTABILITY@@\n"
                           '{"checks": {"unittest": {"pass": true}}}'
                           "\n@@MUT@@\n{}"
                           "\nmutant spot done:\n")
            return 0, ""

        with unittest.mock.patch.object(bench, "sh", side_effect=fake_sh):
            out = bench.docker_leg("/tmp/never",
                                   "/r/rideprotect-rv/rtl/wb_dma.v")
        mnt = [v for v in seen["vols"] if "/work/rideprotect-rv:" in v]
        self.assertEqual(len(mnt), 1)
        # source must be the rideprotect-rv PARENT (so that
        # /work/rideprotect-rv/rtl/wb_dma.v resolves), never the rtl dir
        # itself (the measured wrong-tree bug) nor the .v file.
        self.assertIn("rideprotect-rv:/work/rideprotect-rv", mnt[0])
        self.assertNotIn("wb_dma.v", mnt[0])
        self.assertIn("_mut_spot", out)
    def test_skip_without_rtl(self):
        import sim_frm
        from scripts.run_portability_benchmark import mutant_spot
        orig = sim_frm.DEFAULT_RTL
        try:
            sim_frm.DEFAULT_RTL = "/nonexistent/x.v"
            res = mutant_spot("/tmp/never")
            self.assertEqual(res["classifications"], {})
            self.assertIn("skipped", res)
        finally:
            sim_frm.DEFAULT_RTL = orig


if __name__ == "__main__":
    unittest.main(verbosity=2)
