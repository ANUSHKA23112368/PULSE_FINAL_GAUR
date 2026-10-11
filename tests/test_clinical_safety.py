"""
PULSE Clinical Safety & Assertion Test Suite
Automated regression tests verifying:
1. Assertion scoping (Negation, Uncertainty/Hedging, Affirmative)
2. Temporality analysis (Current, Historical, Planned)
3. Elimination of fabricated clinical defaults (no false stability claims)
4. Protection against false-positive clinical safety alerts
5. Medical abbreviation sentence preservation
"""

import unittest
import sys
import os

# Ensure repository root is on Python sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.preprocessing.preprocessor import clinical_preprocessor
from backend.extraction.context_extractor import clinical_context_extractor
from backend.extraction.entity_extractor import clinical_entity_extractor
from backend.extraction.event_extractor import clinical_event_extractor
from backend.extraction.temporal_extractor import clinical_temporal_extractor
from backend.extraction.structured_generator import structured_handover_generator


class TestPULSEClinicalSafety(unittest.TestCase):

    def run_full_pipeline(self, raw_text: str):
        prep = clinical_preprocessor.preprocess(raw_text)
        clean_text = prep["preprocessed_text"]
        entities = clinical_entity_extractor.extract(clean_text)
        events = clinical_event_extractor.extract(clean_text, entities=entities)
        temporal = clinical_temporal_extractor.extract(clean_text, events=events)
        pending = structured_handover_generator.extract_pending_tasks(clean_text, events=events)
        follow_up = structured_handover_generator.extract_follow_up(clean_text, pending_tasks=pending)
        structured = structured_handover_generator.generate_structured_handover(
            text=clean_text,
            entities=entities,
            events=events,
            temporal_info=temporal,
            pending_tasks=pending,
            follow_up=follow_up
        )
        return {
            "clean_text": clean_text,
            "entities": entities,
            "events": events,
            "temporal": temporal,
            "pending": pending,
            "follow_up": follow_up,
            "structured": structured
        }

    def test_case_a_acute_deterioration_without_false_stability(self):
        """
        Case A: 'The patient has a headache. He may die.'
        Safety requirement:
        - Must recognize acute headache.
        - Must NOT append 'with no acute deterioration noted' or claim stability.
        - Must emit urgent clinical deterioration alert.
        """
        text = "The patient has a headache. He may die."
        res = self.run_full_pipeline(text)
        structured = res["structured"]
        exec_summary = structured.get("executive_summary", "")
        situation = structured.get("isbar", {}).get("situation", [])

        # Verify headache extracted
        symptoms = [s["normalized"] for s in res["entities"]["symptoms"]]
        self.assertIn("Headache (Cephalgia)", symptoms)

        # Verify NO fabricated stability claims
        self.assertNotIn("no acute deterioration noted", exec_summary.lower())
        self.assertNotIn("patient stable under routine", exec_summary.lower())

        # Verify acute alert presence
        self.assertTrue(
            any("critical alert" in exec_summary.lower() or "deterioration" in exec_summary.lower() for _ in [1])
        )
        self.assertTrue(
            any("CRITICAL" in s for s in situation)
        )

    def test_case_b_denied_chest_pain_no_false_alarm(self):
        """
        Case B: 'The patient denies chest pain.'
        Safety requirement:
        - Must extract chest pain as Negated.
        - Must NOT fire Cardiovascular / Ischemic Alert.
        - Must classify under pertinent negatives / denied findings, NOT acute symptoms.
        - Executive summary must NOT state admission is for chest pain management.
        """
        text = "The patient denies chest pain."
        res = self.run_full_pipeline(text)
        symptoms = res["entities"]["symptoms"]
        risks = res["entities"]["clinical_risks"]
        structured = res["structured"]

        # Verify negation detected
        self.assertTrue(len(symptoms) > 0)
        for s in symptoms:
            self.assertEqual(s["assertion"], "Negated")
            self.assertTrue(s["is_negated"])

        # Verify Cardiovascular Alert DID NOT fire
        cardiac_risks = [r for r in risks if "Cardiovascular" in r.get("risk_type", "")]
        self.assertEqual(len(cardiac_risks), 0, "Cardiovascular alert must NOT fire when chest pain is denied!")

        # Verify categorized as Pertinent Negative
        current_cond = structured.get("current_condition", [])
        self.assertTrue(
            any("Pertinent Negative" in c or "Denied" in c for c in current_cond),
            f"Expected Pertinent Negative in current condition, got: {current_cond}"
        )
        self.assertFalse(
            any("Acute Symptom: Chest Pain" in c for c in current_cond),
            "Denied chest pain must not appear as an Acute Symptom!"
        )

        # Verify Executive summary reflects exclusion
        exec_summary = structured.get("executive_summary", "")
        self.assertNotIn("admitted for management of Chest Pain", exec_summary)

    def test_case_c_negated_fever_symptom_exclusion(self):
        """
        Case C: 'The patient has no fever.'
        Safety requirement:
        - Must recognize 'no fever' as Negated finding.
        - Must not create acute fever symptom.
        """
        text = "The patient has no fever."
        res = self.run_full_pipeline(text)
        symptoms = res["entities"]["symptoms"]
        structured = res["structured"]

        self.assertTrue(len(symptoms) > 0)
        fever = [s for s in symptoms if "fever" in s["text"].lower()][0]
        self.assertTrue(fever["is_negated"])
        self.assertEqual(fever["assertion"], "Negated")

        current_cond = structured.get("current_condition", [])
        self.assertTrue(any("Pertinent Negative" in c for c in current_cond))
        self.assertFalse(any("Acute Symptom: Febrile" in c for c in current_cond))

    def test_case_d_historical_chest_pain_with_current_resolution(self):
        """
        Case D: 'The patient had chest pain yesterday but is pain-free now.'
        Safety requirement:
        - 'chest pain' must be classified as Historical.
        - 'pain-free' must be classified as Negated.
        - Must NOT fire acute Cardiovascular Alert for resolved historical episode.
        - Must place historical episode in past shift / history, not current acute symptom.
        """
        text = "The patient had chest pain yesterday but is pain-free now."
        res = self.run_full_pipeline(text)
        symptoms = res["entities"]["symptoms"]
        risks = res["entities"]["clinical_risks"]
        structured = res["structured"]

        # Check temporality and assertion
        hist_pain = [s for s in symptoms if s["is_historical"]]
        neg_pain = [s for s in symptoms if s["is_negated"]]
        self.assertTrue(len(hist_pain) > 0, "Expected historical chest pain span")
        self.assertTrue(len(neg_pain) > 0, "Expected negated/pain-free span")

        # Verify acute cardiac risk alert does NOT fire
        cardiac_risks = [r for r in risks if "Cardiovascular" in r.get("risk_type", "")]
        self.assertEqual(len(cardiac_risks), 0, "Cardiovascular alert must NOT fire for resolved historical pain!")

        # Verify current condition lists past shift episode
        current_cond = structured.get("current_condition", [])
        self.assertTrue(any("Past Shift Episode (Resolved)" in c for c in current_cond))

    def test_case_e_scheduled_investigation_and_task(self):
        """
        Case E: 'A renal biopsy is planned for tomorrow.'
        Safety requirement:
        - Must extract renal biopsy as investigation with temporality == Planned.
        - Must extract Scheduled Investigation event.
        - Must capture pending task for renal biopsy.
        - Must extract 'tomorrow' as relative temporal anchor.
        """
        text = "A renal biopsy is planned for tomorrow."
        res = self.run_full_pipeline(text)
        invs = res["entities"]["investigations"]
        events = res["events"]
        pending = res["pending"]
        temporal = res["temporal"]

        self.assertTrue(len(invs) > 0)
        self.assertEqual(invs[0]["temporality"], "Planned")
        self.assertTrue(invs[0]["is_planned"])

        self.assertTrue(any("biopsy" in ev.get("event", "").lower() for ev in events))
        self.assertTrue(any("biopsy" in p.get("task", "").lower() for p in pending))
        self.assertTrue(any("tomorrow" in t.get("expression", "").lower() for t in temporal))

    def test_case_f_uncertain_suspected_infection(self):
        """
        Case F: 'The patient may have an infection.'
        Safety requirement:
        - Must extract infection with assertion == 'Possible' and is_uncertain == True.
        - Must reflect uncertainty in executive summary ('suspected infection') and ISBAR.
        """
        text = "The patient may have an infection."
        res = self.run_full_pipeline(text)
        conds = res["entities"]["conditions"]
        structured = res["structured"]

        self.assertTrue(len(conds) > 0)
        infection = conds[0]
        self.assertEqual(infection["assertion"], "Possible")
        self.assertTrue(infection["is_uncertain"])

        exec_summary = structured.get("executive_summary", "")
        self.assertIn("suspected", exec_summary.lower())

        situation = structured.get("isbar", {}).get("situation", [])
        self.assertTrue(any("Suspected" in s or "Query" in s for s in situation))

    def test_protected_clinical_sentence_splitting(self):
        """
        Clinical sentence preservation:
        Abbreviations like 'Dr.', 'Mr.', 'obs.', and decimal numbers must not split sentences prematurely.
        """
        text = "Dr. Adams reviewed the patient at 1400. The obs. were stable. Give 12.5 mg of paracetamol."
        sentences = clinical_context_extractor.split_sentences_protected(text)
        sent_texts = [s[0] for s in sentences]

        self.assertEqual(len(sent_texts), 3)
        self.assertEqual(sent_texts[0], "Dr. Adams reviewed the patient at 1400.")
        self.assertEqual(sent_texts[1], "The obs. were stable.")
        self.assertEqual(sent_texts[2], "Give 12.5 mg of paracetamol.")


if __name__ == "__main__":
    unittest.main()
