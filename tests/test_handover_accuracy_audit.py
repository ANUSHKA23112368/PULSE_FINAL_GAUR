"""
PULSE Phase 2: Critical Extraction Safety Regression Test Suite (P0)
Focuses strictly on:
1. Decimal and gram dosage extraction fidelity (e.g., '0.25 mg' must never extract as '25 mg', '1g' preserved).
2. Localized medication attribute binding (attributes like frequency/dose do not leak across drugs in the same sentence).
3. Prevention of unsupported symptom acuity leakage (e.g., 'acute ward' must never modify 'headache' into 'Acute Headache').
"""

import unittest
import sys
import os

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.preprocessing.preprocessor import clinical_preprocessor
from backend.extraction.entity_extractor import clinical_entity_extractor
from backend.extraction.event_extractor import clinical_event_extractor
from backend.extraction.temporal_extractor import clinical_temporal_extractor
from backend.extraction.structured_generator import structured_handover_generator
from backend.database.database import db


class TestHandoverAccuracyAuditP0(unittest.TestCase):
    def setUp(self):
        self.preprocessor = clinical_preprocessor
        self.extractor = clinical_entity_extractor
        self.generator = structured_handover_generator

    def _run_pipeline(self, text: str):
        prep = self.preprocessor.preprocess(text)
        clean = prep["preprocessed_text"]
        entities = self.extractor.extract(clean)
        events = clinical_event_extractor.extract(clean, entities=entities)
        temporal = clinical_temporal_extractor.extract(clean, events=events)
        pending = self.generator.extract_pending_tasks(clean, events=events)
        follow_up = self.generator.extract_follow_up(clean, pending_tasks=pending)
        structured = self.generator.generate_structured_handover(
            text=clean,
            entities=entities,
            events=events,
            temporal_info=temporal,
            pending_tasks=pending,
            follow_up=follow_up
        )
        return {
            "clean_text": clean,
            "entities": entities,
            "events": events,
            "pending_tasks": pending,
            "follow_up": follow_up,
            "structured": structured
        }

    # ==========================================================================
    # 1. Decimal & Gram Dosage Tests
    # ==========================================================================

    def test_digoxin_decimal_dosage_preservation(self):
        """
        'Digoxin 0.25 mg mane' must preserve '0.25 mg' exactly.
        Must never extract '25 mg' or 'Unspecified dose'.
        """
        text = "Administered Digoxin 0.25 mg mane."
        res = self._run_pipeline(text)
        meds = res["entities"]["medications"]

        digoxin_matches = [m for m in meds if "digoxin" in m.get("text", "").lower() or "digoxin" in m.get("normalized", "").lower()]
        self.assertTrue(len(digoxin_matches) > 0, f"Expected Digoxin to be extracted from '{text}', but got {meds}")

        dig_med = digoxin_matches[0]
        self.assertEqual(dig_med.get("dosage"), "0.25 mg", f"Expected exact dosage '0.25 mg', got '{dig_med.get('dosage')}'")
        self.assertNotEqual(dig_med.get("dosage"), "25 mg", "CRITICAL ERROR: '0.25 mg' was corrupted to '25 mg' (100x overdose error)")

    def test_paracetamol_gram_dosage_and_route(self):
        """
        'Paracetamol 1g PO' must preserve the dose '1g' and route 'PO'.
        Must not result in 'Unspecified dose in text'.
        """
        text = "Patient was febrile, given paracetamol 1g PO at 15:30."
        res = self._run_pipeline(text)
        meds = res["entities"]["medications"]

        pcm_matches = [m for m in meds if "paracetamol" in m.get("text", "").lower() or "paracetamol" in m.get("normalized", "").lower()]
        self.assertTrue(len(pcm_matches) > 0, f"Expected Paracetamol to be extracted from '{text}', but got {meds}")

        pcm_med = pcm_matches[0]
        dose_lower = pcm_med.get("dosage", "").lower()
        self.assertIn("1g", dose_lower.replace(" ", ""), f"Expected dosage '1g' or '1 g', got '{pcm_med.get('dosage')}'")
        self.assertEqual(pcm_med.get("route"), "PO", f"Expected route 'PO', got '{pcm_med.get('route')}'")

    def test_arbitrary_decimal_and_integer_doses_no_truncation(self):
        """
        Valid decimal and integer doses (e.g. 12.5 mg, 0.5 ml, 100 mg) must be preserved accurately.
        """
        text = "Started on Metoprolol 12.5 mg mane and Aspirin 100 mg daily."
        res = self._run_pipeline(text)
        meds = res["entities"]["medications"]

        metoprolol = next((m for m in meds if "metoprolol" in m.get("text", "").lower()), None)
        aspirin = next((m for m in meds if "aspirin" in m.get("text", "").lower()), None)

        self.assertIsNotNone(metoprolol, f"Metoprolol not found in {meds}")
        self.assertIsNotNone(aspirin, f"Aspirin not found in {meds}")

        self.assertEqual(metoprolol.get("dosage"), "12.5 mg")
        self.assertNotEqual(metoprolol.get("dosage"), "5 mg")
        self.assertEqual(aspirin.get("dosage"), "100 mg")

    # ==========================================================================
    # 2. Medication Attribute Binding Tests
    # ==========================================================================

    def test_multi_medication_attribute_binding_no_leakage(self):
        """
        For 'Digoxin 0.25mg mane and Metoprolol 25mg BD', attributes must bind locally:
        - Digoxin -> 0.25mg, frequency MANE
        - Metoprolol -> 25mg, frequency BD
        Frequencies and doses must not bleed across medications.
        """
        text = "Started on Digoxin 0.25mg mane and Metoprolol 25mg BD."
        res = self._run_pipeline(text)
        meds = res["entities"]["medications"]

        digoxin = next((m for m in meds if "digoxin" in m.get("text", "").lower() or "digoxin" in m.get("normalized", "").lower()), None)
        metoprolol = next((m for m in meds if "metoprolol" in m.get("text", "").lower()), None)

        self.assertIsNotNone(digoxin, f"Digoxin missing from {meds}")
        self.assertIsNotNone(metoprolol, f"Metoprolol missing from {meds}")

        # Check Digoxin
        self.assertEqual(digoxin.get("dosage"), "0.25mg")
        self.assertEqual(digoxin.get("frequency"), "MANE")
        self.assertNotEqual(digoxin.get("frequency"), "BD", "Digoxin incorrectly inherited Metoprolol's frequency 'BD'")

        # Check Metoprolol
        self.assertEqual(metoprolol.get("dosage"), "25mg")
        self.assertEqual(metoprolol.get("frequency"), "BD")
        self.assertNotEqual(metoprolol.get("frequency"), "MANE", "CRITICAL ERROR: Metoprolol incorrectly inherited Digoxin's frequency 'MANE'")

    # ==========================================================================
    # 3. Acuity Leakage Tests
    # ==========================================================================

    def test_no_acuity_leakage_from_acute_ward(self):
        """
        'Patient admitted to acute ward with headache.' must not produce 'Acute Headache'.
        The word 'acute' elsewhere in the note must not modify a symptom's acuity.
        """
        text = "Patient admitted to acute ward with headache."
        res = self._run_pipeline(text)
        structured = res["structured"]
        situation_text = " ".join(structured.get("isbar", {}).get("situation", [])).lower()
        current_condition = " ".join(structured.get("current_condition", [])).lower()

        self.assertNotIn("acute headache", situation_text, f"Unsupported acuity detected in situation: '{situation_text}'")
        self.assertNotIn("acute symptom: headache", current_condition, f"Unsupported acuity detected in current_condition: '{current_condition}'")
        self.assertIn("headache", situation_text)

    def test_preserve_explicit_acute_headache_when_documented(self):
        """
        When the symptom itself is explicitly documented as 'acute headache', acuity is preserved.
        """
        text = "Patient presented with acute headache."
        res = self._run_pipeline(text)
        structured = res["structured"]
        situation_text = " ".join(structured.get("isbar", {}).get("situation", [])).lower()

        self.assertIn("acute headache", situation_text)

    # ==========================================================================
    # 4. Investigation Status and Pending Action Extraction Tests (Phase 3)
    # ==========================================================================

    def test_ct_head_is_pending_creates_pending_task_and_status(self):
        """
        'CT head is pending.' -> Investigation: CT head; status: Pending;
        corresponding pending action created; priority must not be unsupported 'High'.
        """
        text = "CT head is pending."
        res = self._run_pipeline(text)
        invs = res["entities"]["investigations"]
        pending_tasks = res["pending_tasks"]

        # 1. Investigation recognized with documented status
        ct_inv = next((i for i in invs if "ct" in i.get("text", "").lower() or "ct" in i.get("normalized", "").lower()), None)
        self.assertIsNotNone(ct_inv, f"CT head missing from investigations: {invs}")
        self.assertEqual(ct_inv.get("status", "").lower(), "pending", f"Expected status 'Pending', got '{ct_inv.get('status')}'")

        # 2. Corresponding pending action created
        ct_tasks = [t for t in pending_tasks if "ct" in t.get("task", "").lower()]
        self.assertTrue(len(ct_tasks) > 0, f"Expected pending task for CT head, got {pending_tasks}")
        task = ct_tasks[0]
        self.assertEqual(task.get("status"), "Pending")
        # Priority must not be hardcoded High Priority without clinical trigger
        self.assertNotEqual(task.get("priority"), "High", "CT head should not be assigned High Priority without clinical justification")

    def test_awaiting_blood_culture_results(self):
        """
        'Awaiting blood culture results.' -> Blood culture results: Awaiting results.
        """
        text = "Awaiting blood culture results."
        res = self._run_pipeline(text)
        invs = res["entities"]["investigations"]

        bc_inv = next((i for i in invs if "blood culture" in i.get("text", "").lower() or "pathology" in i.get("normalized", "").lower()), None)
        self.assertIsNotNone(bc_inv, f"Blood cultures missing from investigations: {invs}")
        self.assertEqual(bc_inv.get("status", "").lower(), "awaiting results", f"Expected status 'Awaiting results', got '{bc_inv.get('status')}'")

    def test_blood_cultures_sent_not_labeled_as_results_available(self):
        """
        'Blood cultures sent.' -> Blood cultures: Sent; do not label results as available or completed.
        """
        text = "Blood cultures sent."
        res = self._run_pipeline(text)
        invs = res["entities"]["investigations"]

        bc_inv = next((i for i in invs if "blood culture" in i.get("text", "").lower() or "pathology" in i.get("normalized", "").lower()), None)
        self.assertIsNotNone(bc_inv, f"Blood cultures missing from investigations: {invs}")
        self.assertEqual(bc_inv.get("status", "").lower(), "sent", f"Expected status 'Sent', got '{bc_inv.get('status')}'")
        self.assertNotEqual(bc_inv.get("status", "").lower(), "completed")
        self.assertNotEqual(bc_inv.get("status", "").lower(), "available")

    def test_ct_head_completed_only_when_explicitly_documented(self):
        """
        'CT head completed.' -> Completed only when explicitly documented.
        """
        text = "CT head completed."
        res = self._run_pipeline(text)
        invs = res["entities"]["investigations"]

        ct_inv = next((i for i in invs if "ct" in i.get("text", "").lower() or "ct" in i.get("normalized", "").lower()), None)
        self.assertIsNotNone(ct_inv, f"CT head missing from investigations: {invs}")
        self.assertEqual(ct_inv.get("status", "").lower(), "completed", f"Expected status 'Completed', got '{ct_inv.get('status')}'")

    def test_neurology_review_planned_for_morning(self):
        """
        'Neurology review planned for morning.' -> Action: Neurology review; timing: morning; status: Planned/Pending.
        Must not truncate action to 'Planned for morning'. Priority must not be unsupported 'High'.
        """
        text = "Neurology review planned for morning."
        res = self._run_pipeline(text)
        pending_tasks = res["pending_tasks"]
        follow_ups = res["follow_up"]

        all_actions = pending_tasks + follow_ups
        neuro_action = next((a for a in all_actions if "neurology review" in a.get("task", "").lower() or "neurology review" in a.get("action", "").lower()), None)

        self.assertIsNotNone(neuro_action, f"Expected action containing 'Neurology review', got {all_actions}")
        action_text = neuro_action.get("task") or neuro_action.get("action")
        self.assertNotIn(action_text.lower(), ["planned for morning", "morning"], "Action was truncated to 'Planned for morning'")
        self.assertIn("neurology review", action_text.lower())

        # Timing must capture morning
        timing_str = (neuro_action.get("timing") or neuro_action.get("time") or neuro_action.get("due_time") or action_text).lower()
        self.assertIn("morning", timing_str)

        # Status must be Planned or Pending
        status = neuro_action.get("status", "Pending")
        self.assertIn(status.lower(), ["planned", "pending", "planned / pending"])

        # Priority must not be blindly High
        self.assertNotEqual(neuro_action.get("priority"), "High", "Generic 'review' word must not automatically assign High Priority")

    def test_no_ct_scan_ordered_does_not_create_pending_task(self):
        """
        'No CT scan has been ordered.' -> Must not create a pending CT task.
        """
        text = "No CT scan has been ordered."
        res = self._run_pipeline(text)
        invs = res["entities"]["investigations"]
        pending_tasks = res["pending_tasks"]

        # Negation preserved
        ct_inv = next((i for i in invs if "ct" in i.get("text", "").lower() or "ct" in i.get("normalized", "").lower()), None)
        if ct_inv:
            self.assertTrue(ct_inv.get("is_negated"), "Expected CT scan to be marked as negated")

        # Must NOT create a pending task
        ct_tasks = [t for t in pending_tasks if "ct" in t.get("task", "").lower()]
        self.assertEqual(len(ct_tasks), 0, f"Negated CT scan incorrectly created pending task: {ct_tasks}")

    def test_investigation_without_status_not_marked_pending_or_completed(self):
        """
        A note that does not mention an investigation's status must not automatically mark it pending or completed.
        """
        text = "Patient has a history of previous CT scan in 2021."
        res = self._run_pipeline(text)
        invs = res["entities"]["investigations"]
        pending_tasks = res["pending_tasks"]

        ct_inv = next((i for i in invs if "ct" in i.get("text", "").lower() or "ct" in i.get("normalized", "").lower()), None)
        self.assertIsNotNone(ct_inv, f"CT scan missing from investigations: {invs}")
        status = ct_inv.get("status", "").lower()
        self.assertNotIn(status, ["pending", "completed", "awaiting results"], f"Status was prematurely inferred as '{status}'")

        # Must not create pending tasks
        ct_tasks = [t for t in pending_tasks if "ct" in t.get("task", "").lower()]
        self.assertEqual(len(ct_tasks), 0, f"Unstated status incorrectly created pending task: {ct_tasks}")

    def test_duplicate_pending_task_prevention_and_history_preservation(self):
        """
        Consecutive notes with the same pending task must not create duplicate active pending tasks,
        and task history must be preserved.
        """
        patient = db.create_patient({
            "name": "Audit Task Deduplication Patient",
            "age": "60 years",
            "gender": "Male",
            "ward": "Neurology"
        })
        p_id = patient["id"]

        # First note generates a pending task
        t1 = db.create_patient_task(p_id, {
            "task": "CT head is pending",
            "type": "Pending Diagnostic Investigation",
            "source_sentence": "CT head is pending.",
            "source_note_id": 101,
            "status": "Pending"
        })

        # Second consecutive note also mentions the same pending task
        t2 = db.create_patient_task(p_id, {
            "task": "CT head is pending",
            "type": "Pending Diagnostic Investigation",
            "source_sentence": "CT head is pending.",
            "source_note_id": 102,
            "status": "Pending"
        })

        # Must return the existing pending task and NOT create a duplicate row
        self.assertEqual(t1["id"], t2["id"], "Duplicate pending task row was created for identical pending action")

        all_tasks = db.list_patient_tasks(p_id)
        active_pending = [t for t in all_tasks if t["task"] == "CT head is pending" and t["status"] == "Pending"]
        self.assertEqual(len(active_pending), 1, "Expected exactly 1 active pending task row")

        # Now complete the task
        db.update_patient_task(p_id, t1["id"], "Completed", evidence="CT head scan completed at 14:00")

        # If a new order is made later, history is preserved and a new task can be tracked
        t3 = db.create_patient_task(p_id, {
            "task": "CT head is pending",
            "type": "Pending Diagnostic Investigation",
            "source_sentence": "Repeat CT head is pending.",
            "source_note_id": 103,
            "status": "Pending"
        })
        self.assertNotEqual(t1["id"], t3["id"], "New task after completion should be permitted")

        tasks_after = db.list_patient_tasks(p_id)
        self.assertEqual(len(tasks_after), 2, "Task history must preserve both completed and new pending tasks")

    def test_unassigned_awaiting_clinician_triage_priority_policy(self):
        """
        When no validated priority policy or explicit urgency is present, tasks must be assigned
        'Unassigned / Awaiting Clinician Triage', avoiding unsupported High or arbitrary priorities.
        """
        text = "Neurology review planned for morning."
        res = self._run_pipeline(text)
        pending_tasks = res["pending_tasks"]
        self.assertTrue(len(pending_tasks) > 0)
        self.assertEqual(pending_tasks[0]["priority"], "Unassigned / Awaiting Clinician Triage")

        # When explicit urgency IS present, High priority is allowed
        urgent_text = "Urgent neurology review planned for morning."
        res_urgent = self._run_pipeline(urgent_text)
        urgent_tasks = res_urgent["pending_tasks"]
        self.assertTrue(len(urgent_tasks) > 0)
        self.assertEqual(urgent_tasks[0]["priority"], "High")


if __name__ == "__main__":
    unittest.main()
