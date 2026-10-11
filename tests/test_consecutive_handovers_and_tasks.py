"""
Tests for PULSE Consecutive Handover Tracking ("What Changed?"),
Persistent Pending Actions, and Research Evaluation API.
Validates the exact clinical scenario for Rahul (55 yo):
- Morning Handover Note (Temp 102°F, Paracetamol 8 AM, Blood pending, Recheck 12 PM)
- Evening Handover Note (Temp 100°F at 12 PM, Blood received, Doctor reviewed, Cough persists)
"""

import unittest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database.database import db

class TestConsecutiveHandoversAndTasks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Create a dedicated synthetic patient for this test
        cls.patient_payload = {
            "name": "Rahul Test Patient",
            "age": "55 years",
            "gender": "Male",
            "ward": "General Medicine",
            "bed_number": "Bed 7",
            "consultant": "Dr. Khurana",
            "admitting_diagnosis": "Fever and cough"
        }
        res = cls.client.post("/api/patients", json=cls.patient_payload)
        assert res.status_code in (200, 201), res.text
        cls.patient = res.json()
        cls.patient_id = cls.patient["id"]

    def test_1_create_and_process_consecutive_shift_notes(self):
        """
        1. Test entering and processing Morning Shift note and Evening Shift note for Rahul.
        """
        # Morning Note
        morning_text = "Rahul, 55 years old, admitted with fever and cough. Temperature was 102°F in the morning. Paracetamol given at 8 AM. Blood test report is pending. Patient's temperature should be checked again at 12 PM."
        m_res = self.client.post(
            f"/api/patients/{self.patient_id}/notes",
            json={"raw_text": morning_text, "author_identifier": "Morning Nurse (8 AM)"}
        )
        self.assertIn(m_res.status_code, (200, 201))
        morning_note = m_res.json()

        # Process Morning Note
        m_proc = self.client.post(f"/api/patients/{self.patient_id}/notes/{morning_note['id']}/process")
        self.assertEqual(m_proc.status_code, 200)
        m_data = m_proc.json()
        self.assertEqual(m_data["status"], "Processed")

        # Evening Note
        evening_text = "At 12 PM, Rahul's temperature was 100°F. Blood report received. Doctor reviewed the report and advised continued monitoring. Patient's cough persists."
        e_res = self.client.post(
            f"/api/patients/{self.patient_id}/notes",
            json={"raw_text": evening_text, "author_identifier": "Evening Nurse (12:30 PM)"}
        )
        self.assertIn(e_res.status_code, (200, 201))
        evening_note = e_res.json()

        # Process Evening Note
        e_proc = self.client.post(f"/api/patients/{self.patient_id}/notes/{evening_note['id']}/process")
        self.assertEqual(e_proc.status_code, 200)
        e_data = e_proc.json()
        self.assertEqual(e_data["status"], "Processed")

    def test_2_what_changed_consecutive_handover_comparison(self):
        """
        2. Test consecutive handover comparison identifying observation changes,
           lab updates, task completions, and ongoing symptoms with sentence attribution.
        """
        res = self.client.get(f"/api/patients/{self.patient_id}/compare-handovers")
        self.assertEqual(res.status_code, 200)
        comp = res.json()

        self.assertTrue(comp["comparison_available"])

        # 1. Temperature observation delta
        obs = comp["observations_changed"]
        self.assertGreaterEqual(len(obs), 1)
        temp_change = obs[0]
        self.assertIn("102", temp_change["prior_value"])
        self.assertIn("100", temp_change["current_value"])
        self.assertEqual(temp_change["direction"], "Decreased")
        self.assertIn("Temperature was 102°F", temp_change["prior_sentence"])
        self.assertIn("temperature was 100°F", temp_change["current_sentence"])
        self.assertIn("Clinical Safety Precaution", temp_change["clinical_caution"])

        # 2. Lab updates (Blood test Pending -> Received)
        inv = comp["investigations_updated"]
        self.assertGreaterEqual(len(inv), 1)
        blood_update = inv[0]
        self.assertEqual(blood_update["prior_status"], "Pending")
        self.assertEqual(blood_update["current_status"], "Received / Documented")
        self.assertIn("Blood test report is pending", blood_update["prior_sentence"])
        self.assertIn("Blood report received", blood_update["current_sentence"])

        # 3. Tasks progressed
        tasks = comp["tasks_progressed"]
        self.assertGreaterEqual(len(tasks), 1)
        self.assertIn("temperature", tasks[0]["task"].lower())
        self.assertEqual(tasks[0]["prior_status"], "Planned / Due")
        self.assertEqual(tasks[0]["current_status"], "Completed / Documented")

        # 4. Ongoing conditions
        ongoing = comp["ongoing_conditions"]
        self.assertGreaterEqual(len(ongoing), 1)
        self.assertEqual(ongoing[0]["condition"], "Cough")
        self.assertEqual(ongoing[0]["status"], "Persisting")
        self.assertIn("cough persists", ongoing[0]["current_sentence"].lower())

        # 5. New Directives
        directives = comp["new_directives"]
        self.assertGreaterEqual(len(directives), 1)
        self.assertIn("Doctor reviewed", directives[0]["directive"])

    def test_3_pending_actions_persistence_and_update(self):
        """
        3. Test persistent pending tasks creation, listing, status transitions, and audit.
        """
        # Create a task
        task_payload = {
            "task": "Repeat troponin at 06:00",
            "type": "Diagnostic Investigation Recheck",
            "priority": "High",
            "due_time": "06:00 AM",
            "source_sentence": "Repeat troponin ordered for 0600.",
            "status": "Pending"
        }
        create_res = self.client.post(f"/api/patients/{self.patient_id}/tasks", json=task_payload)
        self.assertEqual(create_res.status_code, 200)
        task = create_res.json()
        self.assertEqual(task["status"], "Pending")
        self.assertEqual(task["task"], "Repeat troponin at 06:00")
        task_id = task["id"]

        # List tasks
        list_res = self.client.get(f"/api/patients/{self.patient_id}/tasks")
        self.assertEqual(list_res.status_code, 200)
        data = list_res.json()
        self.assertGreaterEqual(data["total_tasks"], 1)

        # Update status to Completed with evidence
        update_payload = {
            "status": "Completed",
            "evidence": "Troponin sample collected and dispatched to lab at 06:05 AM"
        }
        patch_res = self.client.patch(f"/api/patients/{self.patient_id}/tasks/{task_id}", json=update_payload)
        self.assertEqual(patch_res.status_code, 200)
        updated = patch_res.json()
        self.assertEqual(updated["status"], "Completed")
        self.assertIn("dispatched to lab", updated["evidence"])

    def test_4_research_evaluation_metrics(self):
        """
        4. Test research evaluation endpoint returns live counts and reference benchmark metrics
           without fabricated accuracy claims.
        """
        res = self.client.get("/api/research/evaluation")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertIn("corpus", data)
        self.assertEqual(data["corpus"]["total_reference_documents"], 101)
        self.assertIn("live_prototype_activity", data)
        self.assertGreaterEqual(data["live_prototype_activity"]["registered_demo_patients"], 1)
        self.assertIn("benchmark_metrics", data)
        self.assertGreaterEqual(len(data["benchmark_metrics"]), 4)
        for cat in data["benchmark_metrics"]:
            self.assertIn("precision", cat)
            self.assertIn("recall", cat)
            self.assertIn("f1", cat)

if __name__ == "__main__":
    unittest.main()
