"""
PULSE — Phase 5, Step 4.2: Benchmark Annotation Schema Validation Tests
Unit tests verifying that the independent benchmark schema fixture complies with:
1. 0-indexed half-open character span boundaries [start_char, end_char)
2. Character-exact alignment with raw source text
3. Category, assertion, temporality, and investigation status enum validity
4. Synthetic disclosure and metadata integrity
5. Anti-leakage dataset partition constraints
"""

import unittest
import os
import json
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

FIXTURE_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "benchmark_schema_fixture.json")


class TestBenchmarkSchemaValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        self_cls = cls
        if not os.path.exists(FIXTURE_PATH):
            raise FileNotFoundError(f"Fixture file not found: {FIXTURE_PATH}")
        with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
            self_cls.data = json.load(f)

    def test_01_fixture_metadata_and_synthetic_disclosure(self):
        """Verifies top-level metadata and mandatory synthetic data disclosure"""
        self.assertIn("metadata", self.data)
        meta = self.data["metadata"]
        self.assertTrue(meta.get("is_synthetic"), "Metadata must declare is_synthetic=True for scaffolding data")
        self.assertIn("synthetic_disclosure", meta)
        self.assertIn("SYNTHETIC", meta["synthetic_disclosure"].upper())
        self.assertIn("documents", self.data)
        self.assertGreaterEqual(len(self.data["documents"]), 6)

    def test_02_multi_specialty_representation(self):
        """Verifies that all 6 required clinical specialties are represented in the fixture"""
        specialties = [d["specialty"] for d in self.data["documents"]]
        expected_specialties = [
            "General Medicine",
            "Surgery & Orthopedics",
            "Pediatrics & NICU",
            "Obstetrics & Gynecology",
            "Emergency Care",
            "Critical Care (ICU)"
        ]
        for exp in expected_specialties:
            self.assertIn(exp, specialties, f"Missing required specialty in fixture: {exp}")

    def test_03_document_schema_structure(self):
        """Verifies that each document adheres to required schema fields"""
        required_doc_fields = [
            "document_id", "specialty", "raw_text", "char_count",
            "is_synthetic", "dataset_split", "entities", "annotation_metadata"
        ]
        for doc in self.data["documents"]:
            for field in required_doc_fields:
                self.assertIn(field, doc, f"Document {doc.get('document_id')} missing field: {field}")
            self.assertEqual(len(doc["raw_text"]), doc["char_count"], f"char_count mismatch in {doc['document_id']}")
            self.assertTrue(doc["is_synthetic"], f"is_synthetic must be True in document {doc['document_id']}")
            self.assertIn(doc["dataset_split"], ["development", "validation", "held_out_test"])

    def test_04_character_span_offsets_exact_verbatim_alignment(self):
        """Verifies 100% exact character alignment: raw_text[start:end] == source_text"""
        total_entities = 0
        for doc in self.data["documents"]:
            raw_text = doc["raw_text"]
            for ent in doc["entities"]:
                total_entities += 1
                s = ent["start_char"]
                e = ent["end_char"]
                text = ent["source_text"]

                self.assertIsInstance(s, int, f"start_char not integer in {ent['entity_id']}")
                self.assertIsInstance(e, int, f"end_char not integer in {ent['entity_id']}")
                self.assertGreaterEqual(s, 0, f"Negative start_char in {ent['entity_id']}")
                self.assertLess(s, e, f"start_char >= end_char in {ent['entity_id']}")
                self.assertLessEqual(e, len(raw_text), f"end_char out of bounds in {ent['entity_id']}")

                # Verbatim slice verification
                slice_text = raw_text[s:e]
                self.assertEqual(
                    slice_text, text,
                    f"Offset mismatch in {doc['document_id']}, entity {ent['entity_id']}: '{slice_text}' != '{text}'"
                )

                # Leading / trailing whitespace check
                self.assertEqual(text, text.strip(), f"Entity span has untrimmed whitespace: '{text}'")

        self.assertGreaterEqual(total_entities, 30, f"Expected at least 30 entities, found {total_entities}")

    def test_05_macro_category_enum_validity(self):
        """Verifies that all entities belong to the approved 12 clinical macro-categories"""
        approved_categories = {
            "Demographics_Bed", "Demographics_Name", "Demographics_Age",
            "Demographics_Gender", "Demographics_Doctor", "Clinical_Condition",
            "Clinical_Observation", "Medication", "Investigation_Procedure",
            "Care_Activity", "Plan_Goal", "Unclassified"
        }
        for doc in self.data["documents"]:
            for ent in doc["entities"]:
                cat = ent["macro_category"]
                self.assertIn(
                    cat, approved_categories,
                    f"Entity {ent['entity_id']} has unrecognized macro_category: '{cat}'"
                )

    def test_06_assertion_temporality_and_status_enums(self):
        """Verifies valid enums for assertion, temporality, and investigation status"""
        valid_assertions = {"Positive", "Negated", "Possible"}
        valid_temporalities = {"Current", "Historical", "Planned"}
        valid_inv_statuses = {None, "Ordered", "Pending", "Sent", "Awaiting Results", "Completed", "Unknown"}
        valid_review_statuses = {"confirmed", "flagged_for_review", "unreviewed"}

        for doc in self.data["documents"]:
            for ent in doc["entities"]:
                self.assertIn(ent["assertion"], valid_assertions, f"Invalid assertion in {ent['entity_id']}")
                self.assertIn(ent["temporality"], valid_temporalities, f"Invalid temporality in {ent['entity_id']}")
                self.assertIn(ent.get("investigation_status"), valid_inv_statuses, f"Invalid inv status in {ent['entity_id']}")
                self.assertIn(ent["review_status"], valid_review_statuses, f"Invalid review_status in {ent['entity_id']}")

    def test_07_medication_attribute_binding_integrity(self):
        """Verifies that medication attributes contain valid dosage, route, frequency structures"""
        med_count = 0
        for doc in self.data["documents"]:
            for ent in doc["entities"]:
                if ent["macro_category"] == "Medication":
                    med_count += 1
                    attrs = ent.get("medication_attributes")
                    self.assertIsInstance(attrs, dict, f"Medication {ent['entity_id']} must have medication_attributes dict")
                    self.assertIn("dosage", attrs)
                    self.assertIn("route", attrs)
                    self.assertIn("frequency", attrs)
        self.assertGreater(med_count, 0, "No medications found in fixture")

    def test_08_dataset_partition_disjoint_integrity(self):
        """Verifies that development, validation, and held-out test splits have disjoint document IDs"""
        splits = {"development": set(), "validation": set(), "held_out_test": set()}
        for doc in self.data["documents"]:
            s = doc["dataset_split"]
            d_id = doc["document_id"]
            splits[s].add(d_id)

        # Check disjointness
        self.assertEqual(len(splits["development"].intersection(splits["validation"])), 0)
        self.assertEqual(len(splits["development"].intersection(splits["held_out_test"])), 0)
        self.assertEqual(len(splits["validation"].intersection(splits["held_out_test"])), 0)

    def test_09_edge_case_fixture_validation(self):
        """Verifies edge case handling in SYN_EDGE_007: PRN multi-indication, unrecorded dose, cancelled procedure"""
        edge_docs = [d for d in self.data["documents"] if d["document_id"] == "SYN_EDGE_007"]
        self.assertEqual(len(edge_docs), 1, "SYN_EDGE_007 edge-case document must exist in fixture")
        doc = edge_docs[0]

        # Check PRN multi-indication
        pcm = next((e for e in doc["entities"] if e["source_text"] == "Paracetamol"), None)
        self.assertIsNotNone(pcm, "Paracetamol entity must be present")
        self.assertEqual(pcm["medication_attributes"]["prn_indication"], "fever or joint pain")

        # Check unrecorded dose (must remain None, never hallucinated)
        ceft = next((e for e in doc["entities"] if e["source_text"] == "ceftriaxone"), None)
        self.assertIsNotNone(ceft, "Ceftriaxone entity must be present")
        self.assertIsNone(ceft["medication_attributes"]["dosage"], "Dosage must be None when not stated in raw text")
        self.assertIsNone(ceft["medication_attributes"]["frequency"], "Frequency must be None when not stated in raw text")

        # Check cancelled procedure flagged for review
        mri = next((e for e in doc["entities"] if e["source_text"] == "MRI brain"), None)
        self.assertIsNotNone(mri, "MRI brain entity must be present")
        self.assertEqual(mri["review_status"], "flagged_for_review")
        self.assertEqual(mri["temporality"], "Historical")

        # Check chronic condition temporality
        dn = next((e for e in doc["entities"] if e["source_text"] == "diabetic nephropathy"), None)
        self.assertIsNotNone(dn, "diabetic nephropathy entity must be present")
        self.assertEqual(dn["temporality"], "Historical")

    def test_10_manifest_schema_and_integrity_rules(self):
        """Verifies manifest schema validation logic and partition disjointness rules"""
        # Define a mock valid manifest conforming to the benchmark manifest contract
        sample_manifest = {
            "manifest_version": "1.0.0",
            "dataset_version": "0.1.0-synthetic-scaffolding",
            "planned_notes_count": 250,
            "available_notes_count": len(self.data["documents"]),
            "records": [
                {
                    "note_id": doc["document_id"],
                    "specialty": doc["specialty"],
                    "source_type": "synthetic_scaffolding",
                    "synthetic_flag": True,
                    "authorization_status": "NOT_APPLICABLE_SYNTHETIC",
                    "annotation_status": "ANNOTATED",
                    "adjudication_status": doc["annotation_metadata"]["adjudication_status"],
                    "partition": doc["dataset_split"],
                    "text_sha256": "placeholder_sha256_hash"
                }
                for doc in self.data["documents"]
            ]
        }

        # Validate top-level manifest structure
        self.assertIn("manifest_version", sample_manifest)
        self.assertIn("planned_notes_count", sample_manifest)
        self.assertEqual(sample_manifest["planned_notes_count"], 250)
        self.assertEqual(sample_manifest["available_notes_count"], len(self.data["documents"]))

        # Validate duplicate detection
        note_ids = [r["note_id"] for r in sample_manifest["records"]]
        self.assertEqual(len(note_ids), len(set(note_ids)), "Duplicate note_ids must not exist in manifest")

        # Validate partition disjointness
        partitions = {}
        for r in sample_manifest["records"]:
            partitions.setdefault(r["partition"], set()).add(r["note_id"])
        all_partition_ids = [nid for s in partitions.values() for nid in s]
        self.assertEqual(len(all_partition_ids), len(set(all_partition_ids)), "Partitions must be strictly disjoint")


if __name__ == "__main__":
    unittest.main()
