"""
PULSE Test Suite: Patient Database Foundation & Confidence Transparency (Phase 2A-2B)
Tests:
1. Database initialization can run repeatedly.
2. Existing database tables and analysis history remain intact.
3. Demo patient seeding does not duplicate records.
4. Patient listing returns stable identifiers.
5. Search filters the expected demo records.
6. A valid patient ID returns its profile.
7. An invalid patient ID returns 404.
8. Invalid patient input returns an appropriate 4xx response.
9. Foreign keys prevent orphaned notes.
10. Confidence metadata never falsely represents hardcoded strings as measured probabilities.
"""

import os
import sys
import tempfile
import sqlite3
import unittest
from fastapi.testclient import TestClient

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from backend.main import app
from backend.database.database import Database, db
from backend.extraction.clinical_bert_extractor import clinical_bert_extractor
from backend.extraction.entity_extractor import clinical_entity_extractor


class TestPatientDatabaseAndTransparency(unittest.TestCase):
    def setUp(self):
        # Create an isolated temporary SQLite database for database tests
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        self.test_db = Database(db_path=self.temp_db_path)
        self.client = TestClient(app)

    def tearDown(self):
        # Safely clean up temporary test database
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except Exception:
                pass

    def test_1_database_initialization_repeatable(self):
        """1. Database initialization can run repeatedly without error."""
        # Initialized once in setUp, now re-run multiple times
        for _ in range(3):
            self.test_db._init_db()

        with self.test_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {r[0] for r in cursor.fetchall()}
            required_tables = {
                "analysis_history", "reports_cache", "patients",
                "patient_notes", "note_extractions", "note_reviews", "simulated_vitals"
            }
            self.assertTrue(required_tables.issubset(tables), f"Missing tables: {required_tables - tables}")

    def test_2_existing_tables_and_analysis_history_intact(self):
        """2. Existing database tables and analysis history remain intact during additive migrations."""
        # Save a sample analysis history entry
        saved_id = self.test_db.save_analysis(
            report_id="TEST-001",
            raw_text="Patient observed overnight.",
            preprocessed_text="Patient observed overnight.",
            structured_data={"summary": "Stable overnight."}
        )
        self.assertGreater(saved_id, 0)

        # Re-run initialization
        self.test_db._init_db()

        # Verify entry remains intact
        recent = self.test_db.get_recent_analyses(limit=5)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["report_id"], "TEST-001")
        self.assertEqual(recent[0]["structured_output"], {"summary": "Stable overnight."})

    def test_3_demo_patient_seeding_idempotent(self):
        """3. Demo patient seeding does not duplicate records when re-run."""
        # Initial seed happened on setup -> 10 records
        patients_pass1 = self.test_db.list_patients()
        self.assertEqual(len(patients_pass1), 10)

        # Run seeder again
        new_count = self.test_db.seed_demo_patients()
        self.assertEqual(new_count, 0)

        # Verify count is still exactly 10
        patients_pass2 = self.test_db.list_patients()
        self.assertEqual(len(patients_pass2), 10)

    def test_4_patient_listing_returns_stable_identifiers(self):
        """4. Patient listing returns stable synthetic identifiers."""
        patients = self.test_db.list_patients()
        self.assertEqual(len(patients), 10)

        display_ids = [p["display_id"] for p in patients]
        expected_ids = [f"PULSE-DEMO-{i:03d}" for i in range(1, 11)]
        self.assertEqual(display_ids, expected_ids)

        for p in patients:
            self.assertIn("id", p)
            self.assertIn("name", p)
            self.assertIn("ward", p)
            self.assertIn("admitting_diagnosis", p)
            self.assertIn("created_at", p)

    def test_5_search_filters_expected_demo_records(self):
        """5. Search filters the expected demo records."""
        # Search by patient name
        res_vera = self.test_db.list_patients(search="Vera")
        self.assertEqual(len(res_vera), 1)
        self.assertEqual(res_vera[0]["display_id"], "PULSE-DEMO-002")

        # Search by display identifier
        res_demo4 = self.test_db.list_patients(search="PULSE-DEMO-004")
        self.assertEqual(len(res_demo4), 1)
        self.assertEqual(res_demo4[0]["name"], "Pierre Cox")

        # Search by consultant
        res_hanlen = self.test_db.list_patients(search="Hanlen")
        self.assertEqual(len(res_hanlen), 1)
        self.assertEqual(res_hanlen[0]["display_id"], "PULSE-DEMO-001")

        # Search for non-existent query
        res_none = self.test_db.list_patients(search="NonExistentPersonXYZ")
        self.assertEqual(len(res_none), 0)

    def test_6_valid_patient_id_returns_profile(self):
        """6. A valid patient ID returns its complete profile with simulated vitals."""
        # Query via live database
        patient = self.test_db.get_patient("PULSE-DEMO-001")
        self.assertIsNotNone(patient)
        self.assertEqual(patient["name"], "Michael I Wu")
        self.assertEqual(patient["bed_number"], "Bed 8")
        self.assertIsNotNone(patient.get("vitals"))
        self.assertEqual(patient["vitals"]["hr"], 78)
        self.assertIn("Simulated", patient["vitals"]["data_source"])

        # Query via live API route
        response = self.client.get("/api/patients/PULSE-DEMO-001")
        self.assertEqual(response.status_code, 200)
        api_data = response.json()
        self.assertEqual(api_data["name"], "Michael I Wu")
        self.assertIsNotNone(api_data.get("vitals"))

    def test_7_invalid_patient_id_returns_404(self):
        """7. An invalid patient ID returns 404."""
        response = self.client.get("/api/patients/UNKNOWN-PATIENT-999")
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"].lower())

        response_num = self.client.get("/api/patients/999999")
        self.assertEqual(response_num.status_code, 404)

    def test_8_invalid_patient_input_returns_4xx(self):
        """8. Invalid patient input returns an appropriate 4xx response."""
        # Missing required fields -> 422 Unprocessable Entity
        resp_missing = self.client.post("/api/patients", json={})
        self.assertEqual(resp_missing.status_code, 422)

        # Duplicate display_id -> 400 Bad Request
        duplicate_payload = {
            "display_id": "PULSE-DEMO-001",
            "name": "Duplicate Test Name",
            "ward": "Neurology"
        }
        resp_duplicate = self.client.post("/api/patients", json=duplicate_payload)
        self.assertEqual(resp_duplicate.status_code, 400)
        self.assertIn("already exists", resp_duplicate.json()["detail"].lower())

    def test_9_foreign_keys_prevent_orphaned_notes(self):
        """9. SQLite Foreign Keys prevent orphaned records."""
        with self.test_db._get_connection() as conn:
            cursor = conn.cursor()
            # Attempt to insert note referencing non-existent patient_id
            with self.assertRaises(sqlite3.IntegrityError):
                cursor.execute("""
                    INSERT INTO patient_notes (patient_id, raw_text, created_at, updated_at)
                    VALUES (999999, 'Orphaned handover note text', '2026-01-01T00:00:00', '2026-01-01T00:00:00')
                """)

    def test_10_confidence_metadata_never_falsely_represents_measured_probabilities(self):
        """10. Confidence metadata never falsely represents hardcoded strings as measured probabilities."""
        sample_text = (
            "Bed eight, Michael I Wu. Forty-eight years under Dr Hanlen. "
            "He came in with headache and vertigo. Digoxin 0.25mg daily. "
            "BP 120/80 mmHg, GCS 15. Plan CT brain."
        )

        # Test Bio_ClinicalBERT extractor
        bert_res = clinical_bert_extractor.extract(sample_text)
        # Test Rule extractor
        rule_res = clinical_entity_extractor.extract(sample_text)

        for engine_name, res in [("Bio_ClinicalBERT", bert_res), ("Rule Engine", rule_res)]:
            all_entities = []
            for cat in ["patient_information", "conditions", "symptoms", "medications", "investigations", "treatments"]:
                all_entities.extend(res.get(cat, []))

            self.assertGreater(len(all_entities), 0, f"Engine {engine_name} extracted 0 entities")

            for ent in all_entities:
                # 1. confidence MUST be None / null (never hardcoded 'High')
                self.assertIsNone(
                    ent.get("confidence"),
                    f"Entity '{ent.get('text') or ent.get('value')}' has non-null confidence: {ent.get('confidence')}"
                )
                self.assertNotIn(
                    "high",
                    str(ent.get("confidence", "")).lower(),
                    "Forbidden hardcoded 'High' string detected in confidence field"
                )

                # 2. confidence_type must be explicit
                self.assertIn(
                    ent.get("confidence_type"),
                    ["uncalibrated_raw_probability", "deterministic_rule", "unavailable"]
                )

                # 3. calibrated must be explicitly False
                self.assertFalse(
                    ent.get("calibrated", False),
                    "Neural entities must not claim calibration when not evaluated"
                )

                # 4. Check raw probability bounds
                if ent.get("confidence_type") == "uncalibrated_raw_probability":
                    raw_prob = ent.get("raw_model_probability")
                    self.assertIsNotNone(raw_prob)
                    self.assertGreaterEqual(raw_prob, 0.0)
                    self.assertLessEqual(raw_prob, 1.0)
                elif ent.get("confidence_type") == "deterministic_rule":
                    self.assertIsNone(ent.get("raw_model_probability"))
                    self.assertIsNotNone(ent.get("rule_source"))


if __name__ == "__main__":
    unittest.main()
