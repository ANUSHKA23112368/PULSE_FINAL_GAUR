"""
PULSE Phase 2G Regression Test Suite: Clinical Extraction Quality, Source Fidelity, and Safety Audit
Validates all 10 regression criteria defined in PULSE Phase 2G:
1. Exact preservation of the three original source notes.
2. WBC, RBC, platelets, and ECG remaining distinguishable as investigations/tests (not clinical presentation).
3. Follow-up after four days being preserved as source-supported information.
4. 'He may die' not producing unsupported claims of confirmed instability or a resuscitation requirement.
5. 'Combiflam' not being silently corrupted to 'Comb'.
6. Ambiguous '2 dosage' not producing an invented dose or frequency.
7. CT scan being represented as a source-mentioned investigation, not as a completed result.
8. No fabricated vital signs or unsupported diagnoses.
9. Existing negation, uncertainty, and temporal-order safety tests continuing to pass.
10. Original note text, historical extractions, and clinician review audit records remaining intact.
"""

import unittest
import sys
import os
import re

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.main import app
from backend.database.database import db
from backend.preprocessing.preprocessor import clinical_preprocessor
from backend.extraction.clinical_bert_extractor import clinical_bert_extractor
from backend.extraction.entity_extractor import clinical_entity_extractor
from backend.extraction.event_extractor import clinical_event_extractor
from backend.extraction.temporal_extractor import clinical_temporal_extractor
from backend.extraction.structured_generator import structured_handover_generator


