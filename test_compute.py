"""Unit tests for the compute adapter + CPU-aware eval report."""
import json
import os
import tempfile
import unittest

from compute import BACKENDS, describe, load_config, record_envelope, split_suite
from eval_harness import evaluate, make_suite


class TestCompute(unittest.TestCase):
    def _cfg(self, **kw):
        d = {"backend": "local-cpu", "suite": "wb_dma", "timeout_s": 60}
        d.update(kw)
        return d

    def test_backends(self):
        self.assertEqual(BACKENDS, ("local-cpu", "free-cloud", "accelerated-external"))

    def test_load_json_config(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(self._cfg(), f)
            path = f.name
        try:
            cfg = load_config(path)
            self.assertEqual(cfg["backend"], "local-cpu")
            self.assertEqual(cfg["timeout_s"], 60)
        finally:
            os.unlink(path)

    def test_remote_needs_endpoint(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(self._cfg(backend="free-cloud"), f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_unknown_backend_rejected(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(self._cfg(backend="mars-gpu"), f)
            path = f.name
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            os.unlink(path)

    def test_describe_local(self):
        s = describe(self._cfg())
        self.assertIn("local-cpu", s)
        self.assertIn("no GPU", s)

    def test_split_stable_no_loss(self):
        ids = [f"T{i}" for i in range(10)]
        shards = split_suite(ids, 3)
        flat = sorted(sum(shards, []))
        self.assertEqual(flat, sorted(ids))
        self.assertEqual(len(shards), 3)
        with self.assertRaises(ValueError):
            split_suite(ids, 0)


class TestCpuReport(unittest.TestCase):
    def test_eval_reports_cpu_and_cost(self):
        rep = evaluate(make_suite(n_per_kind=2, seed=11))
        self.assertIn("avg_cpu_time_s", rep)
        self.assertIn("avg_cost_per_task_usd", rep)
        self.assertGreaterEqual(rep["avg_cpu_time_s"], 0.0)
        self.assertGreater(rep["avg_cost_per_task_usd"], 0.0)
        self.assertIn("tokens", rep)

    def test_eval_reports_closure_gates(self):
        rep = evaluate(make_suite(n_per_kind=2, seed=11))
        for k in ("closure_success_rate", "first_pass_rate",
                  "avg_closure_iterations", "median_closure_iterations",
                  "max_closure_iterations", "escalated_to_human"):
            self.assertIn(k, rep)
        self.assertGreaterEqual(rep["closure_success_rate"], 0.0)
        self.assertLessEqual(rep["closure_success_rate"], 1.0)
        self.assertLessEqual(rep["max_closure_iterations"], 3)


class TestEnvelope(unittest.TestCase):
    def test_envelope_carries_reproducibility_keys(self):
        env = record_envelope({"backend": "local-cpu"}, model="selected-open-llm",
                              seed=7, tool_versions={"verilator": "5.032"})
        for k in ("environment", "os", "cpu", "ram_gb", "model",
                  "quantization", "runtime", "runtime_version",
                  "tool_versions", "dataset_version", "benchmark_version",
                  "seed", "token_settings", "verification_config",
                  "artifact_hashes"):
            self.assertIn(k, env)
        self.assertEqual(env["seed"], 7)
        self.assertEqual(env["tool_versions"]["verilator"], "5.032")


if __name__ == "__main__":
    unittest.main(verbosity=2)
