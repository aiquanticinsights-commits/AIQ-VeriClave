"""Unit tests for adopted architecture: policy, evidence ledger, P0 profile."""
import unittest

from evidence import (EVIDENCE_OPTIONAL, KNOWN_VERDICTS, EvidenceLedger,
                      EvidenceRecord)
from p0 import (DASHBOARD_FIELDS, P0_BENCHMARKS, P0_PROFILE, PHASES,
                run_ablation)
from policy import (DETERMINISTIC_OPS, HUMAN_SIGNOFF_ACTIONS, LLM_LANES,
                    SMALL_MODELS, assert_no_auto_merge, is_deterministic,
                    requires_human_signoff)
from router import BAKEOFF_CANDIDATES, BASELINE_GENERATOR, Task


class TestPolicy(unittest.TestCase):
    def test_deterministic_allowlist_complete(self):
        for op in ("syntax-validation", "compilation", "rtl-simulation",
                   "reference-model-comparison", "assertion-execution",
                   "formal-proof", "mutation-generation",
                   "mutation-kill-measurement", "coverage-measurement",
                   "requirement-traceability", "evidence-recording",
                   "test-reproducibility", "pass-fail-thresholds",
                   "security-privacy-rules", "artifact-hashing", "versioning"):
            self.assertTrue(is_deterministic(op), op)
        self.assertEqual(len(DETERMINISTIC_OPS), 16)

    def test_llm_lanes_bounded(self):
        self.assertEqual(len(LLM_LANES), 6)
        self.assertIn("C-sva-generation", LLM_LANES)

    def test_small_model_table(self):
        self.assertEqual(SMALL_MODELS["router"], "86m-encoder")
        self.assertEqual(SMALL_MODELS["token-cost-routing"], "deterministic")
        self.assertEqual(SMALL_MODELS["sva-generation"], "medium-coding-model")
        self.assertEqual(SMALL_MODELS["test-generation"], "medium-coding-model")
        self.assertEqual(SMALL_MODELS["bug-classification"], "small-model")

    def test_signoff_guard(self):
        for a in ("rtl-merge", "sign-off", "tapeout-release", "repair-merge"):
            self.assertTrue(requires_human_signoff(a))
            with self.assertRaises(PermissionError):
                assert_no_auto_merge(a)
        self.assertFalse(requires_human_signoff("draft-testbench"))


class TestLedger(unittest.TestCase):
    def _rec(self, rid="R-017", verdict="PASS", checks=None, signed="eng"):
        return EvidenceRecord(rid, "A-017", checks or {"equiv": True},
                              verdict, signed_by=signed)

    def test_chain_integrity(self):
        L = EvidenceLedger()
        L.append(self._rec())
        L.append(self._rec("R-018", "DISPOSITIONED", {}, "eng2"))
        self.assertTrue(L.verify_chain())
        self.assertAlmostEqual(L.audit_completeness(), 1.0)

    def test_tamper_detected(self):
        L = EvidenceLedger()
        L.append(self._rec())
        L.records[0].verdict = "FAIL"
        self.assertFalse(L.verify_chain())

    def test_incomplete_record_breaks_c4(self):
        L = EvidenceLedger()
        L.append(EvidenceRecord("R-1", "A-1", {}, "PENDING", signed_by="eng"))
        self.assertLess(L.audit_completeness(), 1.0)

    def test_frozen_verdict_states_known(self):
        for v in ("EXECUTED", "NOT_EXECUTED", "PASS", "FAIL", "UNPROVEN",
                  "UNAVAILABLE", "SKIPPED_BY_POLICY", "DISPOSITIONED"):
            self.assertIn(v, KNOWN_VERDICTS)
        self.assertNotIn("PENDING", KNOWN_VERDICTS)

    def test_not_executed_is_explicit_not_silent(self):
        L = EvidenceLedger()
        L.record_not_executed("R-9", "Vivado/synth", "no license on runner",
                              run_id="ci-1")
        self.assertAlmostEqual(L.audit_completeness(), 1.0)
        rec = L.records[0]
        self.assertEqual(rec.verdict, "NOT_EXECUTED")
        # rewriting NOT_EXECUTED into PASS breaks the hash chain by construction
        rec.verdict = "PASS"
        self.assertFalse(L.verify_chain())

    def test_unknown_verdict_breaks_c4(self):
        L = EvidenceLedger()
        L.append(EvidenceRecord("R-1", "A-1", {"equiv": True}, "MAYBE"))
        self.assertLess(L.audit_completeness(), 1.0)

    def test_anonymous_signoff_denied(self):
        L = EvidenceLedger()
        with self.assertRaises(ValueError):
            L.signoff("R-1", "")
        with self.assertRaises(ValueError):
            L.signoff("R-1", "   ")
        r = L.signoff("R-1", "satish")
        self.assertEqual(r.signed_by, "satish")

    def test_empty_ledger_complete(self):
        self.assertEqual(EvidenceLedger().audit_completeness(), 1.0)