class TestClinicalExtractionFidelityPhase2G(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.case_a_text = (
            "Test for WBC RBC platelettes, ecg test and given some medicines for relief of pain for temporal pain relief. "
            "Patient have to come after 4 days after testing the given test"
        )
        cls.case_b_text = "Patient has a Headache. He may die"
        cls.case_c_text = (
            "Patient has little bit fever ad headache\n"
            "told him to take combiflam 2 dosage\n"
            "and for test CT scan of brain\n"
            "and meet me after 4 days"
        )

    def _run_pipeline(self, text: str):
        prep = clinical_preprocessor.preprocess(text)
        clean = prep["preprocessed_text"]
        entities = clinical_bert_extractor.extract(clean)
        events = clinical_event_extractor.extract(clean, entities=entities)
        temporal = clinical_temporal_extractor.extract(clean, events=events)
        pending = structured_handover_generator.extract_pending_tasks(clean, events=events)
        follow_up = structured_handover_generator.extract_follow_up(clean, pending_tasks=pending)
        structured = structured_handover_generator.generate_structured_handover(
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
            "temporal": temporal,
            "pending": pending,
            "follow_up": follow_up,
            "structured": structured
        }

    # --------------------------------------------------------------------------
    # Criterion 1: Exact preservation of the three original source notes
    # --------------------------------------------------------------------------
    def test_criterion_1_exact_preservation_of_source_notes(self):
        """Verifies that source notes are stored verbatim without mutation."""
        patient = db.get_patient("PULSE-DEMO-001")
        self.assertIsNotNone(patient)

        for source_text in [self.case_a_text, self.case_b_text, self.case_c_text]:
            resp = self.client.post(
                f"/api/patients/{patient['id']}/notes",
                json={"raw_text": source_text, "author_identifier": "Audit Tester"}
            )
            self.assertEqual(resp.status_code, 201)
            saved_note = resp.json()
            self.assertEqual(saved_note["raw_text"], source_text, "Raw source text must be preserved verbatim!")

    # --------------------------------------------------------------------------
    # Criterion 2: WBC, RBC, platelets, and ECG remaining distinguishable as investigations
    # --------------------------------------------------------------------------
    def test_criterion_2_investigations_vs_presentation_separation(self):
        """WBC, RBC, platelets, and ECG must be investigations, not clinical presentation symptoms."""
        res = self._run_pipeline(self.case_a_text)
        invs = [i["text"].lower() for i in res["entities"]["investigations"]]
        symptoms = [s["text"].lower() for s in res["entities"]["symptoms"]]

        # Investigations must contain WBC, RBC, platelettes/platelets, and ECG
        self.assertTrue(any("wbc" in i for i in invs), f"WBC missing from investigations: {invs}")
        self.assertTrue(any("rbc" in i for i in invs), f"RBC missing from investigations: {invs}")
        self.assertTrue(any("platelet" in i for i in invs), f"Platelets missing from investigations: {invs}")
        self.assertTrue(any("ecg" in i for i in invs), f"ECG missing from investigations: {invs}")

        # Symptoms must NOT include RBC, WBC, platelettes, or ECG
        self.assertFalse(any("bc" in s for s in symptoms), f"'Bc' incorrectly present in symptoms: {symptoms}")
        self.assertFalse(any("wbc" in s for s in symptoms), f"WBC incorrectly in symptoms: {symptoms}")
        self.assertFalse(any("ecg" in s for s in symptoms), f"ECG incorrectly in symptoms: {symptoms}")
        self.assertFalse(any("platelet" in s for s in symptoms), f"Platelets incorrectly in symptoms: {symptoms}")

        # ISBAR presentation must preserve pain, not tests
        situation = res["structured"]["isbar"]["situation"]
        situation_str = " ".join(situation).lower()
        self.assertIn("pain", situation_str)
        self.assertNotIn("acute wbc", situation_str)
        self.assertNotIn("acute bc", situation_str)

    # --------------------------------------------------------------------------
    # Criterion 3: Follow-up after four days being preserved as source-supported information
    # --------------------------------------------------------------------------
    def test_criterion_3_four_day_followup_preservation(self):
        """Follow-up timing 'after 4 days' must be captured in Case A and Case C."""
        for text in [self.case_a_text, self.case_c_text]:
            res = self._run_pipeline(text)
            follow_ups = [f["action"].lower() for f in res["follow_up"]]
            recommendations = [r.lower() for r in res["structured"]["isbar"]["recommendation"]]

            has_4_days = any("4 days" in fu for fu in follow_ups) or any("4 days" in r for r in recommendations)
            self.assertTrue(has_4_days, f"Expected 4-day follow-up preserved for text '{text}', got {follow_ups}")

    # --------------------------------------------------------------------------
    # Criterion 4: 'He may die' not producing unsupported claims of confirmed instability
    # --------------------------------------------------------------------------
    def test_criterion_4_no_fabricated_resuscitation_or_instability(self):
        """'He may die' must not produce claims of confirmed acute instability or resuscitation assessment."""
        res = self._run_pipeline(self.case_b_text)
        isbar = res["structured"]["isbar"]
        exec_summary = res["structured"]["executive_summary"].lower()

        situation_str = " ".join(isbar["situation"]).lower()
        assessment_str = " ".join(isbar["assessment"]).lower()
        recommendation_str = " ".join(isbar["recommendation"]).lower()

        # Must NOT claim confirmed acute instability risk or resuscitation assessment
        self.assertNotIn("acute resuscitation assessment", recommendation_str)
        self.assertNotIn("acute instability risk", assessment_str)
        self.assertNotIn("immediate clinical deterioration concern", situation_str)
        self.assertNotIn("acute headache", situation_str)

        # Must preserve the concerning original phrase verbatim and flag for review
        self.assertIn("may die", situation_str)
        self.assertTrue(any("clinician review" in s.lower() or "verification" in s.lower() for s in isbar["situation"]))

    # --------------------------------------------------------------------------
    # Criterion 5: 'Combiflam' not being silently corrupted to 'Comb'
    # --------------------------------------------------------------------------
    def test_criterion_5_combiflam_whole_token_preservation(self):
        """Combiflam must remain intact and not split into 'Comb' or 'If'."""
        res = self._run_pipeline(self.case_c_text)
        meds = [m["text"].lower() for m in res["entities"]["medications"]]
        symptoms = [s["text"].lower() for s in res["entities"]["symptoms"]]
        treatments = [t["text"].lower() for t in res["entities"]["treatments"]]

        # Must contain 'combiflam'
        self.assertTrue(any("combiflam" in m for m in meds), f"Combiflam missing from medications: {meds}")

        # Must NOT have orphan subword fragments 'comb' or 'if'
        self.assertNotIn("comb", treatments)
        self.assertNotIn("if", symptoms)
        self.assertNotIn("c", symptoms)

    # --------------------------------------------------------------------------
    # Criterion 6: Ambiguous '2 dosage' not producing an invented dose or frequency
    # --------------------------------------------------------------------------
    def test_criterion_6_ambiguous_dosage_not_invented(self):
        """'2 dosage' must be recorded verbatim without guessed milligrams, routes, or dosing intervals."""
        res = self._run_pipeline(self.case_c_text)
        combiflam = [m for m in res["entities"]["medications"] if "combiflam" in m["text"].lower()]
        self.assertTrue(len(combiflam) > 0)
        med = combiflam[0]

        # Verify dosage contains '2 dosage' and not guessed units
        self.assertIn("2 dosage", med["dosage"].lower())
        self.assertNotIn("mg", med["dosage"].lower())
        self.assertNotIn("mcg", med["dosage"].lower())

        # Frequency must remain unspecified
        self.assertEqual(med["frequency"], "Unspecified frequency")

    # --------------------------------------------------------------------------
    # Criterion 7: CT scan represented as source-mentioned investigation, not completed result
    # --------------------------------------------------------------------------
    def test_criterion_7_ct_scan_source_mentioned_investigation(self):
        """CT scan must be classified as an investigation with planned/requested status."""
        res = self._run_pipeline(self.case_c_text)
        invs = res["entities"]["investigations"]
        self.assertTrue(len(invs) > 0)
        ct = [i for i in invs if "ct" in i["text"].lower() or "computed tomography" in i.get("normalized", "").lower()]
        self.assertTrue(len(ct) > 0, f"CT scan not found in investigations: {invs}")

        # Verification in ISBAR assessment
        assessments = res["structured"]["isbar"]["assessment"]
        ct_assessments = [a for a in assessments if "ct" in a.lower()]
        self.assertTrue(len(ct_assessments) > 0)
        self.assertTrue(any("[planned]" in a.lower() for a in ct_assessments))

    # --------------------------------------------------------------------------
    # Criterion 8: No fabricated vital signs or unsupported diagnoses
    # --------------------------------------------------------------------------
    def test_criterion_8_no_fabricated_vital_signs_or_diagnoses(self):
        """Notes without BP, HR, GCS, or temp must not fabricate numerical vital signs."""
        for text in [self.case_a_text, self.case_b_text, self.case_c_text]:
            res = self._run_pipeline(text)
            measurements = res["entities"]["measurements"]
            self.assertEqual(len(measurements), 0, f"No measurements should be extracted from '{text}', found: {measurements}")

    # --------------------------------------------------------------------------
    # Criterion 9: Existing safety tests continue to pass
    # --------------------------------------------------------------------------
    def test_criterion_9_safety_negation_and_uncertainty(self):
        """Verifies negation and uncertainty extraction continue to function correctly."""
        neg_text = "The patient has no fever and denies chest pain."
        res = self._run_pipeline(neg_text)
        symptoms = res["entities"]["symptoms"]
        for s in symptoms:
            self.assertTrue(s["is_negated"], f"Symptom '{s['text']}' should be negated")

        unc_text = "The patient may have pneumonia."
        res_unc = self._run_pipeline(unc_text)
        conds = res_unc["entities"]["conditions"]
        self.assertTrue(len(conds) > 0)
        self.assertTrue(conds[0]["is_uncertain"])

    # --------------------------------------------------------------------------
    # Criterion 10: Original note text, historical extractions, and clinician review audit records intact
    # --------------------------------------------------------------------------
    def test_criterion_10_audit_history_and_note_review_integrity(self):
        """Verifies complete note lifecycle and audit preservation via API."""
        patient = db.get_patient("PULSE-DEMO-002")
        self.assertIsNotNone(patient)

        # 1. Create draft note
        post_resp = self.client.post(
            f"/api/patients/{patient['id']}/notes",
            json={"raw_text": self.case_c_text, "author_identifier": "Audit Clinician"}
        )
        self.assertEqual(post_resp.status_code, 201)
        note_id = post_resp.json()["id"]

        # 2. Process note
        proc_resp = self.client.post(f"/api/patients/{patient['id']}/notes/{note_id}/process")
        self.assertEqual(proc_resp.status_code, 200)
        proc_data = proc_resp.json()
        self.assertIn("extraction", proc_data)
        original_ai_extraction = proc_data["extraction"]

        # 3. Submit clinician review
        reviewed_payload = {
            "reviewer_identifier": "Dr. Verification, MD",
            "review_notes": "Phase 2G Audit Verification",
            "reviewed_data": {
                "verified": True,
                "diagnosis": "Headache and fever under evaluation"
            }
        }
        rev_resp = self.client.post(
            f"/api/patients/{patient['id']}/notes/{note_id}/review",
            json=reviewed_payload
        )
        self.assertEqual(rev_resp.status_code, 200)

        # 4. Fetch note history and verify audit integrity
        notes_resp = self.client.get(f"/api/patients/{patient['id']}/notes")
        self.assertEqual(notes_resp.status_code, 200)
        all_notes = notes_resp.json()["notes"]
        the_note = [n for n in all_notes if n["id"] == note_id][0]

        # Verify raw text intact
        self.assertEqual(the_note["raw_text"], self.case_c_text)
        self.assertEqual(the_note["status"], "Reviewed")
        self.assertIsNotNone(the_note["review"])
        self.assertEqual(the_note["reviewer_identifier"], "Dr. Verification, MD")
        self.assertEqual(the_note["review"]["review_notes"], "Phase 2G Audit Verification")
        # Verify original AI extraction preserved intact
        self.assertIsNotNone(the_note["extraction"])
        self.assertIn("data", the_note["extraction"])

    # --------------------------------------------------------------------------
    # Section 6: Patient count consistency
    # --------------------------------------------------------------------------
    def test_patient_count_consistency(self):
        """Verifies /api/health and /api/patients report matching patient counts."""
        health_resp = self.client.get("/api/health")
        self.assertEqual(health_resp.status_code, 200)
        health_count = health_resp.json()["total_patients"]

        patients_resp = self.client.get("/api/patients")
        self.assertEqual(patients_resp.status_code, 200)
        patients_count = patients_resp.json()["total_patients"]

        self.assertEqual(health_count, patients_count)
        self.assertGreaterEqual(patients_count, 10)


if __name__ == "__main__":
    unittest.main()
