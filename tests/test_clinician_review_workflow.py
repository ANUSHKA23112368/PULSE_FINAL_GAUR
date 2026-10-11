"""
PULSE Test Suite: Clinician Review and Handover Verification Workflow (Phase 2D)
Tests:
1. Saving a valid clinician review (200 OK, status -> 'Reviewed', timestamp and reviewer).
2. Rejecting a review for a nonexistent patient or note (404 Not Found).
3. Rejecting a review for a note belonging to another patient (cross-patient isolation 404).
4. Rejecting review of a note that has not been processed (reject Draft status with 400 Bad Request).
5. Preserving original AI extraction after editing (note_extractions untouched).
6. Preserving original note text verbatim (raw_text untouched).
7. Updating note status to 'Reviewed' only after successful review persistence (transactional integrity).
8. Retrieving saved review, reviewer identifier, and timestamp via GET APIs.
9. Handling invalid or empty reviewed_data (400 Bad Request).
10. Preserving earlier review records in review_history when multiple reviews are submitted.
"""

import os
import sys
import tempfile
import unittest
from fastapi.testclient import TestClient

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from backend.main import app
import backend.api.routes
from backend.database.database import Database, db


class TestClinicianReviewWorkflow(unittest.TestCase):
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

    def _create_and_process_sample_note(self, patient_display_id="PULSE-DEMO-001"):
        """Helper to create and process a note for testing."""
        patient = self.test_db.get_patient(patient_display_id)
        raw_text = (
            "Patient Michael Wu presented with sudden vertigo, vomiting and gait instability. "
            "Commenced IV Stemetil 12.5mg and IV normal saline. CT brain ordered. Nil acute bleed."
        )
        note = self.test_db.create_patient_note(
            patient_id=patient["id"],
            raw_text=raw_text,
            author_identifier="Nurse Sarah"
        )
        # Process the note
        proc_resp = self.client.post(f"/api/patients/{patient['display_id']}/notes/{note['id']}/process")
        self.assertEqual(proc_resp.status_code, 200)
        return patient, proc_resp.json()

    def test_1_save_valid_review(self):
        """1. Saving a valid clinician review persists review and transitions status to 'Reviewed'."""
        patient, proc_note = self._create_and_process_sample_note()
        note_id = proc_note["id"]

        reviewed_data = {
            "isbar": {
                "situation": "Patient Michael Wu admitted with acute vestibular vertigo.",
                "background": "No prior cerebrovascular history.",
                "assessment": "Vertigo improving post-Stemetil, CT brain negative for hemorrhage.",
                "recommendation": "Repeat neurology consult in AM, mobilize with physio."
            },
            "entities": {
                "conditions": [
                    {"text": "acute vestibular vertigo", "is_negated": False, "is_historical": False},
                    {"text": "cerebrovascular hemorrhage", "is_negated": True, "is_historical": False}
                ],
                "medications": [
                    {"text": "Stemetil", "dosage": "12.5mg", "frequency": "STAT", "route": "IV"}
                ]
            },
            "pending_tasks": [
                {"task": "Neurology review tomorrow morning"}
            ]
        }

        resp = self.client.post(
            f"/api/patients/{patient['display_id']}/notes/{note_id}/review",
            json={
                "reviewed_data": reviewed_data,
                "reviewer_identifier": "Dr. Sarah Hanlen, MD",
                "review_notes": "Confirmed negative CT, adjusted physio mobilization orders."
            }
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIsNotNone(data["review_id"])
        self.assertEqual(data["note_id"], note_id)
        self.assertEqual(data["patient_id"], patient["id"])
        self.assertEqual(data["status"], "Reviewed")
        self.assertEqual(data["reviewer_identifier"], "Dr. Sarah Hanlen, MD")
        self.assertIn("Confirmed negative CT", data["review_notes"])
        self.assertIsNotNone(data["reviewed_at"])
        self.assertEqual(data["reviewed_data"]["isbar"]["situation"], "Patient Michael Wu admitted with acute vestibular vertigo.")

        # Verify note state in db
        db_note = self.test_db.get_patient_note(patient["id"], note_id)
        self.assertEqual(db_note["status"], "Reviewed")
        self.assertEqual(db_note["reviewer_identifier"], "Dr. Sarah Hanlen, MD")
        self.assertIsNotNone(db_note["review"])

    def test_2_reject_review_for_nonexistent_patient_or_note(self):
        """2. Rejecting a review for a nonexistent patient or nonexistent note returns 404."""
        patient, proc_note = self._create_and_process_sample_note()

        payload = {
            "reviewed_data": {"isbar": {"situation": "test"}},
            "reviewer_identifier": "Dr. Tester"
        }

        # Nonexistent patient
        resp_patient = self.client.post(
            f"/api/patients/PULSE-NONEXISTENT-999/notes/{proc_note['id']}/review",
            json=payload
        )
        self.assertEqual(resp_patient.status_code, 404)

        # Nonexistent note
        resp_note = self.client.post(
            f"/api/patients/{patient['display_id']}/notes/999999/review",
            json=payload
        )
        self.assertEqual(resp_note.status_code, 404)

    def test_3_reject_note_belonging_to_another_patient(self):
        """3. Rejecting a review for a note belonging to another patient returns 404 (cross-patient isolation)."""
        patient1, proc_note1 = self._create_and_process_sample_note("PULSE-DEMO-001")
        patient2 = self.test_db.get_patient("PULSE-DEMO-002")

        payload = {
            "reviewed_data": {"isbar": {"situation": "Cross patient attempt"}},
            "reviewer_identifier": "Dr. Attacker"
        }

        # Attempt to review note 1 using patient 2's display ID
        resp = self.client.post(
            f"/api/patients/{patient2['display_id']}/notes/{proc_note1['id']}/review",
            json=payload
        )
        self.assertEqual(resp.status_code, 404)

    def test_4_reject_review_of_unprocessed_draft_note(self):
        """4. Rejecting reviews of notes that are still in 'Draft' status returns 400 Bad Request."""
        patient = self.test_db.get_patient("PULSE-DEMO-001")
        draft_note = self.test_db.create_patient_note(
            patient_id=patient["id"],
            raw_text="Unprocessed clinical draft note.",
            author_identifier="Nurse Amy"
        )
        self.assertEqual(draft_note["status"], "Draft")

        payload = {
            "reviewed_data": {"isbar": {"situation": "Premature review"}},
            "reviewer_identifier": "Dr. Early"
        }

        resp = self.client.post(
            f"/api/patients/{patient['display_id']}/notes/{draft_note['id']}/review",
            json=payload
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("has not been processed", resp.json()["detail"])

    def test_5_preserve_original_ai_extraction_after_editing(self):
        """5. Preserving original AI extraction after human review editing."""
        patient, proc_note = self._create_and_process_sample_note()
        note_id = proc_note["id"]

        original_ext_data = proc_note["extraction"]["data"]
        original_engine = proc_note["extraction"]["engine_used"]
        self.assertIsNotNone(original_ext_data)

        # Submit human review with completely rewritten content
        reviewed_data = {
            "isbar": {"situation": "Completely revised clinical handover by human clinician."},
            "entities": {"conditions": [{"text": "Revised condition"}]}
        }

        resp = self.client.post(
            f"/api/patients/{patient['display_id']}/notes/{note_id}/review",
            json={
                "reviewed_data": reviewed_data,
                "reviewer_identifier": "Dr. Auditor"
            }
        )
        self.assertEqual(resp.status_code, 200)

        # Fetch note again and check original extraction
        updated_note = self.test_db.get_patient_note(patient["id"], note_id)
        self.assertEqual(updated_note["status"], "Reviewed")
        self.assertIsNotNone(updated_note["extraction"])
        self.assertEqual(updated_note["extraction"]["engine_used"], original_engine)
        self.assertEqual(updated_note["extraction"]["data"], original_ext_data)
        # Verify human edits are in review, NOT in extraction
        self.assertNotEqual(updated_note["extraction"]["data"], reviewed_data)
        self.assertEqual(updated_note["review"]["reviewed_data"], reviewed_data)

    def test_6_preserve_original_note_text_verbatim(self):
        """6. Preserving original note raw_text verbatim through note creation, processing, and review."""
        patient, proc_note = self._create_and_process_sample_note()
        note_id = proc_note["id"]
        original_text = proc_note["raw_text"]

        # Submit review
        self.client.post(
            f"/api/patients/{patient['display_id']}/notes/{note_id}/review",
            json={
                "reviewed_data": {"isbar": {"situation": "New situation"}},
                "reviewer_identifier": "Dr. Sarah"
            }
        )

        updated_note = self.test_db.get_patient_note(patient["id"], note_id)
        self.assertEqual(updated_note["raw_text"], original_text)

    def test_7_transactional_integrity_status_only_updated_on_success(self):
        """7. Database transaction ensures a failed review does not leave note marked 'Reviewed'."""
        patient, proc_note = self._create_and_process_sample_note()
        note_id = proc_note["id"]

        # Call with invalid reviewed_data directly to DB or API
        with self.assertRaises(ValueError):
            self.test_db.review_patient_note(
                patient_id=patient["id"],
                note_id=note_id,
                reviewed_data={},  # Invalid empty dict
                reviewer_identifier="Dr. Test"
            )

        # Note should still be Processed, NOT Reviewed
        note_after_failed_tx = self.test_db.get_patient_note(patient["id"], note_id)
        self.assertEqual(note_after_failed_tx["status"], "Processed")
        self.assertIsNone(note_after_failed_tx["review"])

    def test_8_retrieve_saved_review_and_timestamp(self):
        """8. Retrieving saved review, reviewer identifier, and timestamp via GET APIs."""
        patient, proc_note = self._create_and_process_sample_note()
        note_id = proc_note["id"]

        review_payload = {
            "reviewed_data": {
                "isbar": {"situation": "Verified situation"},
                "conditions": ["Condition 1"]
            },
            "reviewer_identifier": "Dr. Marcus Vance, Chief Medical Officer",
            "review_notes": "Verified after bedside rounds."
        }

        post_resp = self.client.post(
            f"/api/patients/{patient['display_id']}/notes/{note_id}/review",
            json=review_payload
        )
        self.assertEqual(post_resp.status_code, 200)

        # 1. Test single note GET endpoint
        get_single_resp = self.client.get(f"/api/patients/{patient['display_id']}/notes/{note_id}")
        self.assertEqual(get_single_resp.status_code, 200)
        single_data = get_single_resp.json()

        self.assertEqual(single_data["status"], "Reviewed")
        self.assertEqual(single_data["reviewer_identifier"], "Dr. Marcus Vance, Chief Medical Officer")
        self.assertIsNotNone(single_data["reviewed_at"])
        self.assertIsNotNone(single_data["review"])
        self.assertEqual(single_data["review"]["review_notes"], "Verified after bedside rounds.")
        self.assertEqual(single_data["raw_text"], proc_note["raw_text"])
        self.assertIsNotNone(single_data["extraction"])

        # 2. Test list notes GET endpoint
        get_list_resp = self.client.get(f"/api/patients/{patient['display_id']}/notes")
        self.assertEqual(get_list_resp.status_code, 200)
        list_notes = get_list_resp.json()["notes"]
        reviewed_entry = next(n for n in list_notes if n["id"] == note_id)
        self.assertEqual(reviewed_entry["status"], "Reviewed")
        self.assertEqual(reviewed_entry["reviewer_identifier"], "Dr. Marcus Vance, Chief Medical Officer")
        self.assertIsNotNone(reviewed_entry["reviewed_at"])

    def test_9_handle_invalid_reviewed_data(self):
        """9. Handling invalid or empty reviewed_data returns 400 Bad Request."""
        patient, proc_note = self._create_and_process_sample_note()
        note_id = proc_note["id"]

        # Empty dictionary
        resp_empty = self.client.post(
            f"/api/patients/{patient['display_id']}/notes/{note_id}/review",
            json={"reviewed_data": {}, "reviewer_identifier": "Dr. Test"}
        )
        self.assertEqual(resp_empty.status_code, 400)

    def test_10_keep_earlier_review_records_when_multiple_reviews(self):
        """10. Preserving earlier review records in review_history when note is reviewed multiple times."""
        patient, proc_note = self._create_and_process_sample_note()
        note_id = proc_note["id"]

        # Review 1 by Dr. First
        resp1 = self.client.post(
            f"/api/patients/{patient['display_id']}/notes/{note_id}/review",
            json={
                "reviewed_data": {"isbar": {"situation": "First human review"}},
                "reviewer_identifier": "Dr. First, Registrar",
                "review_notes": "Initial review"
            }
        )
        self.assertEqual(resp1.status_code, 200)

        # Review 2 by Dr. Second (Senior Consultant)
        resp2 = self.client.post(
            f"/api/patients/{patient['display_id']}/notes/{note_id}/review",
            json={
                "reviewed_data": {"isbar": {"situation": "Second human review (Senior sign-off)"}},
                "reviewer_identifier": "Dr. Second, Senior Consultant",
                "review_notes": "Final sign-off"
            }
        )
        self.assertEqual(resp2.status_code, 200)

        # Verify DB state
        note = self.test_db.get_patient_note(patient["id"], note_id)
        self.assertEqual(note["status"], "Reviewed")
        self.assertEqual(note["reviewer_identifier"], "Dr. Second, Senior Consultant")
        self.assertEqual(note["review"]["reviewer_identifier"], "Dr. Second, Senior Consultant")

        # History should contain both reviews in descending order (latest first)
        self.assertIn("review_history", note)
        self.assertEqual(len(note["review_history"]), 2)
        self.assertEqual(note["review_history"][0]["reviewer_identifier"], "Dr. Second, Senior Consultant")
        self.assertEqual(note["review_history"][1]["reviewer_identifier"], "Dr. First, Registrar")
        self.assertEqual(note["review_history"][1]["review_notes"], "Initial review")


if __name__ == "__main__":
    unittest.main()
