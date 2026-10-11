"""Tests for the P4 framing record and the P4-E measurement spec: namespace
separation held, metric set complete, baselines recomputed, no training."""
import json
import os
import statistics
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def vals(node):
    return list(node.values()) if isinstance(node, dict) else list(node or [])


class TestFraming(unittest.TestCase):
    def test_namespace_separated(self):
        f = load("P4_FRAMING.json")
        self.assertIn("P4-SYS", json.dumps(f))
        self.assertIn("P4-TRAIN", json.dumps(f))
        blob = json.dumps(f).lower()
        self.assertIn("no training", blob)
        self.assertNotIn("training authorized", blob.replace(
            "no training authorization", ""))

    def test_p4e_has_no_training_scope(self):
        blob = json.dumps(load("P4_E_SPEC.json")).lower()
        self.assertNotIn("lora", blob)
        self.assertNotIn("finetun", blob)
        self.assertIn("never proposes training", blob)


class TestP4EMetrics(unittest.TestCase):
    def test_metric_set_complete(self):
        s = load("P4_E_SPEC.json")
        for m in ("latency_per_task_s", "tokens_per_task",
                  "cpu_ram_per_task", "verifier_runtime_s",
                  "closure_iterations", "candidate_count",
                  "cost_per_task_usd", "success_per_task"):
            self.assertIn(m, s["metrics"], m)

    def test_unmeasured_marked_tbd(self):
        s = load("P4_E_SPEC.json")
        self.assertEqual(s["baselines"]["cpu_ram_per_task"],
                         "TBD (instrument next run)")
        self.assertEqual(s["baselines"]["verifier_runtime_s"],
                         "TBD (instrument next run)")

    def test_baselines_recomputed(self):
        s = load("P4_E_SPEC.json")
        q = load("P3_C_PIPELINE_QWEN.json")
        t = vals(q["t4"]["samples"])
        self.assertAlmostEqual(
            s["baselines"]["Q1_T4_pipeline_qwen"]["mean_latency_s"],
            round(statistics.mean(v["latency_s"] for v in t), 1))
        r = list(q["r2"]["rows"].values())
        self.assertEqual(s["baselines"]["Q1_R2_pipeline_qwen"]["success"],
                         "20/20")
        self.assertEqual(len(r), 20)
        c1 = load("R4_CYCLE_1.json")
        self.assertEqual(s["baselines"]["R4C1_R2_pipeline_qwen"]["success"],
                         "19/22")

    def test_decision_rule_guarded(self):
        s = load("P4_E_SPEC.json")
        rule = json.dumps(s["decision_rule"]).lower()
        self.assertIn("false acceptances stay 0", rule)
        self.assertIn("frozen benchmarks", rule)


if __name__ == "__main__":
    unittest.main()
