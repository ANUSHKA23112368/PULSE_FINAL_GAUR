"""
PULSE Test Suite: Synthetic Demo Patient Creation Workflow (Phase 2F)
Tests:
1. Successful patient creation with auto-generated unique display ID (PULSE-DEMO-011).
2. Successful patient creation with custom valid display ID.
3. Rejection of patient creation with missing or whitespace-only name (400 Bad Request).
4. Collision-safe unique ID auto-generation across multiple sequential patient creations.
5. Rejection of duplicate display_id submission (400 Bad Request).
6. Retrieval of newly created patient by display_id and primary key id with simulated vitals attached.
7. Persistence of new patient across database reconnection / re-instantiation.
8. Complete clinical isolation: new patient notes/history do not cross-pollinate with existing patients.
9. Regression verification: all 10 original synthetic seeded patients remain intact and unmodified.
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
from backend.database.database import Database


class TestPatientCreationWorkflow(unittest.TestCase):
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

    def test_1_create_patient_with_auto_generated_display_id(self):
        """1. Successful patient creation with auto-generated unique display ID."""
        initial_patients = self.test_db.list_patients()
        self.assertEqual(len(initial_patients), 10)

        payload = {
            "name": "Eleanor Vance",
            "age": "58 years",
            "gender": "Female",
            "ward": "Cardiology (Demo Ward A)",
            "bed_number": "Bed 4",
            "consultant": "Dr. Sarah Hanlen",
            "admitting_diagnosis": "Acute palpitations and exertional dyspnea (Synthetic demo)"
        }

        resp = self.client.post("/api/patients", json=payload)
        self.assertEqual(resp.status_code, 201)
        created = resp.json()

        self.assertEqual(created["name"], "Eleanor Vance")
        self.assertEqual(created["display_id"], "PULSE-DEMO-011")
        self.assertEqual(created["ward"], "Cardiology (Demo Ward A)")
        self.assertIsNotNone(created["vitals"])
        self.assertEqual(created["vitals"]["data_source"], "Simulated Clinical Demonstration Data (Synthetic Engine)")

        # Verify list updated to 11
        updated_list = self.test_db.list_patients()
        self.assertEqual(len(updated_list), 11)

    def test_2_create_patient_with_custom_display_id(self):
        """2. Successful patient creation with explicit custom display ID."""
        payload = {
            "display_id": "PULSE-CUSTOM-999",
            "name": "Arthur Pendelton",
            "age": "67 years",
            "gender": "Male",
            "ward": "Orthopaedics",
            "bed_number": "Bed 1",
            "consultant": "Dr. Miller",
            "admitting_diagnosis": "Elective total hip replacement"
        }

        resp = self.client.post("/api/patients", json=payload)
        self.assertEqual(resp.status_code, 201)
        created = resp.json()

        self.assertEqual(created["display_id"], "PULSE-CUSTOM-999")
        self.assertEqual(created["name"], "Arthur Pendelton")

        # Query back via GET endpoint
        get_resp = self.client.get("/api/patients/PULSE-CUSTOM-999")
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.json()["name"], "Arthur Pendelton")

    def test_3_rejection_of_empty_or_whitespace_name(self):
        """3. Rejection of patient creation with missing or whitespace-only name."""
        # Whitespace-only name
        resp1 = self.client.post("/api/patients", json={"name": "   \t  \n "})
        self.assertEqual(resp1.status_code, 400)

        # Missing name field entirely
        resp2 = self.client.post("/api/patients", json={"age": "50 years"})
        self.assertEqual(resp2.status_code, 422)  # Unprocessable entity by Pydantic

    def test_4_sequential_auto_id_generation_collision_safety(self):
        """4. Collision-safe unique ID auto-generation across multiple sequential patient creations."""
        patient_a = self.client.post("/api/patients", json={"name": "Patient Alpha"}).json()
        patient_b = self.client.post("/api/patients", json={"name": "Patient Beta"}).json()
        patient_c = self.client.post("/api/patients", json={"name": "Patient Gamma"}).json()

        self.assertEqual(patient_a["display_id"], "PULSE-DEMO-011")
        self.assertEqual(patient_b["display_id"], "PULSE-DEMO-012")
        self.assertEqual(patient_c["display_id"], "PULSE-DEMO-013")

    def test_5_rejection_of_duplicate_display_id(self):
        """5. Rejection of duplicate display_id submission returns 400 Bad Request."""
        # Existing seeded ID PULSE-DEMO-001
        resp = self.client.post("/api/patients", json={
            "display_id": "PULSE-DEMO-001",
            "name": "Duplicate Identifier Attemptee"
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("already exists", resp.json()["detail"])

    def test_6_retrieval_with_simulated_vitals(self):
        """6. Retrieval of newly created patient by display_id and primary key id includes simulated vitals."""
        created = self.client.post("/api/patients", json={"name": "George Miller"}).json()
        patient_id = created["id"]
        display_id = created["display_id"]

        # Fetch by display_id
        res_disp = self.client.get(f"/api/patients/{display_id}").json()
        self.assertEqual(res_disp["name"], "George Miller")
        self.assertIsNotNone(res_disp["vitals"])
        self.assertIn("hr", res_disp["vitals"])
        self.assertIn("spo2", res_disp["vitals"])

        # Fetch by primary key integer string
        res_pk = self.client.get(f"/api/patients/{patient_id}").json()
        self.assertEqual(res_pk["name"], "George Miller")
        self.assertEqual(res_pk["display_id"], display_id)

    def test_7_persistence_after_database_reconnection(self):
        """7. Persistence of new patient across database reconnection / re-instantiation."""
        created = self.client.post("/api/patients", json={
            "name": "Persistent Demo Patient",
            "ward": "Rehab Unit"
        }).json()
        disp_id = created["display_id"]

        # Re-open database from the same SQLite file
        reopened_db = Database(db_path=self.temp_db_path)
        persisted = reopened_db.get_patient(disp_id)
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted["name"], "Persistent Demo Patient")
        self.assertEqual(persisted["ward"], "Rehab Unit")

    def test_8_clinical_note_and_history_isolation(self):
        """8. New patient clinical notes and review history are completely isolated from existing patients."""
        # 1. Create new patient
        new_p = self.client.post("/api/patients", json={"name": "Isolated Patient"}).json()
        new_disp_id = new_p["display_id"]

        # 2. Add note for existing patient (Michael Wu PULSE-DEMO-001)
        wu_patient = self.test_db.get_patient("PULSE-DEMO-001")
        self.test_db.create_patient_note(
            patient_id=wu_patient["id"],
            raw_text="Michael Wu note.",
            author_identifier="Nurse A"
        )

        # 3. Add note for new patient
        self.test_db.create_patient_note(
            patient_id=new_p["id"],
            raw_text="Isolated patient proprietary handover note.",
            author_identifier="Nurse B"
        )

        # 4. Verify new patient's notes list
        new_p_notes = self.client.get(f"/api/patients/{new_disp_id}/notes").json()["notes"]
        self.assertEqual(len(new_p_notes), 1)
        self.assertEqual(new_p_notes[0]["raw_text"], "Isolated patient proprietary handover note.")

        # 5. Verify Michael Wu's notes list does NOT contain new patient's note
        wu_notes = self.client.get("/api/patients/PULSE-DEMO-001/notes").json()["notes"]
        for n in wu_notes:
            self.assertNotEqual(n["patient_id"], new_p["id"])
            self.assertNotIn("Isolated patient", n["raw_text"])

    def test_9_regression_all_original_seeded_patients_intact(self):
        """9. Regression verification: all 10 original synthetic seeded patients remain intact and unmodified."""
        # Create a new patient
        self.client.post("/api/patients", json={"name": "Twelfth Patient"})

        # Check seeded patients 1 through 10
        for i in range(1, 11):
            disp_id = f"PULSE-DEMO-{i:03d}"
            p = self.test_db.get_patient(disp_id)
            self.assertIsNotNone(p, f"Original seeded patient {disp_id} was lost!")
            self.assertIsNotNone(p["vitals"])
            self.assertIsNotNone(p["name"])


if __name__ == "__main__":
    unittest.main()
