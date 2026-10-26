"""
PULSE — Phase 5, Step 4.1: Benchmark Validation Audit Tests
Comprehensive unit tests covering:
1. Strict and lenient span evaluation edge cases (Task B):
   - Exact span and category match
   - Correct span but wrong category
   - Partial overlap
   - Prediction completely outside gold span
   - Duplicate predictions
   - Multiple predictions overlapping one gold entity
   - Empty prediction set
   - Empty reference set
   - Both sets empty
   - Incorrect or out-of-range offsets
2. Clinical source-grounding and hallucination audit cases (Task C):
   - Hinglish normalization: "chakkar" -> "Dizziness"
   - Shorthand normalization: "T2DM" -> "Type 2 Diabetes Mellitus"
   - Unsupported clinical entity
   - Unsupported medication dosage
   - Incorrect medication-frequency binding
   - Incorrect investigation status
   - Negated symptom incorrectly emitted as positive finding
   - Pending investigation incorrectly represented as completed
   - Valid normalized entity with source evidence span
   - Ambiguous clinical evidence flagged as unresolved
"""

import unittest
import os
import json
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.benchmark_runner import (
    compute_span_eval,
    audit_entity_grounding,
    GroundingCategory,
    GENERALIZATION_CHALLENGE_CASES,
    BENCHMARK_OUTPUT_PATH,
    AUDIT_OUTPUT_PATH
)


