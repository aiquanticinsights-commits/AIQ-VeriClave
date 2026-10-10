"""Hermetic tests for the R-4 scale runner. No models, no lint: pool rule,
row shape, config pins. The pool rule (constraint agreement) is the frozen
gate that keeps misleading prompts out of scale data."""
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
import sys
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))

from r4_scale_run import (MODEL_ID, SPEC_TAG, TIMEOUT_R2, build_row,  # noqa: E402
                          pool_cases)


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


class TestR4Pool(unittest.TestCase):
    def test_pool_is_p2_plus_agreeing_r2b(self):
        """Amendment A1: agreement now requires width match too. Cycle-1
        lesson: R2B-R-00/01 matched on expect (0==0) but computed width 4
        vs true width 1 — a wrong-line constraint. Both are excluded with
        recorded width-mismatch reasons; the pool is P2-only until
        agreeing real cases exist."""
        pool, excluded = pool_cases()
        origins = [o for o, _ in pool]
        self.assertEqual(origins.count("P2"), 20)
        self.assertEqual([c["id"] for o, c in pool if o == "R2B"], [])
        self.assertEqual(len(excluded), 11)
        wdrop = {e["id"]: e for e in excluded
                 if e["id"] in ("R2B-R-00", "R2B-R-01")}
        self.assertEqual(len(wdrop), 2)
        for e in wdrop.values():
            self.assertNotEqual(e["con_width"], e["case_width"])
        for e in excluded:
            self.assertTrue(e["reason"] or
                            e["con_width"] != e["case_width"], e["id"])

    def test_row_shape_feeds_assessor(self):
        r = {"stage_rank": {"abstained": False, "answer": "assign q = 1'b0;",
                            "n_passing": 4, "sim": "not-run"},
             "stage_constraint": {"ok": True}, "latency_s": 1.5,
             "tokens": 100}
        row = build_row("P2", {"id": "P2-R2-00"}, r, 1)
        for k in ("cycle", "origin", "case", "closed", "first_pass",
                  "n_passing", "n_candidates", "abstained", "sim",
                  "answer", "constraint", "latency_s", "tokens"):
            self.assertIn(k, row, k)
        self.assertEqual((row["cycle"], row["origin"]), (1, "P2"))
        self.assertTrue(row["closed"])

    def test_config_pins(self):
        import r4_scale_run as r
        self.assertEqual(MODEL_ID, "qwen2.5-coder-14b-instruct")
        self.assertEqual(TIMEOUT_R2, 3600)
        self.assertEqual(SPEC_TAG, "p3-r4-scale-frozen")
        self.assertTrue(r.TRAJ_PATH.endswith("R4_TRAJECTORIES.json"))


class TestR4Verdict(unittest.TestCase):
    """The verdict is a readout: pass-rate math, the frozen (not invented)
    bar, FA re-derivation, and the recorded exclusions must all agree."""

    def test_pass_rate_math(self):
        cyc = load("R4_CYCLE_1.json")
        v = load("P3_R4_VERDICT.json")
        self.assertEqual(len(cyc["rows"]), 22)
        self.assertEqual(cyc["closed"], 19)
        self.assertEqual(v["result"]["pass_rate_exact"], "19/22")
        self.assertAlmostEqual(v["result"]["pass_rate"], 19 / 22, places=4)

    def test_frozen_bar_and_outcome(self):
        v = load("P3_R4_VERDICT.json")
        self.assertEqual(v["bar_applied"]["bar"],
                         "closes >= 4 AND false_acceptances == 0")
        self.assertIn("NO R-4-specific acceptance bar was ever frozen",
                      v["bar_applied"]["provenance"])
        self.assertIn("PASS", v["bar_applied"]["outcome"])
        self.assertIn("PASS", v["closure"]["status"])

    def test_false_acceptances_rederived(self):
        import r2_pipeline
        from p2_bench import r2_cases
        from repair import value_gate
        p2 = {c["id"]: c for c in r2_cases()}
        r2b = {c["id"]: c for c in load("P3_R2B_REAL.json")["cases"]}
        cyc = load("R4_CYCLE_1.json")
        fa = []
        for cid, row in cyc["rows"].items():
            ans = row.get("answer")
            if not ans:
                continue
            case = p2[row["case"]] if row["origin"] == "P2" \
                else r2b[row["case"]]
            line = r2_pipeline._assign_line(ans) or ans
            if not value_gate(line, case["expect_value"], case["bad"]):
                fa.append(cid)
        self.assertEqual(fa, [])
        self.assertEqual(cyc["false_acceptances"], 0)

    def test_exclusions_recorded(self):
        cyc = load("R4_CYCLE_1.json")
        v = load("P3_R4_VERDICT.json")
        self.assertEqual(len(cyc["excluded"]), 9)
        self.assertEqual(len(v["exclusions"]["who"]), 9)
        self.assertFalse(v["closure"]["training_authorized"])

    def test_no_plain_arm_mixed_in(self):
        """R-4 is pipeline-recipe only: the cycle doc must show the Qwen
        pipeline runner's signature on every row, no plain-regime rows."""
        cyc = load("R4_CYCLE_1.json")
        self.assertEqual(cyc["spec_tag"], "p3-r4-scale-frozen")
        self.assertEqual(cyc["model_id"], "qwen2.5-coder-14b-instruct")
        for row in cyc["rows"].values():
            self.assertIn("n_candidates", row)
            self.assertIn("constraint", row)


class TestCycle2Closeout(unittest.TestCase):
    def test_closeout_matches_cycle_file(self):
        cyc = load("R4_CYCLE_2.json")
        v = load("P3_R4_CYCLE2_CLOSEOUT.json")
        self.assertEqual(len(cyc["rows"]), 20)
        self.assertEqual(cyc["closed"], 20)
        self.assertEqual(cyc["false_acceptances"], 0)
        self.assertEqual(v["result"]["pass_rate_exact"], "20/20")
        self.assertEqual(v["evaluated"]["passing_candidates"], 83)
        self.assertEqual(v["cumulative"]["positives"], 266)
        self.assertEqual(v["closure"]["status"], "CLOSED")
        self.assertFalse(v["closure"]["training_authorized"])

    def test_cycle2_pool_is_p2_only(self):
        """The 11 excluded R-2b cases stayed out: every cycle-2 row is
        P2-origin, and the exclusion list names all 11."""
        cyc = load("R4_CYCLE_2.json")
        self.assertEqual({r["origin"] for r in cyc["rows"].values()}, {"P2"})
        self.assertEqual(len(cyc["excluded"]), 11)
        v = load("P3_R4_CYCLE2_CLOSEOUT.json")
        self.assertIn("NOT RUN", v["plain_regime"])


class TestD1Analysis(unittest.TestCase):
    def test_numbers_match_live_artifacts(self):
        a = load("P3_D1_SCALE_ANALYSIS.json")
        v2 = load("P3_D_READINESS_V2.json")
        self.assertEqual(a["current_state"]["positives"],
                         v2["measurements"]["d1_scale"]["positive_trajectories"])
        self.assertEqual(a["current_state"]["gap"],
                         1000 - a["current_state"]["positives"])
        self.assertEqual(v2["grades"]["d1_scale"], "FAIL")

    def test_no_execution_smuggled_in(self):
        a = load("P3_D1_SCALE_ANALYSIS.json")
        self.assertFalse(a["training_authorized"])
        blob = json.dumps(a).lower()
        self.assertIn("without explicit authorization", blob)
        self.assertIn("forbidden", blob)


if __name__ == "__main__":
    unittest.main()
