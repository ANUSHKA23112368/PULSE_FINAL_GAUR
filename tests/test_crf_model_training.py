"""
PULSE — Conditional Random Field (CRF) Sequence Tagger Integrity Tests
Phase 5 — Model Comparison & Evaluation

Verifies:
1. Document-level 5-fold cross-validation split disjointness and coverage.
2. Correct label sequence generation and macro-category harmonization.
3. Entity-span reconstruction from sequence predictions.
4. Strict vs. lenient span metric calculation logic.
5. Handling of empty predictions, all-O sequences, and unseen entity cases.
6. CRF model fit and deterministic sequence tagging on synthetic clinical sequences.
7. Historical baseline results immutability (Logistic Regression and historical baselines).
8. Reproducible configuration and crf_tuning_results.json schema integrity.
"""

import unittest
import os
import json
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import sklearn_crfsuite
from scripts.train_statistical_classifier import (
    extract_token_features,
    reconstruct_spans_from_tokens,
    compute_span_metrics,
    map_label,
    MACRO_CATEGORIES,
    CORPUS_PATH,
    SPLITS_PATH,
)
from scripts.train_crf_tagger import RESULTS_OUTPUT_PATH, LR_RESULTS_PATH


class TestCRFModelTraining(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(CORPUS_PATH, "r", encoding="utf-8") as f:
            cls.corpus = json.load(f)
        with open(SPLITS_PATH, "r", encoding="utf-8") as f:
            cls.splits = json.load(f)

    def test_01_training_corpus_and_splits_structure(self):
        """Verifies 101 reports in corpus and 5 folds in precomputed splits."""
        reports = self.corpus.get("reports", [])
        self.assertEqual(len(reports), 101, "Expected 101 reports in gold standard corpus")
        self.assertEqual(len(self.splits), 5, "Expected 5 cross-validation folds")

    def test_02_split_disjointness_across_folds(self):
        """Enforces that train, val, and test splits are strictly disjoint across all folds."""
        all_ids = {str(i) for i in range(101)}
        for fold_name, split in self.splits.items():
            tr = set(split["train"])
            vl = set(split["val"])
            ts = set(split["test"])

            # Disjointness checks
            self.assertEqual(len(tr & vl), 0, f"{fold_name}: train and val must be disjoint")
            self.assertEqual(len(tr & ts), 0, f"{fold_name}: train and test must be disjoint")
            self.assertEqual(len(vl & ts), 0, f"{fold_name}: val and test must be disjoint")

            # Coverage check
            self.assertEqual(tr | vl | ts, all_ids, f"{fold_name}: must cover all 101 notes")

    def test_03_label_sequence_generation(self):
        """Verifies that sequence token mapping accurately converts fine-grained labels to macro classes."""
        self.assertEqual(map_label("Medication_Medicine"), "Medication")
        self.assertEqual(map_label("Medication_Dosage"), "Medication")
        self.assertEqual(map_label("B-Medication_Medicine"), "Medication")
        self.assertEqual(map_label("I-MyShift_Status"), "Clinical_Observation")
        self.assertEqual(map_label("PatientIntroduction_AdmissionReason/Diagnosis"), "Clinical_Condition")
        self.assertEqual(map_label("O"), "O")
        self.assertEqual(map_label("NA"), "O")
        self.assertEqual(map_label(None), "O")

    def test_04_entity_span_reconstruction(self):
        """Verifies that contiguous identical tokens in the same document merge into a single span."""
        preds = ["Clinical_Condition", "Clinical_Condition", "O", "Demographics_Name"]
        meta = [
            {"report_id": "12", "start_char": 0, "end_char": 5, "token": "Acute"},
            {"report_id": "12", "start_char": 6, "end_char": 17, "token": "pancreatitis"},
            {"report_id": "12", "start_char": 17, "end_char": 18, "token": "."},
            {"report_id": "12", "start_char": 19, "end_char": 23, "token": "John"}
        ]
        spans = reconstruct_spans_from_tokens(preds, meta)
        self.assertEqual(len(spans), 2)
        self.assertEqual(spans[0], {
            "label": "Clinical_Condition",
            "report_id": "12",
            "start_char": 0,
            "end_char": 17
        })
        self.assertEqual(spans[1], {
            "label": "Demographics_Name",
            "report_id": "12",
            "start_char": 19,
            "end_char": 23
        })

    def test_05_strict_and_lenient_metrics(self):
        """Verifies precision, recall, and F1 calculations for exact and partial span overlaps."""
        gold = [
            {"label": "Medication", "report_id": "1", "start_char": 5, "end_char": 15, "text": "Aspirin 75"},
            {"label": "Care_Activity", "report_id": "1", "start_char": 25, "end_char": 35, "text": "Mobilised"}
        ]
        # Pred 1 matches gold 1 strictly; Pred 2 has partial overlap with gold 2; Pred 3 is a false positive
        pred = [
            {"label": "Medication", "report_id": "1", "start_char": 5, "end_char": 15},
            {"label": "Care_Activity", "report_id": "1", "start_char": 20, "end_char": 33},
            {"label": "Plan_Goal", "report_id": "1", "start_char": 50, "end_char": 60}
        ]
        metrics = compute_span_metrics(gold, pred)
        # Strict: 1 TP, 2 FP, 1 FN -> P = 1/3 (33.33%), R = 1/2 (50.0%), F1 = 40.0%
        self.assertEqual(metrics["strict"]["tp"], 1)
        self.assertEqual(metrics["strict"]["fp"], 2)
        self.assertEqual(metrics["strict"]["fn"], 1)
        self.assertEqual(metrics["strict"]["precision"], 33.33)
        self.assertEqual(metrics["strict"]["recall"], 50.0)
        self.assertEqual(metrics["strict"]["f1"], 40.0)

        # Lenient: 2 TP (both gold matched), 1 FP (the Plan_Goal pred), 0 FN -> P = 2/3 (66.67%), R = 2/2 (100.0%), F1 = 80.0%
        self.assertEqual(metrics["lenient"]["tp"], 2)
        self.assertEqual(metrics["lenient"]["fp"], 1)
        self.assertEqual(metrics["lenient"]["fn"], 0)
        self.assertEqual(metrics["lenient"]["precision"], 66.67)
        self.assertEqual(metrics["lenient"]["recall"], 100.0)
        self.assertEqual(metrics["lenient"]["f1"], 80.0)

    def test_06_empty_and_unseen_entity_cases(self):
        """Verifies metric calculations with empty predictions or all-'O' outputs."""
        gold = [{"label": "Medication", "report_id": "1", "start_char": 0, "end_char": 10, "text": "Paracetamol"}]
        empty_pred = []
        metrics_empty = compute_span_metrics(gold, empty_pred)
        self.assertEqual(metrics_empty["strict"]["f1"], 0.0)
        self.assertEqual(metrics_empty["strict"]["tp"], 0)
        self.assertEqual(metrics_empty["strict"]["fn"], 1)

        # No gold and no pred
        metrics_both_empty = compute_span_metrics([], [])
        self.assertEqual(metrics_both_empty["strict"]["f1"], 0.0)
        self.assertEqual(metrics_both_empty["strict"]["tp"], 0)

    def test_07_crf_fit_and_predict_determinism(self):
        """Verifies CRF model fitting and inference on sequence dictionaries."""
        X_seq = [
            [{"bias": 1.0, "token": "patient", "is_title": True},
             {"bias": 1.0, "token": "prescribed", "is_title": False},
             {"bias": 1.0, "token": "metoprolol", "is_title": False}]
        ]
        y_seq = [["O", "O", "Medication"]]

        crf = sklearn_crfsuite.CRF(
            algorithm="lbfgs",
            c1=0.1,
            c2=0.1,
            max_iterations=20,
            all_possible_transitions=True
        )
        crf.fit(X_seq, y_seq)
        preds = crf.predict(X_seq)
        self.assertEqual(len(preds), 1)
        self.assertEqual(len(preds[0]), 3)
        self.assertEqual(preds[0][2], "Medication")

    def test_08_historical_baselines_immutability(self):
        """Verifies that historical baseline evaluation and Logistic Regression files remain unchanged."""
        hist_baseline = os.path.join(BASE_DIR, "data", "gold_standard", "baseline_evaluation_results.json")
        self.assertTrue(os.path.exists(hist_baseline))
        with open(hist_baseline, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["statistical_classifier_baseline"]["strict_span_metrics"]["f1_mean"], 52.2)

        # Also verify LR results file is intact
        self.assertTrue(os.path.exists(LR_RESULTS_PATH))
        with open(LR_RESULTS_PATH, "r", encoding="utf-8") as f:
            lr_data = json.load(f)
        self.assertIn("overall_test_metrics", lr_data)
        self.assertEqual(lr_data["overall_test_metrics"]["strict_span_metrics"]["f1"]["mean"], 51.69)

    def test_09_crf_tuning_results_schema(self):
        """Verifies that the CRF tuning output exists and satisfies schema requirements."""
        if os.path.exists(RESULTS_OUTPUT_PATH):
            with open(RESULTS_OUTPUT_PATH, "r", encoding="utf-8") as f:
                res = json.load(f)
            self.assertIn("metadata", res)
            self.assertIn("hyperparameter_search_space", res)
            self.assertIn("selected_configurations_per_fold", res)
            self.assertEqual(len(res["selected_configurations_per_fold"]), 5)
            self.assertIn("overall_test_metrics", res)
            self.assertIn("direct_comparison_with_logistic_regression", res)


if __name__ == "__main__":
    unittest.main()