class TestBenchmarkValidationAudit(unittest.TestCase):
    """
    Unit tests validating metric correctness, edge cases, and source grounding.
    """

    # ==========================================================================
    # Task B: Strict and Lenient Matching Edge Cases
    # ==========================================================================

    def test_b01_exact_span_and_category_match(self):
        """1. Exact span and category match: strict and lenient both 100%"""
        gold = [{"label": "Medication", "start_char": 10, "end_char": 17, "text": "Digoxin"}]
        pred = [{"label": "Medication", "start_char": 10, "end_char": 17, "text": "Digoxin"}]
        res = compute_span_eval(gold, pred)
        self.assertEqual(res["strict"]["tp"], 1)
        self.assertEqual(res["strict"]["fp"], 0)
        self.assertEqual(res["strict"]["fn"], 0)
        self.assertEqual(res["strict"]["f1"], 100.0)
        self.assertEqual(res["lenient"]["f1"], 100.0)

    def test_b02_correct_span_wrong_category(self):
        """2. Correct span but wrong category: 0 TP in both strict and lenient"""
        gold = [{"label": "Clinical_Condition", "start_char": 5, "end_char": 17, "text": "hypertension"}]
        pred = [{"label": "Clinical_Observation", "start_char": 5, "end_char": 17, "text": "hypertension"}]
        res = compute_span_eval(gold, pred)
        self.assertEqual(res["strict"]["tp"], 0)
        self.assertEqual(res["strict"]["fp"], 1)
        self.assertEqual(res["strict"]["fn"], 1)
        self.assertEqual(res["strict"]["f1"], 0.0)
        self.assertEqual(res["lenient"]["tp"], 0)
        self.assertEqual(res["lenient"]["f1"], 0.0)

    def test_b03_partial_overlap_same_category(self):
        """3. Partial overlap with same category: strict TP=0, lenient TP=1"""
        gold = [{"label": "Clinical_Condition", "start_char": 10, "end_char": 25, "text": "type 2 diabetes"}]
        pred = [{"label": "Clinical_Condition", "start_char": 17, "end_char": 25, "text": "diabetes"}]
        res = compute_span_eval(gold, pred)
        self.assertEqual(res["strict"]["tp"], 0)
        self.assertEqual(res["strict"]["fp"], 1)
        self.assertEqual(res["strict"]["fn"], 1)
        self.assertEqual(res["strict"]["f1"], 0.0)
        self.assertEqual(res["lenient"]["tp"], 1)
        self.assertEqual(res["lenient"]["fp"], 0)
        self.assertEqual(res["lenient"]["fn"], 0)
        self.assertEqual(res["lenient"]["f1"], 100.0)

    def test_b04_prediction_completely_outside_gold_span(self):
        """4. Prediction completely outside gold span: strict TP=0, lenient TP=0"""
        gold = [{"label": "Medication", "start_char": 0, "end_char": 10, "text": "Furosemide"}]
        pred = [{"label": "Medication", "start_char": 20, "end_char": 30, "text": "Metoprolol"}]
        res = compute_span_eval(gold, pred)
        self.assertEqual(res["strict"]["tp"], 0)
        self.assertEqual(res["strict"]["fp"], 1)
        self.assertEqual(res["strict"]["fn"], 1)
        self.assertEqual(res["strict"]["f1"], 0.0)
        self.assertEqual(res["lenient"]["tp"], 0)
        self.assertEqual(res["lenient"]["f1"], 0.0)

    def test_b05_duplicate_predictions_for_single_gold(self):
        """5. Duplicate predictions: cannot inflate TP; second prediction is counted as FP"""
        gold = [{"label": "Medication", "start_char": 0, "end_char": 7, "text": "Digoxin"}]
        pred = [
            {"label": "Medication", "start_char": 0, "end_char": 7, "text": "Digoxin"},
            {"label": "Medication", "start_char": 0, "end_char": 7, "text": "Digoxin"}
        ]
        res = compute_span_eval(gold, pred)
        self.assertEqual(res["strict"]["tp"], 1)
        self.assertEqual(res["strict"]["fp"], 1)
        self.assertEqual(res["strict"]["fn"], 0)
        self.assertEqual(res["strict"]["precision"], 50.0)
        self.assertEqual(res["strict"]["recall"], 100.0)
        self.assertEqual(res["lenient"]["tp"], 1)
        self.assertEqual(res["lenient"]["fp"], 1)

    def test_b06_multiple_predictions_overlapping_single_gold(self):
        """6. Multiple predictions overlapping one gold: gold matched at most once; extra is FP"""
        gold = [{"label": "Clinical_Observation", "start_char": 0, "end_char": 20, "text": "severe abdominal pain"}]
        pred = [
            {"label": "Clinical_Observation", "start_char": 0, "end_char": 6, "text": "severe"},
            {"label": "Clinical_Observation", "start_char": 7, "end_char": 20, "text": "abdominal pain"}
        ]
        res = compute_span_eval(gold, pred)
        self.assertEqual(res["lenient"]["tp"], 1)
        self.assertEqual(res["lenient"]["fp"], 1)
        self.assertEqual(res["lenient"]["fn"], 0)
        self.assertEqual(res["lenient"]["precision"], 50.0)
        self.assertEqual(res["lenient"]["recall"], 100.0)

    def test_b07_empty_prediction_set(self):
        """7. Empty prediction set: TP=0, FP=0, FN=len(gold), P=0%, R=0%, F1=0%"""
        gold = [{"label": "Medication", "start_char": 0, "end_char": 7, "text": "Digoxin"}]
        pred = []
        res = compute_span_eval(gold, pred)
        self.assertEqual(res["strict"]["tp"], 0)
        self.assertEqual(res["strict"]["fp"], 0)
        self.assertEqual(res["strict"]["fn"], 1)
        self.assertEqual(res["strict"]["f1"], 0.0)

    def test_b08_empty_reference_set(self):
        """8. Empty reference set: TP=0, FP=len(pred), FN=0, P=0%, R=0%, F1=0%"""
        gold = []
        pred = [{"label": "Medication", "start_char": 0, "end_char": 7, "text": "Digoxin"}]
        res = compute_span_eval(gold, pred)
        self.assertEqual(res["strict"]["tp"], 0)
        self.assertEqual(res["strict"]["fp"], 1)
        self.assertEqual(res["strict"]["fn"], 0)
        self.assertEqual(res["strict"]["f1"], 0.0)

    def test_b09_both_sets_empty(self):
        """9. Both sets empty: 100% agreement when no entities are present"""
        gold = []
        pred = []
        res = compute_span_eval(gold, pred, empty_both_value=100.0)
        self.assertEqual(res["strict"]["tp"], 0)
        self.assertEqual(res["strict"]["fp"], 0)
        self.assertEqual(res["strict"]["fn"], 0)
        self.assertEqual(res["strict"]["f1"], 100.0)
        self.assertEqual(res["lenient"]["f1"], 100.0)

    def test_b10_incorrect_or_out_of_range_offsets(self):
        """10. Incorrect or out-of-range offsets: gracefully treated as false positives"""
        gold = [{"label": "Medication", "start_char": 0, "end_char": 7, "text": "Digoxin"}]
        pred = [
            {"label": "Medication", "start_char": -5, "end_char": 2, "text": "Dig"},
            {"label": "Medication", "start_char": 10, "end_char": 5, "text": "ox"},
            {"label": "Medication", "start_char": None, "end_char": 7, "text": "in"}
        ]
        res = compute_span_eval(gold, pred)
        self.assertEqual(res["strict"]["tp"], 0)
        self.assertEqual(res["strict"]["fp"], 3)
        self.assertEqual(res["strict"]["fn"], 1)
        self.assertEqual(res["strict"]["f1"], 0.0)


    # ==========================================================================
    # Task C: Hallucination and Source Grounding Audit Cases
    # ==========================================================================

    def test_c01_hinglish_normalization_grounding(self):
        """1. Hinglish normalization: 'chakkar aa raha hai' -> 'Dizziness' is valid normalization"""
        source = "Patient ko subah se chakkar aa raha hai."
        ent = {
            "entity_type": "Clinical_Observation",
            "source_text": "chakkar aa raha hai",
            "normalized_value": "Dizziness",
            "source_start": 20,
            "source_end": 39
        }
        res = audit_entity_grounding(ent, source)
        self.assertEqual(res["category"], GroundingCategory.VALID_NORMALIZATION)
        self.assertTrue(res["is_grounded"])

    def test_c02_shorthand_normalization_grounding(self):
        """2. Indian shorthand normalization: 'T2DM' -> 'Type 2 Diabetes Mellitus' is valid normalization"""
        source = "Patient is a K/C/O T2DM."
        ent = {
            "entity_type": "Clinical_Condition",
            "source_text": "T2DM",
            "normalized_value": "Type 2 Diabetes Mellitus",
            "source_start": 19,
            "source_end": 23
        }
        res = audit_entity_grounding(ent, source)
        self.assertEqual(res["category"], GroundingCategory.VALID_NORMALIZATION)
        self.assertTrue(res["is_grounded"])

    def test_c03_unsupported_clinical_entity(self):
        """3. Unsupported clinical entity: entity not in source is unsupported assertion"""
        source = "Patient has mild headache and fever."
        ent = {
            "entity_type": "Clinical_Condition",
            "source_text": "Intracranial Hemorrhage",
            "normalized_value": "Intracranial Hemorrhage",
            "source_start": 50,
            "source_end": 73
        }
        res = audit_entity_grounding(ent, source)
        self.assertEqual(res["category"], GroundingCategory.UNSUPPORTED_ASSERTION)
        self.assertFalse(res["is_grounded"])

    def test_c04_unsupported_medication_dosage(self):
        """4. Unsupported medication dosage: invented dosage not supported by text"""
        source = "Administer Metoprolol 12.5 mg BD."
        gold = [{"label": "Medication", "text": "Metoprolol", "dose": "12.5 mg"}]
        ent = {
            "entity_type": "Medication",
            "source_text": "Metoprolol",
            "source_start": 11,
            "source_end": 21,
            "dosage": "100 mg"
        }
        res = audit_entity_grounding(ent, source, gold_entities=gold)
        self.assertEqual(res["category"], GroundingCategory.UNSUPPORTED_ATTRIBUTE)
        self.assertFalse(res["is_grounded"])

    def test_c05_incorrect_medication_frequency_binding(self):
        """5. Incorrect medication frequency: misbinding frequency attribute"""
        source = "Prescribed Paracetamol 1g PRN and Ceftriaxone 1g BD."
        gold = [{"label": "Medication", "text": "Paracetamol", "freq": "PRN"}]
        ent = {
            "entity_type": "Medication",
            "source_text": "Paracetamol",
            "source_start": 11,
            "source_end": 22,
            "frequency": "BD"
        }
        res = audit_entity_grounding(ent, source, gold_entities=gold)
        self.assertEqual(res["category"], GroundingCategory.UNSUPPORTED_ATTRIBUTE)
        self.assertFalse(res["is_grounded"])

    def test_c06_incorrect_investigation_status(self):
        """6. Incorrect investigation status: investigation pending emitted as completed"""
        source = "CT head is pending."
        gold = [{"label": "Investigation_Procedure", "text": "CT head", "status": "Pending"}]
        ent = {
            "entity_type": "Investigation_Procedure",
            "source_text": "CT head",
            "source_start": 0,
            "source_end": 7,
            "status": "Completed"
        }
        res = audit_entity_grounding(ent, source, gold_entities=gold)
        self.assertEqual(res["category"], GroundingCategory.UNSUPPORTED_ATTRIBUTE)
        self.assertFalse(res["is_grounded"])

    def test_c07_negated_symptom_emitted_as_positive(self):
        """7. Negated symptom emitted as positive: clinical negation failure is unsupported assertion"""
        source = "Patient denies chest pain."
        gold = [{"label": "Clinical_Observation", "text": "chest pain", "assertion": "Negated"}]
        ent = {
            "entity_type": "Clinical_Observation",
            "source_text": "chest pain",
            "source_start": 15,
            "source_end": 25,
            "assertion": "Positive",
            "is_negated": False
        }
        res = audit_entity_grounding(ent, source, gold_entities=gold)
        self.assertEqual(res["category"], GroundingCategory.UNSUPPORTED_ASSERTION)
        self.assertFalse(res["is_grounded"])

    def test_c08_pending_investigation_represented_as_completed(self):
        """8. Pending investigation represented as completed is unsupported attribute"""
        source = "Echocardiogram is awaited."
        gold = [{"label": "Investigation_Procedure", "text": "Echocardiogram", "status": "Pending"}]
        ent = {
            "entity_type": "Investigation_Procedure",
            "source_text": "Echocardiogram",
            "source_start": 0,
            "source_end": 14,
            "status": "Completed"
        }
        res = audit_entity_grounding(ent, source, gold_entities=gold)
        self.assertEqual(res["category"], GroundingCategory.UNSUPPORTED_ATTRIBUTE)
        self.assertFalse(res["is_grounded"])

    def test_c09_valid_normalized_entity_with_source_evidence_span(self):
        """9. Valid normalized entity with source evidence span is valid normalization"""
        source = "Patient ko tez bukhar hai."
        ent = {
            "entity_type": "Clinical_Observation",
            "source_text": "tez bukhar",
            "normalized_value": "High Fever",
            "source_start": 11,
            "source_end": 21
        }
        res = audit_entity_grounding(ent, source)
        self.assertEqual(res["category"], GroundingCategory.VALID_NORMALIZATION)
        self.assertTrue(res["is_grounded"])

    def test_c10_ambiguous_source_evidence(self):
        """10. Ambiguous clinical evidence without sufficient context is unresolved"""
        source = "Unknown acronym XYZ documented."
        ent = {
            "entity_type": "Unclassified",
            "source_text": "XYZ",
            "source_start": 16,
            "source_end": 19,
            "review_status": "flagged_for_review"
        }
        res = audit_entity_grounding(ent, source)
        self.assertEqual(res["category"], GroundingCategory.UNRESOLVED)

    # ==========================================================================
    # Task D: Challenge Benchmark Offsets and Categories Integrity
    # ==========================================================================

    def test_d01_challenge_benchmark_offsets_fidelity(self):
        """Verifies that all 43 entities across 10 challenge cases have exact verified character offsets"""
        total_ents = 0
        for case in GENERALIZATION_CHALLENGE_CASES:
            text = case["text"]
            for e in case["gold_entities"]:
                total_ents += 1
                self.assertIn("start_char", e, f"Missing start_char in entity: {e}")
                self.assertIn("end_char", e, f"Missing end_char in entity: {e}")
                s = e["start_char"]
                idx = e["end_char"]
                self.assertLess(s, idx)
                self.assertEqual(text[s:idx], e["text"], f"Offset mismatch in {case['id']}: '{text[s:idx]}' != '{e['text']}'")
        self.assertEqual(total_ents, 43, f"Expected 43 entities, found {total_ents}")


if __name__ == "__main__":
    unittest.main()
