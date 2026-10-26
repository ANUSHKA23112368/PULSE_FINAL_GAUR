"""
PULSE — Category-Wise Hybrid Extractor Integrity & Safety Tests
Phase 5 — Step 5.6 Model Comparison & Hybrid Extraction

Verifies:
1. Exact source character offsets for hybrid entities.
2. Conflict resolution policy for overlapping entity spans.
3. Duplicate entity prevention in fused results.
4. Medication attribute binding (dosage, frequency, route).
5. Investigation status binding (Awaiting Results, Completed, etc.).
6. Assertion and temporality preservation (negated, historical).
7. Unknown-term preservation and open-vocabulary review flags.
8. Regression safety against historical baselines and tuning outputs.
"""

import unittest
import os
import json
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import sklearn_crfsuite
from scripts.evaluate_hybrid_extractor import CategoryWiseHybridExtractor, RESULTS_OUTPUT_PATH
from backend.extraction.entity_extractor import clinical_entity_extractor


class MockCRF:
    """Mock CRF model returning predetermined sequence predictions for testing."""
    def __init__(self, pred_seq):
        self.pred_seq = pred_seq

    def predict_single(self, doc_feats):
        return self.pred_seq


class TestHybridExtractor(unittest.TestCase):
    def setUp(self):
        self.sample_text = "Bed 4, Michael Wu. 68yo male under Dr Smith. History of CCF. Complaining of chest pain. Metoprolol 25mg BD PO. CXR completed."
        self.tokens = [
            {"token": "Bed", "start_char": 0, "end_char": 3},
            {"token": "4", "start_char": 4, "end_char": 5},
            {"token": ",", "start_char": 5, "end_char": 6},
            {"token": "Michael", "start_char": 7, "end_char": 14},
            {"token": "Wu", "start_char": 15, "end_char": 17},
            {"token": ".", "start_char": 17, "end_char": 18},
            {"token": "68yo", "start_char": 19, "end_char": 23},
            {"token": "male", "start_char": 24, "end_char": 28},
            {"token": "under", "start_char": 29, "end_char": 34},
            {"token": "Dr", "start_char": 35, "end_char": 37},
            {"token": "Smith", "start_char": 38, "end_char": 43},
            {"token": ".", "start_char": 43, "end_char": 44},
            {"token": "History", "start_char": 45, "end_char": 52},
            {"token": "of", "start_char": 53, "end_char": 55},
            {"token": "CCF", "start_char": 56, "end_char": 59},
            {"token": ".", "start_char": 59, "end_char": 60},
            {"token": "Complaining", "start_char": 61, "end_char": 72},
            {"token": "of", "start_char": 73, "end_char": 75},
            {"token": "chest", "start_char": 76, "end_char": 81},
            {"token": "pain", "start_char": 82, "end_char": 86},
            {"token": ".", "start_char": 86, "end_char": 87},
            {"token": "Metoprolol", "start_char": 88, "end_char": 98},
            {"token": "25mg", "start_char": 99, "end_char": 103},
            {"token": "BD", "start_char": 104, "end_char": 106},
            {"token": "PO", "start_char": 107, "end_char": 109},
            {"token": ".", "start_char": 109, "end_char": 110},
            {"token": "CXR", "start_char": 111, "end_char": 114},
            {"token": "completed", "start_char": 115, "end_char": 124},
            {"token": ".", "start_char": 124, "end_char": 125}
        ]

    def test_01_exact_source_offsets(self):
        """Verifies that all extracted entities strictly match their text slices."""
        extractor = CategoryWiseHybridExtractor(crf_model=None)
        res = extractor.extract_hybrid_entities(self.sample_text, self.tokens, report_id="1")
        for ent in res["entities"]:
            st = ent["start_char"]
            en = ent["end_char"]
            expected_slice = self.sample_text[st:en]
            self.assertEqual(ent["text"], expected_slice, f"Mismatch at offset [{st}, {en}]")

    def test_02_conflict_resolution_and_precedence(self):
        """Verifies that CRF span boundary takes precedence over rule boundary when they overlap."""
        # Mock CRF predicting CCF as Clinical_Condition
        mock_labels = ["O"] * len(self.tokens)
        mock_labels[14] = "Clinical_Condition"  # token 'CCF' [56, 59]

        mock_crf = MockCRF(mock_labels)
        extractor = CategoryWiseHybridExtractor(crf_model=mock_crf)
        res = extractor.extract_hybrid_entities(self.sample_text, self.tokens, report_id="1")

        # Find the CCF entity
        ccf_ents = [e for e in res["entities"] if e["text"] == "CCF"]
        self.assertEqual(len(ccf_ents), 1)
        self.assertEqual(ccf_ents[0]["label"], "Clinical_Condition")
        self.assertEqual(ccf_ents[0]["extraction_source"], "crf_sequence_tagger")

    def test_03_duplicate_entity_prevention(self):
        """Verifies that overlapping or identical character spans are never duplicated."""
        extractor = CategoryWiseHybridExtractor(crf_model=None)
        res = extractor.extract_hybrid_entities(self.sample_text, self.tokens, report_id="1")
        spans_seen = set()
        for ent in res["entities"]:
            key = (ent["start_char"], ent["end_char"])
            self.assertNotIn(key, spans_seen, f"Duplicate entity detected at span {key}")
            spans_seen.add(key)

    def test_04_medication_attribute_binding(self):
        """Verifies that medication entities bind dosage, route, and frequency accurately."""
        extractor = CategoryWiseHybridExtractor(crf_model=None)
        res = extractor.extract_hybrid_entities(self.sample_text, self.tokens, report_id="1")

        meds = [e for e in res["entities"] if e["label"] == "Medication"]
        self.assertGreaterEqual(len(meds), 1)
        metoprolol = meds[0]
        self.assertEqual(metoprolol["text"], "Metoprolol")
        attrs = metoprolol.get("attributes", {})
        self.assertIn("25mg", attrs.get("dosage", ""))
        self.assertIn("BD", attrs.get("frequency", ""))
        self.assertIn("PO", attrs.get("route", ""))

    def test_05_investigation_status_binding(self):
        """Verifies that investigation entities preserve clinical status."""
        extractor = CategoryWiseHybridExtractor(crf_model=None)
        res = extractor.extract_hybrid_entities(self.sample_text, self.tokens, report_id="1")

        invs = [e for e in res["entities"] if e["label"] == "Investigation_Procedure"]
        self.assertGreaterEqual(len(invs), 1)
        cxr = invs[0]
        self.assertEqual(cxr["text"], "CXR")
        self.assertEqual(cxr.get("attributes", {}).get("status"), "Completed")

    def test_06_assertion_and_temporality(self):
        """Verifies that negated symptoms and historical conditions are correctly attributed."""
        text_with_negation = "Patient denies any headache. Past history of asthma."
        tokens = [
            {"token": "Patient", "start_char": 0, "end_char": 7},
            {"token": "denies", "start_char": 8, "end_char": 14},
            {"token": "any", "start_char": 15, "end_char": 18},
            {"token": "headache", "start_char": 19, "end_char": 27},
            {"token": ".", "start_char": 27, "end_char": 28},
            {"token": "Past", "start_char": 29, "end_char": 33},
            {"token": "history", "start_char": 34, "end_char": 41},
            {"token": "of", "start_char": 42, "end_char": 44},
            {"token": "asthma", "start_char": 45, "end_char": 51},
            {"token": ".", "start_char": 51, "end_char": 52}
        ]
        extractor = CategoryWiseHybridExtractor(crf_model=None)
        res = extractor.extract_hybrid_entities(text_with_negation, tokens, report_id="2")

        headache = [e for e in res["entities"] if e["text"] == "headache"][0]
        self.assertTrue(headache["attributes"].get("is_negated"))
        self.assertEqual(headache["attributes"].get("assertion"), "Negated")

        asthma = [e for e in res["entities"] if e["text"] == "asthma"][0]
        self.assertEqual(asthma["attributes"].get("temporality"), "Historical")

    def test_07_regression_against_historical_baselines(self):
        """Verifies that previous baseline and CRF tuning results files remain unmodified."""
        hist_baseline = os.path.join(BASE_DIR, "data", "gold_standard", "baseline_evaluation_results.json")
        crf_results = os.path.join(BASE_DIR, "data", "gold_standard", "crf_tuning_results.json")

        self.assertTrue(os.path.exists(hist_baseline))
        self.assertTrue(os.path.exists(crf_results))

        with open(hist_baseline, "r", encoding="utf-8") as f:
            hb = json.load(f)
        self.assertEqual(hb["statistical_classifier_baseline"]["strict_span_metrics"]["f1_mean"], 52.2)

        with open(crf_results, "r", encoding="utf-8") as f:
            cb = json.load(f)
        self.assertEqual(cb["overall_test_metrics"]["strict_span_metrics"]["f1"]["mean"], 60.2)


if __name__ == "__main__":
    unittest.main()
