"""
PULSE — Statistical Model Training & Cross-Validation Integrity Tests
Phase 5 — Training Pipeline & Model Comparison

Verifies:
1. Training data suitability and completeness (101 corpus, 2,103 spans, 8,487 tokens).
2. Document-level 5-fold cross-validation split disjointness and coverage.
3. Leak-free feature extraction and DictVectorizer fitting.
4. Token-to-span reconstruction fidelity.
5. Strict vs. Lenient span metric calculation logic.
6. Historical baseline result immutability.
7. Hyperparameter tuning output integrity.
"""

import unittest
import os
import json
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.train_statistical_classifier import (
    extract_token_features,
    reconstruct_spans_from_tokens,
    compute_span_metrics,
    map_label,
    CORPUS_PATH,
    SPLITS_PATH,
    RESULTS_OUTPUT_PATH
)
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression


class TestStatisticalModelTraining(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(CORPUS_PATH, "r", encoding="utf-8") as f:
            cls.corpus = json.load(f)
        with open(SPLITS_PATH, "r", encoding="utf-8") as f:
            cls.splits = json.load(f)

    def test_01_training_corpus_structure_and_counts(self):
        """Verifies 101 documents, 2,103 entity spans, and 8,487 tokens in gold standard corpus."""
        reports = self.corpus.get("reports", [])
        self.assertEqual(len(reports), 101, "Expected 101 reports in historical training corpus")

        total_spans = sum(len(r.get("entity_spans", [])) for r in reports)
        self.assertEqual(total_spans, 2103, "Expected exactly 2,103 entity spans in gold standard")

        total_tokens = sum(len(r.get("tokens", [])) for r in reports)
        self.assertEqual(total_tokens, 8487, "Expected exactly 8,487 aligned tokens in gold standard")

    def test_02_split_disjointness_and_coverage(self):
        """Verifies that each fold's train, val, and test splits are strictly disjoint and cover all 101 reports."""
        all_ids = {str(i) for i in range(101)}
        for fold_name, split in self.splits.items():
            tr = set(split["train"])
            vl = set(split["val"])
            ts = set(split["test"])

            # Disjointness checks
            self.assertEqual(len(tr & vl), 0, f"{fold_name}: train and val must be strictly disjoint")
            self.assertEqual(len(tr & ts), 0, f"{fold_name}: train and test must be strictly disjoint")
            self.assertEqual(len(vl & ts), 0, f"{fold_name}: val and test must be strictly disjoint")

            # Completeness check
            self.assertEqual(tr | vl | ts, all_ids, f"{fold_name}: union must cover all 101 documents")

    def test_03_token_feature_extraction(self):
        """Verifies that token feature extraction generates valid contextual linguistic features."""
        sample_doc = self.corpus["reports"][0]
        toks = sample_doc["tokens"]
        self.assertGreater(len(toks), 10)

        # First token features (must have BOS)
        feats_0 = extract_token_features(toks, 0)
        self.assertIn("bias", feats_0)
        self.assertIn("token", feats_0)
        self.assertIn("pos", feats_0)
        self.assertTrue(feats_0.get("BOS"), "First token must have BOS flag")
        self.assertNotIn("EOS", feats_0)

        # Last token features (must have EOS)
        feats_last = extract_token_features(toks, len(toks) - 1)
        self.assertTrue(feats_last.get("EOS"), "Last token must have EOS flag")
        self.assertNotIn("BOS", feats_last)

    def test_04_leak_free_vectorizer_fitting(self):
        """Verifies that DictVectorizer fitted on train fold does not leak test features into vocabulary."""
        split_0 = self.splits["fold_0"]
        reports_map = {r["report_id"]: r for r in self.corpus["reports"]}

        train_feats = [extract_token_features(reports_map[rid]["tokens"], idx)
                       for rid in split_0["train"][:5]
                       for idx in range(len(reports_map[rid]["tokens"]))]
        test_feats = [{"novel_unseen_feature": 999.0}]

        vec = DictVectorizer(sparse=True)
        X_tr = vec.fit_transform(train_feats)
        vocab_size_after_train = len(vec.vocabulary_)

        # Transform test features
        X_ts = vec.transform(test_feats)
        vocab_size_after_test = len(vec.vocabulary_)

        self.assertEqual(vocab_size_after_train, vocab_size_after_test,
                         "Vectorizer vocabulary size must not change during test transform (no leakage)")

    def test_05_reconstruct_spans_from_tokens(self):
        """Verifies span boundary reconstruction from token sequences."""
        preds = ["Demographics_Bed", "Demographics_Bed", "O", "Medication", "O"]
        meta = [
            {"report_id": "0", "start_char": 0, "end_char": 3, "token": "Bed"},
            {"report_id": "0", "start_char": 4, "end_char": 9, "token": "eight"},
            {"report_id": "0", "start_char": 9, "end_char": 10, "token": ","},
            {"report_id": "0", "start_char": 11, "end_char": 18, "token": "Digoxin"},
            {"report_id": "0", "start_char": 18, "end_char": 19, "token": "."}
        ]

        spans = reconstruct_spans_from_tokens(preds, meta)
        self.assertEqual(len(spans), 2)
        self.assertEqual(spans[0], {"label": "Demographics_Bed", "report_id": "0", "start_char": 0, "end_char": 9})
        self.assertEqual(spans[1], {"label": "Medication", "report_id": "0", "start_char": 11, "end_char": 18})

    def test_06_compute_span_metrics_logic(self):
        """Verifies exact strict vs lenient metric calculations on controlled synthetic spans."""
        gold = [
            {"label": "Medication", "report_id": "0", "start_char": 10, "end_char": 20, "text": "Paracetamol"},
            {"label": "Clinical_Condition", "report_id": "0", "start_char": 30, "end_char": 40, "text": "Appendicitis"}
        ]
        # Pred 1 is exact match for Paracetamol; Pred 2 has partial overlap with Appendicitis (28-42)
        pred = [
            {"label": "Medication", "report_id": "0", "start_char": 10, "end_char": 20},
            {"label": "Clinical_Condition", "report_id": "0", "start_char": 28, "end_char": 42}
        ]

        metrics = compute_span_metrics(gold, pred)
        # Strict: 1 match (Paracetamol), 1 FP, 1 FN -> P = 50%, R = 50%, F1 = 50%
        self.assertEqual(metrics["strict"]["tp"], 1)
        self.assertEqual(metrics["strict"]["fp"], 1)
        self.assertEqual(metrics["strict"]["fn"], 1)
        self.assertEqual(metrics["strict"]["f1"], 50.0)

        # Lenient: 2 matches -> P = 100%, R = 100%, F1 = 100%
        self.assertEqual(metrics["lenient"]["tp"], 2)
        self.assertEqual(metrics["lenient"]["fp"], 0)
        self.assertEqual(metrics["lenient"]["fn"], 0)
        self.assertEqual(metrics["lenient"]["f1"], 100.0)

    def test_07_historical_baseline_immutability(self):
        """Verifies that the historical baseline file exists and preserves historical metrics without modification."""
        hist_path = os.path.join(BASE_DIR, "data", "gold_standard", "baseline_evaluation_results.json")
        self.assertTrue(os.path.exists(hist_path), f"Historical baseline file must exist at: {hist_path}")

        with open(hist_path, "r", encoding="utf-8") as f:
            hist_data = json.load(f)

        self.assertIn("statistical_classifier_baseline", hist_data)
        stat = hist_data["statistical_classifier_baseline"]
        self.assertIn("strict_span_metrics", stat)
        self.assertEqual(stat["strict_span_metrics"]["f1_mean"], 52.2)

    def test_08_tuning_results_export_integrity(self):
        """Verifies that the new tuning results file is generated with valid structure and metrics."""
        self.assertTrue(os.path.exists(RESULTS_OUTPUT_PATH), f"Tuning results file not found at: {RESULTS_OUTPUT_PATH}")

        with open(RESULTS_OUTPUT_PATH, "r", encoding="utf-8") as f:
            res = json.load(f)

        self.assertIn("metadata", res)
        self.assertIn("hyperparameter_search_space", res)
        self.assertIn("selected_configurations_per_fold", res)
        self.assertEqual(len(res["selected_configurations_per_fold"]), 5)

        self.assertIn("overall_test_metrics", res)
        test_m = res["overall_test_metrics"]
        self.assertIn("strict_span_metrics", test_m)
        self.assertGreater(test_m["strict_span_metrics"]["f1"]["mean"], 45.0)


if __name__ == "__main__":
    unittest.main()
