"""Hospital training corpus construction and span alignment tests."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.dataset.hospital_training_corpus import (
    build_hospital_training_corpus,
    load_fold_ids,
    load_hospital_training_documents,
)
from backend.extraction.label_schema import MACRO_CATEGORIES, map_raw_label
from backend.extraction.realtime_pipeline import run_realtime_analysis


class TestHospitalTrainingCorpus(unittest.TestCase):
    def test_gold_plus_synthetic_counts(self):
        corpus = build_hospital_training_corpus(n_synthetic=20, seed=1)
        self.assertEqual(corpus["metadata"]["gold_documents"], 101)
        self.assertEqual(corpus["metadata"]["synthetic_hospital_documents"], 20)
        self.assertEqual(len(corpus["documents"]), 121)

    def test_synthetic_spans_align_to_text(self):
        docs = load_hospital_training_documents(include_synthetic=True, n_synthetic=12, seed=7)
        synth = [d for d in docs if d["source"] == "synthetic_hospital_isbar"]
        self.assertGreaterEqual(len(synth), 12)
        for doc in synth:
            self.assertTrue(doc["raw_text"])
            self.assertGreaterEqual(len(doc["entity_spans"]), 8)
            for span in doc["entity_spans"]:
                self.assertIn(span["category"], MACRO_CATEGORIES)
                slice_text = doc["raw_text"][span["start_char"]:span["end_char"]]
                self.assertEqual(slice_text, span["text"])
                self.assertGreater(span["end_char"], span["start_char"])

    def test_gold_spans_use_macro_categories(self):
        gold = load_hospital_training_documents(include_synthetic=False)
        self.assertEqual(len(gold), 101)
        sample = next(d for d in gold if d["report_id"] == "0")
        categories = {sp["category"] for sp in sample["entity_spans"]}
        self.assertTrue(categories.issubset(set(MACRO_CATEGORIES)))
        self.assertIn("Clinical_Condition", categories)

    def test_fold_zero_test_ids_are_gold_only(self):
        splits = load_fold_ids("fold_0")
        self.assertGreaterEqual(len(splits["test"]), 15)
        gold_ids = {d["report_id"] for d in load_hospital_training_documents(include_synthetic=False)}
        self.assertTrue(set(splits["test"]).issubset(gold_ids))

    def test_label_map_covers_nursing_handover_columns(self):
        self.assertEqual(map_raw_label("PatientIntroduction_AdmissionReason/Diagnosis"), "Clinical_Condition")
        self.assertEqual(map_raw_label("Medication_Medicine"), "Medication")
        self.assertEqual(map_raw_label("B-Appointment/Procedure_Description"), "Investigation_Procedure")


class TestRealtimePipeline(unittest.TestCase):
    def test_rule_engine_pipeline_returns_timings(self):
        text = (
            "Bed 12 Rahul Sharma 55 yo male under Dr Hanlen. Admitted with pneumonia. "
            "Nil chest pain. On IV Augmentin 1.2 g TDS. For chest X-ray this morning."
        )
        result = run_realtime_analysis(text, engine="rule")
        self.assertIn("structured_handover", result)
        self.assertIn("isbar", result)
        timings = result["model_metadata"]["pipeline_timings_ms"]
        self.assertIn("total_ms", timings)
        self.assertGreater(timings["total_ms"], 0)
        self.assertEqual(result["model_metadata"]["selected_engine"], "rule")
        self.assertIn("Deterministic Rule", result["model_metadata"]["pipeline"])

    def test_hybrid_falls_back_when_weights_missing(self):
        result = run_realtime_analysis(
            "Bed 4 Jane Doe 74yo admitted with COPD exacerbation. Started on IV Lasix 40mg bd.",
            engine="hybrid",
        )
        self.assertTrue(result["entities"]["medications"] or result["entities"]["conditions"])
        self.assertIn("pipeline_timings_ms", result["model_metadata"])


if __name__ == "__main__":
    unittest.main()
