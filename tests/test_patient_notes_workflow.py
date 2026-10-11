"""
PULSE Test Suite: Patient Clinical Notes Workflow Backend (Phase 2C)
Tests:
1. Creating a draft note for the correct patient.
2. Rejecting empty or whitespace-only notes (400 Bad Request).
3. Retrieving notes by patient ID (chronological order).
4. Preventing cross-patient note access (isolation guarantees).
5. Processing a saved draft note via the NLP pipeline.
6. Persisting extraction output in note_extractions table.
7. Preserving original note text verbatim before and after processing.
8. Retaining historical notes after a new note is added.
9. Handling requests for non-existent patients gracefully (404).
10. Tagging extraction outputs with unreviewed status ("AI-generated — not yet reviewed").
"""

import os
import sys
import tempfile
import unittest
from fastapi.testclient import TestClient

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from backend.main import app
import backend.api.routes
from backend.database.database import Database, db


class TestPatientNotesWorkflow(unittest.TestCase):
    def setUp(self):
        # Create an isolated temporary test SQLite database
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.temp_db_fd)
        self.test_db = Database(db_path=self.temp_db_path)
        self.orig_routes_db = backend.api.routes.db
        backend.api.routes.db = self.test_db
        self.client = TestClient(app)

    def tearDown(self):
        backend.api.routes.db = self.orig_routes_db
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except Exception:
                pass

    def test_1_create_draft_note_for_correct_patient(self):
        """1. Creating a draft note for the correct patient returns 201 with 'Draft' status."""
        patient = self.test_db.get_patient("PULSE-DEMO-001")
        self.assertIsNotNone(patient)

        note_text = "Patient Michael Wu admitted with acute vertigo and severe headache. Vitals stable."
        note = self.test_db.create_patient_note(
            patient_id=patient["id"],
            raw_text=note_text,
            author_identifier="Dr. Hanlen (Demo)"
        )

        self.assertIsNotNone(note["id"])
        self.assertEqual(note["patient_id"], patient["id"])
        self.assertEqual(note["raw_text"], note_text)
        self.assertEqual(note["status"], "Draft")
        self.assertEqual(note["author_identifier"], "Dr. Hanlen (Demo)")
        self.assertIsNone(note["extraction"])

        # Also verify via API client
        api_resp = self.client.post(
            f"/api/patients/{patient['display_id']}/notes",
            json={"raw_text": "Second draft note for Michael.", "author_identifier": "Nurse Jane"}
        )
        self.assertEqual(api_resp.status_code, 201)
        api_note = api_resp.json()
        self.assertEqual(api_note["status"], "Draft")
        self.assertEqual(api_note["raw_text"], "Second draft note for Michael.")

    def test_2_reject_empty_or_whitespace_notes(self):
        """2. Rejecting empty or whitespace-only notes with 400 Bad Request."""
        patient = self.test_db.get_patient("PULSE-DEMO-001")

        # Database direct validation
        with self.assertRaises(ValueError):
            self.test_db.create_patient_note(patient["id"], "")
        with self.assertRaises(ValueError):
            self.test_db.create_patient_note(patient["id"], "   \n\t  ")

        # API validation
        resp_empty = self.client.post(
            f"/api/patients/{patient['display_id']}/notes",
            json={"raw_text": "   "}
        )
        self.assertEqual(resp_empty.status_code, 400)
        self.assertIn("cannot be empty", resp_empty.json()["detail"].lower())

    def test_3_retrieve_notes_by_patient_id(self):
        """3. Retrieving notes by patient ID returns chronological list."""
        patient = self.test_db.get_patient("PULSE-DEMO-002")

        note1 = self.test_db.create_patient_note(patient["id"], "Note 1: Chest pain reported.", "Nurse A")
        note2 = self.test_db.create_patient_note(patient["id"], "Note 2: Administered GTN spray.", "Nurse B")

        notes = self.test_db.get_patient_notes(patient["id"])
        self.assertEqual(len(notes), 2)
        # Verify retrieved notes belong strictly to this patient
        for n in notes:
            self.assertEqual(n["patient_id"], patient["id"])

        # Test via API
        resp = self.client.get(f"/api/patients/{patient['display_id']}/notes")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["display_id"], patient["display_id"])
        self.assertGreaterEqual(data["total_notes"], 2)

    def test_4_prevent_cross_patient_note_access(self):
        """4. Preventing cross-patient note access (isolation guarantees)."""
        patient1 = self.test_db.get_patient("PULSE-DEMO-001")
        patient2 = self.test_db.get_patient("PULSE-DEMO-002")

        note1 = self.test_db.create_patient_note(patient1["id"], "Confidential note for Patient 1.", "Dr. A")

        # Patient 2 trying to get Patient 1's note returns None in DB
        isolated = self.test_db.get_patient_note(patient2["id"], note1["id"])
        self.assertIsNone(isolated)

        # Via API: querying Patient 2 with Patient 1's note ID returns 404
        resp = self.client.post(
            f"/api/patients/{patient2['display_id']}/notes/{note1['id']}/process"
        )
        self.assertEqual(resp.status_code, 404)

    def test_5_and_6_process_saved_note_and_persist_extraction(self):
        """5 & 6. Processing a saved draft note via NLP and persisting extraction output."""
        patient = self.test_db.get_patient("PULSE-DEMO-001")
        note_text = "Bed eight, Michael I Wu. Forty-eight years under Dr Hanlen. Headache and vertigo. Digoxin 0.25mg daily."

        # Create draft via API
        create_resp = self.client.post(
            f"/api/patients/{patient['display_id']}/notes",
            json={"raw_text": note_text, "author_identifier": "Staff Nurse"}
        )
        self.assertEqual(create_resp.status_code, 201)
        created_note = create_resp.json()
        self.assertEqual(created_note["status"], "Draft")
        self.assertIsNone(created_note["extraction"])

        # Process note via API
        proc_resp = self.client.post(
            f"/api/patients/{patient['display_id']}/notes/{created_note['id']}/process"
        )
        self.assertEqual(proc_resp.status_code, 200)
        processed_note = proc_resp.json()

        # Verify status transitioned to 'Processed'
        self.assertEqual(processed_note["status"], "Processed")
        self.assertIsNotNone(processed_note["extraction"])
        ext = processed_note["extraction"]
        self.assertIn("engine_used", ext)
        self.assertIsNotNone(ext["data"])

        # Verify extraction data contains structured categories
        ext_data = ext["data"]
        self.assertIn("entities", ext_data)
        self.assertIn("structured_handover", ext_data)
        self.assertIn("isbar", ext_data)

        # Subsequent retrieval confirms persistence
        get_resp = self.client.get(f"/api/patients/{patient['display_id']}/notes")
        all_notes = get_resp.json()["notes"]
        matching = [n for n in all_notes if n["id"] == created_note["id"]]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["status"], "Processed")
        self.assertIsNotNone(matching[0]["extraction"])

    def test_7_preserving_original_note_text(self):
        """7. Preserving original note text verbatim before and after processing."""
        patient = self.test_db.get_patient("PULSE-DEMO-003")
        exact_text = "   Bed 5, Leila sonya Da silva, 34 under Dr Liu. Blood sugar 14.2 mmol/L.   "

        note = self.test_db.create_patient_note(patient["id"], exact_text, "Nurse C")
        self.assertEqual(note["raw_text"], exact_text)

        # Process the note
        proc_note = self.test_db.process_patient_note(
            patient_id=patient["id"],
            note_id=note["id"],
            extraction_data={"test": "dummy_extraction"},
            engine_used="TestEngine"
        )
        # Note text MUST NOT be modified or normalized
        self.assertEqual(proc_note["raw_text"], exact_text)

    def test_8_retaining_historical_notes_after_new_note_added(self):
        """8. Retaining historical notes after a new note is added."""
        patient = self.test_db.get_patient("PULSE-DEMO-004")

        # Note 1
        n1 = self.test_db.create_patient_note(patient["id"], "Day 1: Leg swelling observed.", "Dr. A")
        self.test_db.process_patient_note(patient["id"], n1["id"], {"summary": "Day 1 processed"})

        # Note 2
        n2 = self.test_db.create_patient_note(patient["id"], "Day 2: Ultrasound confirmed DVT.", "Dr. B")

        notes = self.test_db.get_patient_notes(patient["id"])
        self.assertEqual(len(notes), 2)
        note_ids = {n["id"] for n in notes}
        self.assertIn(n1["id"], note_ids)
        self.assertIn(n2["id"], note_ids)

        # Verify n1 retained its processed extraction
        n1_retrieved = [n for n in notes if n["id"] == n1["id"]][0]
        self.assertEqual(n1_retrieved["status"], "Processed")
        self.assertIsNotNone(n1_retrieved["extraction"])

    def test_9_error_handling_nonexistent_patient(self):
        """9. Handling requests for non-existent patients returns 404."""
        resp_get = self.client.get("/api/patients/NON-EXISTENT-XYZ/notes")
        self.assertEqual(resp_get.status_code, 404)

        resp_post = self.client.post(
            "/api/patients/NON-EXISTENT-XYZ/notes",
            json={"raw_text": "Sample text"}
        )
        self.assertEqual(resp_post.status_code, 404)

    def test_10_ai_generated_unreviewed_metadata_present(self):
        """10. Extracted output explicitly includes unreviewed clinical assertion metadata."""
        patient = self.test_db.get_patient("PULSE-DEMO-001")
        note = self.test_db.create_patient_note(patient["id"], "Bed 8, Michael Wu. Headache improved.", "Nurse A")

        resp = self.client.post(f"/api/patients/{patient['display_id']}/notes/{note['id']}/process")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["extraction"]["data"]

        self.assertEqual(data.get("review_status"), "ai_generated_unreviewed")
        self.assertIn("not yet reviewed", data.get("status_label", "").lower())
        self.assertFalse(data.get("is_human_reviewed"))
        self.assertIn("not verified by a clinician", data.get("disclaimer", "").lower())


if __name__ == "__main__":
    unittest.main()