class TestP0(unittest.TestCase):
    def test_profile_minimal(self):
        # Frozen architecture: P0 is model-agnostic (bake-off winner alias).
        self.assertEqual(P0_PROFILE["generators"], [BASELINE_GENERATOR])
        self.assertEqual(P0_PROFILE["generators"], ["selected-open-llm"])
        self.assertNotIn("qwen3-coder-next", P0_PROFILE["generators"])
        self.assertEqual(P0_PROFILE["bon"], 3)
        self.assertEqual(P0_PROFILE["router"], "deterministic")
        self.assertEqual(P0_PROFILE["train"], "nothing")
        self.assertEqual(P0_PROFILE["max_rounds"], 3)  # hard closure boundary

    def test_bakeoff_slate(self):
        for m in ("gpt-oss-20b", "deepseek-coder-6.7b", "llama-3.1-8b"):
            self.assertIn(m, BAKEOFF_CANDIDATES)

    def test_benchmarks_split(self):
        self.assertIn("P0-A", P0_BENCHMARKS)
        self.assertIn("P0-C", P0_BENCHMARKS)

    def test_dashboard_fields(self):
        for f in ("kill_rate", "audit_complete", "false_positive_rate",
                  "avg_cost_per_task", "avg_cpu_time_per_task",
                  "avg_tokens_per_task",
                  # Frozen Gates B/D/E fields
                  "closure_success_rate", "first_pass_rate",
                  "avg_closure_iterations", "median_closure_iterations",
                  "max_closure_iterations", "engineer_review_time_per_task",
                  "human_rejection_rate", "human_override_rate",
                  "evidence_items_reviewed_per_task", "signoff_status",
                  "environment", "tool_versions", "model_runtime",
                  "benchmark_version", "dataset_version", "seed",
                  "artifact_hashes", "cross_env_variance"):
            self.assertIn(f, DASHBOARD_FIELDS)

    def test_phases_cover_0_to_7(self):
        self.assertEqual(sorted(PHASES), [0, 1, 2, 3, 4, 5, 6, 7])
        self.assertIn("CPU", PHASES[0])
        self.assertIn("GRPO", PHASES[6])
        self.assertEqual(P0_PROFILE["inference"], "lmstudio-local")
        self.assertEqual(P0_PROFILE["compute"], "local-cpu")

    def test_ablation_shape_and_cost_order(self):
        def gen(g, t, r):
            return "o"

        def ver(g, t, o):
            return {"syntax": True, "equiv": True, "proof": True}

        rows = run_ablation(Task("T", "mutant-kill", 2), gen, ver)
        self.assertEqual(sorted(rows), [1, 3, 5])  # CPU-first P0 default
        for n, row in rows.items():
            self.assertTrue(row["closed"])
            for k in ("rounds", "approvals", "est_cost_usd",
                      "escalated_to_human"):
                self.assertIn(k, row)
            self.assertFalse(row["escalated_to_human"])
        costs = [rows[n]["est_cost_usd"] for n in (1, 3, 5)]
        self.assertEqual(costs, sorted(costs))
        wide = run_ablation(Task("T", "mutant-kill", 2), gen, ver, ns=(1, 3, 5, 8))
        self.assertEqual(sorted(wide), [1, 3, 5, 8])


if __name__ == "__main__":
    unittest.main(verbosity=2)
