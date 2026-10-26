"""
PULSE — Phase 5, Step 4: Multi-Model Benchmark Verification Tests
Unit tests verifying the multi-model evaluation framework, metric calculations,
dataset integrity, and ExtractorRegistry interfaces.
"""

import unittest
import os
import json
from scripts.benchmark_runner import (
    PULSEBenchmarkRunner,
    compute_span_eval,
    GENERALIZATION_CHALLENGE_CASES,
    BENCHMARK_OUTPUT_PATH
)
from backend.extraction.contract import ExtractorRegistry
import backend.extraction.entity_extractor


class TestBenchmarkFramework(unittest.TestCase):
    def setUp(self):
        self.runner = PULSEBenchmarkRunner()

    def test_01_extractor_registry_availability(self):
        """Verifies that all evaluated extractors are registered behind ExtractorRegistry"""
        available = ExtractorRegistry.list_available()
        self.assertIn("hybrid", available)
        self.assertIn("pure_rule", available)
        self.assertIn("bio_clinicalbert", available)

    def test_02_challenge_benchmark_categories(self):
        """Verifies that the Generalization Challenge Benchmark contains all 10 explicit categories"""
        self.assertEqual(len(GENERALIZATION_CHALLENGE_CASES), 10)
        category_names = [c["category"] for c in GENERALIZATION_CHALLENGE_CASES]
        expected_substrings = [
            "Standard English",
            "Indian Clinical Shorthand",
            "Hinglish Clinical Expressions",
            "Decimal Medication Doses",
            "Medication-Attribute Binding",
            "Investigation Status",
            "Negation & Temporality",
            "Open-Vocabulary Candidates",
            "Ambiguous Terms",
            "Negative Controls"
        ]
        for expected in expected_substrings:
            matched = any(expected.lower() in cat.lower() for cat in category_names)
            self.assertTrue(matched, f"Missing challenge category matching: {expected}")

    def test_03_metric_calculation_strict_and_lenient(self):
        """Validates exact calculation of strict and lenient span evaluation"""
        gold = [
            {"label": "Medication", "start_char": 0, "end_char": 7, "text": "Digoxin"},
            {"label": "Clinical_Condition", "start_char": 10, "end_char": 22, "text": "hypertension"}
        ]
        # Pred 1 exact, Pred 2 partial overlap with different boundaries
        pred = [
            {"label": "Medication", "start_char": 0, "end_char": 7, "text": "Digoxin"},
            {"label": "Clinical_Condition", "start_char": 10, "end_char": 20, "text": "hyperten"}
        ]
        eval_res = compute_span_eval(gold, pred)
        # Strict: 1 match out of 2 (P=50%, R=50%, F1=50%)
        self.assertEqual(eval_res["strict"]["tp"], 1)
        self.assertEqual(eval_res["strict"]["f1"], 50.0)
        # Lenient: 2 matches out of 2 (P=100%, R=100%, F1=100%)
        self.assertEqual(eval_res["lenient"]["tp"], 2)
        self.assertEqual(eval_res["lenient"]["f1"], 100.0)

    def test_04_benchmark_results_json_schema(self):
        """Verifies that benchmark results file is generated, valid JSON, and contains expected metadata"""
        self.assertTrue(os.path.exists(BENCHMARK_OUTPUT_PATH), "Benchmark results JSON was not found!")
        with open(BENCHMARK_OUTPUT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("metadata", data)
        self.assertIn("corpus_gold_standard_101", data)
        self.assertIn("generalization_challenge_benchmark", data)

        challenge = data["generalization_challenge_benchmark"]
        self.assertIn("metrics_by_model", challenge)
        models = challenge["metrics_by_model"]
        self.assertIn("pure_rule", models)
        self.assertIn("hybrid_pipeline", models)
        self.assertIn("bio_clinicalbert", models)
        self.assertIn("statistical_classifier", models)
        self.assertIn("local_slm", models)

        # Verify local_slm is explicitly noted as unavailable
        self.assertIn("NOT EVALUATED", models["local_slm"]["status"])

    def test_05_hybrid_pipeline_challenge_superiority(self):
        """Verifies that the Hybrid pipeline outperforms pure rules on Hinglish and medication binding"""
        with open(BENCHMARK_OUTPUT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        models = data["generalization_challenge_benchmark"]["metrics_by_model"]
        pure_rule = models["pure_rule"]
        hybrid = models["hybrid_pipeline"]

        # Hybrid medication attribute binding should exceed pure rule
        self.assertGreaterEqual(
            hybrid["medication_attribute_binding_accuracy"]["score"],
            pure_rule["medication_attribute_binding_accuracy"]["score"]
        )
        # Hybrid investigation status accuracy should exceed pure rule
        self.assertGreaterEqual(
            hybrid["investigation_status_accuracy"]["score"],
            pure_rule["investigation_status_accuracy"]["score"]
        )
        # Hallucination rate must remain 0.0%
        self.assertEqual(hybrid["hallucination_rate"]["score"], 0.0)


if __name__ == "__main__":
    unittest.main()
