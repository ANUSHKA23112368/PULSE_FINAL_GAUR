"""
PULSE — Independent Benchmark Annotation Validation Tests
Unit tests validating:
1. Annotation schema validation and verbatim source-text offset integrity.
2. Macro-category, assertion, temporality, and investigation status enum checks.
3. Directed relationship endpoint referential integrity and medication edge constraints.
4. Duplicate span and duplicate relationship detection.
5. Three-way split document and patient-episode disjointness.
6. Conditional directive structure (trigger vs action separation).
7. Benchmark lifecycle stage progression and blocking governance gates.
"""

import copy
import json
import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from backend.dataset.benchmark_validator import (
    BenchmarkAnnotationValidator,
    BenchmarkLifecycleEvaluator,
    APPROVED_MACRO_CATEGORIES,
    APPROVED_ASSERTIONS,
    APPROVED_TEMPORALITIES,
    APPROVED_INVESTIGATION_STATUSES,
)

EXAMPLE_ANNO_PATH = os.path.join(
    BASE_DIR, "data", "gold_standard", "benchmark_annotation_example.json"
)
MANIFEST_TEMPLATE_PATH = os.path.join(
    BASE_DIR, "data", "gold_standard", "benchmark_manifest_template.json"
)


class TestBenchmarkAnnotationValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        self_cls = cls
        with open(EXAMPLE_ANNO_PATH, "r", encoding="utf-8") as f:
            self_cls.example_data = json.load(f)
        with open(MANIFEST_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            self_cls.manifest_data = json.load(f)
        self_cls.validator = BenchmarkAnnotationValidator()

    def setUp(self):
        # Deepcopy example document for isolated mutation testing
        self.doc = copy.deepcopy(self.example_data["documents"][0])

    def test_01_valid_example_passes_validation(self):
        """Verifies that the reference synthetic example document passes validation cleanly"""
        result = self.validator.validate_document(self.doc)
        self.assertTrue(result.is_valid, f"Validation errors: {result.errors}")
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(result.stats["entities_checked"], 17)
        self.assertEqual(result.stats["relationships_checked"], 6)
        self.assertEqual(result.stats["conditional_directives_checked"], 1)

    def test_02_source_offset_mismatch_detected(self):
        """Verifies detection when source_text does not match raw_text slice"""
        # Mutate entity 01 to point to wrong offsets
        self.doc["entities"][0]["start_char"] = 10
        self.doc["entities"][0]["end_char"] = 15
        result = self.validator.validate_document(self.doc)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("source_text" in e and "!=" in e for e in result.errors))

    def test_03_out_of_bounds_offsets_detected(self):
        """Verifies detection of negative or out-of-bounds character offsets"""
        # Case A: start < 0
        doc_neg = copy.deepcopy(self.doc)
        doc_neg["entities"][0]["start_char"] = -1
        res_neg = self.validator.validate_document(doc_neg)
        self.assertFalse(res_neg.is_valid)
        self.assertTrue(any("start_char must be an integer >= 0" in e for e in res_neg.errors))

        # Case B: end > len(raw_text)
        doc_oob = copy.deepcopy(self.doc)
        doc_oob["entities"][0]["end_char"] = 99999
        res_oob = self.validator.validate_document(doc_oob)
        self.assertFalse(res_oob.is_valid)
        self.assertTrue(any("out of bounds" in e for e in res_oob.errors))

        # Case C: start >= end
        doc_inv = copy.deepcopy(self.doc)
        doc_inv["entities"][0]["start_char"] = 10
        doc_inv["entities"][0]["end_char"] = 5
        res_inv = self.validator.validate_document(doc_inv)
        self.assertFalse(res_inv.is_valid)

    def test_04_whitespace_trimming_discipline_enforced(self):
        """Verifies rejection of entity spans with untrimmed leading or trailing whitespace"""
        self.doc["entities"][0]["source_text"] = " Bed 6 "
        self.doc["raw_text"] = " Bed 6 " + self.doc["raw_text"][5:]
        self.doc["entities"][0]["start_char"] = 0
        self.doc["entities"][0]["end_char"] = 7
        result = self.validator.validate_document(self.doc)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("untrimmed leading/trailing whitespace" in e for e in result.errors))

    def test_05_invalid_macro_category_detected(self):
        """Verifies rejection of non-approved clinical macro-categories"""
        self.doc["entities"][0]["macro_category"] = "Invented_Category_XYZ"
        result = self.validator.validate_document(self.doc)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("invalid macro_category" in e for e in result.errors))

    def test_06_assertion_and_temporality_enums_enforced(self):
        """Verifies that invalid assertion or temporality strings are caught"""
        self.doc["entities"][0]["assertion"] = "Highly_Probable"  # Non-standard
        self.doc["entities"][1]["temporality"] = "Recent"          # Non-standard
        result = self.validator.validate_document(self.doc)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("invalid assertion" in e for e in result.errors))
        self.assertTrue(any("invalid temporality" in e for e in result.errors))

    def test_07_investigation_status_enums_enforced(self):
        """Verifies that investigation status is validated against approved enums"""
        # ent_10 is ECG (Investigation_Procedure)
        ent_ecg = next(e for e in self.doc["entities"] if e["entity_id"] == "ent_10")
        ent_ecg["investigation_status"] = "Processing_Sample"  # Non-standard
        result = self.validator.validate_document(self.doc)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("invalid investigation_status" in e for e in result.errors))

    def test_08_relationship_endpoint_referential_integrity(self):
        """Verifies rejection of relationships pointing to non-existent entity IDs"""
        self.doc["relationships"].append({
            "rel_id": "rel_err_01",
            "rel_type": "has_dosage",
            "source_entity_id": "ent_08",
            "target_entity_id": "NON_EXISTENT_ENTITY_999",
        })
        result = self.validator.validate_document(self.doc)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("does not exist in entities" in e for e in result.errors))

    def test_09_medication_attribute_edge_source_constraint(self):
        """Verifies that medication attribute edges (has_dosage, etc.) must originate from a Medication entity"""
        # ent_01 is Demographics_Bed
        self.doc["relationships"].append({
            "rel_id": "rel_err_02",
            "rel_type": "has_dosage",
            "source_entity_id": "ent_01",
            "target_entity_id": "ent_08_dose",
        })
        result = self.validator.validate_document(self.doc)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("expected 'Medication'" in e for e in result.errors))

    def test_10_duplicate_span_and_relationship_detection(self):
        """Verifies detection of duplicate spans or identical relationship edges"""
        # Duplicate entity span
        dup_ent = copy.deepcopy(self.doc["entities"][0])
        dup_ent["entity_id"] = "ent_dup_01"
        self.doc["entities"].append(dup_ent)

        # Duplicate relationship
        dup_rel = copy.deepcopy(self.doc["relationships"][0])
        dup_rel["rel_id"] = "rel_dup_01"
        self.doc["relationships"].append(dup_rel)

        result = self.validator.validate_document(self.doc)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("duplicate entity span" in e for e in result.errors))
        self.assertTrue(any("duplicate relationship" in e for e in result.errors))

    def test_11_conditional_directive_structure(self):
        """Verifies structure of contingent directives (trigger_condition and resulting_action)"""
        # Missing resulting_action
        self.doc["conditional_directives"][0]["resulting_action"] = ""
        result = self.validator.validate_document(self.doc)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("resulting_action" in e for e in result.errors))

    def test_12_dataset_partition_disjointness_enforced(self):
        """Verifies corpus-level detection of partition overlap and patient leakage across splits"""
        doc_dev = copy.deepcopy(self.doc)
        doc_dev["document_id"] = "DOC_DEV_01"
        doc_dev["patient_id"] = "PATIENT_SHARED_01"
        doc_dev["dataset_split"] = "development"

        doc_test = copy.deepcopy(self.doc)
        doc_test["document_id"] = "DOC_TEST_01"
        doc_test["patient_id"] = "PATIENT_SHARED_01"  # Same patient in held-out test -> leakage!
        doc_test["dataset_split"] = "held_out_test"

        corpus = {
            "metadata": {"version": "1.0.0"},
            "documents": [doc_dev, doc_test]
        }
        res = self.validator.validate_corpus(corpus)
        self.assertFalse(res.is_valid)
        self.assertTrue(any("Patient Leakage Violation" in e for e in res.errors))

    def test_13_lifecycle_state_machine_blocks_unauthorized_evaluation(self):
        """Verifies that lifecycle evaluator correctly flags unapproved/uncollected benchmark stages"""
        report = BenchmarkLifecycleEvaluator.evaluate_manifest_readiness(
            self.manifest_data, base_dir=BASE_DIR
        )
        self.assertTrue(report["protocol_created"], "Protocol should be detected as created")
        self.assertFalse(report["data_collected"], "Real data must not be marked collected")
        self.assertFalse(report["annotations_completed"], "Annotations must not be marked complete")
        self.assertFalse(report["annotations_adjudicated"], "Adjudication must not be marked complete")
        self.assertFalse(report["benchmark_ready_for_evaluation"], "Benchmark must NOT be ready for evaluation")
        self.assertEqual(report["governance_status"], "UNRESOLVED")
        self.assertGreaterEqual(len(report["blocking_reasons"]), 3)

    def test_14_cross_medication_attribute_contamination_detected(self):
        """Verifies that binding the same attribute span to two distinct medications without is_shared_attribute is caught"""
        # ent_08 is Aspirin, ent_09 is Sorbitrate. Both binding to ent_08_dose
        self.doc["relationships"].append({
            "rel_id": "rel_leak_01",
            "rel_type": "has_dosage",
            "source_entity_id": "ent_09",
            "target_entity_id": "ent_08_dose",  # Belonging to Aspirin!
            "is_shared_attribute": False
        })
        result = self.validator.validate_document(self.doc)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("cross-medication attribute contamination" in e for e in result.errors))

    def test_15_same_category_partial_overlap_detected(self):
        """Verifies that partial character overlaps within the same category are detected and rejected"""
        # ent_07 is "chhati me dard" [65, 79] Clinical_Observation
        # Add another Clinical_Observation partially overlapping [70, 85]
        overlap_ent = {
            "entity_id": "ent_obs_overlap",
            "macro_category": "Clinical_Observation",
            "source_text": self.doc["raw_text"][70:85],
            "start_char": 70,
            "end_char": 85,
            "assertion": "Positive",
            "temporality": "Current"
        }
        self.doc["entities"].append(overlap_ent)
        result = self.validator.validate_document(self.doc)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("partial overlapping entity spans" in e for e in result.errors))

    def test_16_missing_patient_id_triggers_unverified_independence_warning(self):
        """Verifies that documents lacking patient_id are explicitly flagged rather than treated as independent"""
        doc1 = copy.deepcopy(self.doc)
        doc1["document_id"] = "DOC_DEV_01"
        doc1["patient_id"] = None  # Missing!
        doc1["dataset_split"] = "development"

        doc2 = copy.deepcopy(self.doc)
        doc2["document_id"] = "DOC_TEST_01"
        doc2["patient_id"] = ""  # Blank!
        doc2["dataset_split"] = "held_out_test"

        corpus = {
            "metadata": {"version": "1.0.0"},
            "documents": [doc1, doc2]
        }
        res = self.validator.validate_corpus(corpus)
        self.assertFalse(res.stats["patient_independence_guaranteed"])
        self.assertEqual(res.stats["docs_missing_patient_id"], 2)
        self.assertTrue(any("Patient independence cannot be verified" in w for w in res.warnings))

    def test_17_approval_booleans_without_institutional_evidence_rejected(self):
        """Verifies that flipping boolean flags to True without institutional numbers/dates does NOT grant approval"""
        tampered_manifest = copy.deepcopy(self.manifest_data)
        tampered_manifest["governance"]["iec_irb_approved"] = True
        tampered_manifest["governance"]["data_owner_authorized"] = True
        tampered_manifest["governance"]["dua_signed"] = True
        # But leave approval_number, data_owner_entity, dua_execution_date null!

        report = BenchmarkLifecycleEvaluator.evaluate_manifest_readiness(
            tampered_manifest, base_dir=BASE_DIR
        )
        self.assertEqual(report["governance_status"], "UNRESOLVED")
        self.assertFalse(report["benchmark_ready_for_evaluation"])
        self.assertTrue(any("missing or empty" in r for r in report["blocking_reasons"]))

    def test_18_duplicate_annotator_id_blocks_double_blind_completion(self):
        """Verifies that identical annotator IDs do not satisfy the double-blind annotation requirement"""
        mock_manifest = copy.deepcopy(self.manifest_data)
        mock_manifest["governance"]["iec_irb_approved"] = True
        mock_manifest["governance"]["iec_approval_number"] = "IEC-2026-9081"
        mock_manifest["governance"]["iec_institution"] = "All India Institute of Medical Sciences"
        mock_manifest["governance"]["data_owner_authorized"] = True
        mock_manifest["governance"]["data_owner_entity"] = "Hospital Medical Directorate"
        mock_manifest["governance"]["dua_signed"] = True
        mock_manifest["governance"]["dua_execution_date"] = "2026-10-01"

        # Create 250 dummy docs with identical annotators (e.g. ANN_01 and ANN_01)
        mock_docs = []
        for i in range(250):
            d = copy.deepcopy(self.doc)
            d["document_id"] = f"DOC_REAL_{i:03d}"
            d["annotation_metadata"]["annotator_ids"] = ["ANN_01", "ANN_01"]  # Not distinct!
            mock_docs.append(d)
        mock_manifest["documents"] = mock_docs

        report = BenchmarkLifecycleEvaluator.evaluate_manifest_readiness(
            mock_manifest, base_dir=BASE_DIR
        )
        self.assertFalse(report["annotations_completed"])
        self.assertTrue(any("distinct double-blinded" in r for r in report["blocking_reasons"]))


if __name__ == "__main__":
    unittest.main()

