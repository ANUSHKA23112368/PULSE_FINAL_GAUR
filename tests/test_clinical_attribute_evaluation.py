"""
PULSE — Clinical Attribute Evaluation & Handover Integrity Tests
Phase 5 — Step 5.7 Attribute Accuracy & Structured Handover Evaluation

Tests:
1. Cross-medication attribute contamination prevention (clause boundary isolation).
2. Missing attribute preservation (no invented doses, routes, or frequencies).
3. PRN indication extraction and binding without confusing PRN indication for drug name.
4. Investigation status distinctions (Completed, Sent, Pending, Awaiting Results).
5. Negation and temporality preservation (Negated not active, Historical not current).
6. Conditional trigger condition and resulting action separation.
7. Evidence-offset grounding integrity (text slices match exactly).
8. Structured summary and ISBAR generation fidelity.
"""

import unittest
import os
import json
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from backend.extraction.entity_extractor import clinical_entity_extractor
from backend.extraction.structured_generator import StructuredHandoverGenerator
from scripts.evaluate_clinical_attributes import RESULTS_OUTPUT_PATH, FIXTURE_PATH


class TestClinicalAttributeEvaluation(unittest.TestCase):
    def setUp(self):
        self.generator = StructuredHandoverGenerator()

    def test_01_cross_medication_attribute_contamination(self):
        """Verifies that route, frequency, and dosage are not contaminated across multiple medications in a clause."""
        text = "Prescribed Tab Furosemide 40 mg PO daily and Metoprolol 12.5 mg BD."
        res = clinical_entity_extractor.extract(text)
        meds = {m["text"]: m for m in res["medications"]}

        self.assertIn("Furosemide", meds)
        self.assertIn("Metoprolol", meds)

        furo = meds["Furosemide"]
        meto = meds["Metoprolol"]

        # Furosemide should have 40 mg, PO, daily
        self.assertIn("40 mg", furo["dosage"])
        self.assertEqual(furo["route"], "PO")
        self.assertEqual(furo["frequency"], "DAILY")

        # Metoprolol should have 12.5 mg, BD, and NOT leak PO
        self.assertIn("12.5 mg", meto["dosage"])
        self.assertEqual(meto["frequency"], "BD")
        self.assertEqual(meto["route"], "Unspecified route")

    def test_02_distinct_drugs_sharing_pharmacological_class(self):
        """Verifies that multiple distinct drugs in the same pharmacological class are not collapsed into each other."""
        text = "Ceased Warfarin; commenced Heparin 5000 units subcut."
        res = clinical_entity_extractor.extract(text)
        med_names = [m["text"] for m in res["medications"]]

        self.assertIn("Warfarin", med_names)
        self.assertIn("Heparin", med_names)
        self.assertEqual(len(med_names), 2, "Both Warfarin and Heparin must be extracted as distinct entities")

        heparin = [m for m in res["medications"] if m["text"] == "Heparin"][0]
        self.assertIn("5000 units", heparin["dosage"])
        self.assertEqual(heparin["route"], "SUBCUT")

    def test_03_missing_attribute_preservation(self):
        """Verifies that unmentioned dosages and routes remain unspecified and are never hallucinated."""
        text = "Started on Paracetamol and Aspirin."
        res = clinical_entity_extractor.extract(text)
        for m in res["medications"]:
            self.assertEqual(m["dosage"], "Unspecified dose in text")
            self.assertEqual(m["route"], "Unspecified route")
            self.assertEqual(m["frequency"], "Unspecified frequency")

    def test_04_prn_indication_binding(self):
        """Verifies that PRN indications are bound to medication entities and not mistaken for drug names."""
        text = "Administer Paracetamol 1g PO QID PRN for headache."
        res = clinical_entity_extractor.extract(text)
        paracetamol = [m for m in res["medications"] if m["text"] == "Paracetamol"][0]

        self.assertEqual(paracetamol.get("prn_indication"), "headache")
        self.assertFalse(any(m["text"] == "headache" for m in res["medications"]))

    def test_05_investigation_status_distinctions(self):
        """Verifies distinction between Completed, Sent, and Pending investigation progress states."""
        text = "Chest X-Ray is completed. Blood cultures sent off to lab. Renal biopsy is pending."
        res = clinical_entity_extractor.extract(text)
        invs = {inv["text"].lower(): inv.get("status") for inv in res["investigations"]}

        # CXR
        cxr_status = [v for k, v in invs.items() if "x-ray" in k][0]
        self.assertEqual(cxr_status, "Completed")

        # Blood cultures
        culture_status = [v for k, v in invs.items() if "culture" in k][0]
        self.assertEqual(culture_status, "Sent")

        # Biopsy
        biopsy_status = [v for k, v in invs.items() if "biopsy" in k][0]
        self.assertEqual(biopsy_status, "Pending")

    def test_06_negation_and_temporality_preservation(self):
        """Verifies that negated mentions are not treated as active, and historical conditions are preserved."""
        text = "Patient denies any chest pain. Prior history of asthma."
        res = clinical_entity_extractor.extract(text)

        symptoms = [s for s in res["symptoms"] if "chest pain" in s["text"].lower()]
        self.assertTrue(len(symptoms) > 0)
        self.assertTrue(symptoms[0].get("is_negated"))
        self.assertEqual(symptoms[0].get("assertion"), "Negated")

        conditions = [c for c in res["conditions"] if "history of" in c.get("rule_source", "").lower() or c.get("temporality") == "Historical"]
        self.assertTrue(len(conditions) > 0)
        self.assertEqual(conditions[0].get("temporality"), "Historical")

    def test_07_conditional_trigger_and_action_separation(self):
        """Verifies that conditional directives separate trigger condition from resulting clinical action."""
        text = "If BP < 90, inform MO. Hold Metoprolol if SBP < 100."
        conditionals = self.generator.extract_conditional_instructions(text)
        self.assertEqual(len(conditionals), 2)

        c1 = conditionals[0]
        self.assertEqual(c1["trigger_condition"], "BP < 90")
        self.assertEqual(c1["resulting_action"], "inform MO")

        c2 = conditionals[1]
        self.assertEqual(c2["trigger_condition"], "SBP < 100")
        self.assertEqual(c2["resulting_action"], "Hold Metoprolol")

    def test_08_evidence_offset_integrity(self):
        """Verifies that all extracted entities have character offsets exactly matching the source text slice."""
        text = "Bed 8, Michael Wu. 68yo under Dr Smith. History of CCF. Prescribed Digoxin 125mcg daily."
        res = clinical_entity_extractor.extract(text)
        for ent in res.get("all_entities", []):
            st = ent.get("start_char", ent.get("source_start"))
            en = ent.get("end_char", ent.get("source_end"))
            txt = ent.get("text", ent.get("source_text"))
            self.assertIsNotNone(st)
            self.assertIsNotNone(en)
            self.assertEqual(text[st:en], txt, f"Offset mismatch for {txt}: expected {text[st:en]}")

    def test_09_structured_summary_fidelity(self):
        """Verifies that executive summary synthesis accurately respects negated and active conditions."""
        patient_dict = {"Patient Name": "Arthur Pendelton", "Bed / Room": "Bed 4", "Age": "68 years", "Attending Consultant": "Dr Edwards"}
        conditions = [{"normalized": "Type 2 Diabetes Mellitus", "is_negated": False, "is_historical": True, "is_uncertain": False}]
        symptoms = [{"normalized": "Chest Pain", "is_negated": True, "is_historical": False, "is_uncertain": False, "text": "chest pain"}]
        pending = [{"task": "Review renal biopsy results"}]
        measurements = [{"type": "Blood Pressure", "text": "120/80"}]

        summary = self.generator.generate_executive_summary(patient_dict, conditions, symptoms, pending, measurements, "")
        self.assertIn("Arthur Pendelton", summary)
        self.assertIn("Bed 4", summary)
        # Negated chest pain must NOT be stated as active
        self.assertNotIn("admitted for management of Chest Pain", summary)
        self.assertIn("denies chest pain", summary)

    def test_10_attribute_results_artifact_schema(self):
        """Verifies that the generated clinical attribute evaluation JSON artifact exists and has valid sections."""
        self.assertTrue(os.path.exists(RESULTS_OUTPUT_PATH), f"Results artifact missing at: {RESULTS_OUTPUT_PATH}")
        with open(RESULTS_OUTPUT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("metadata", data)
        self.assertIn("section_a_historical_corpus", data)
        self.assertIn("section_b_schema_fixtures_regression", data)
        self.assertIn("section_c_controlled_error_analysis", data)

        sec_a = data["section_a_historical_corpus"]
        self.assertEqual(sec_a["source_offset_integrity"]["offset_accuracy_pct"], 100.0)
        self.assertIn("NOT EVALUABLE", sec_a["attribute_evaluation_status"]["medication_to_dose_binding"])


if __name__ == "__main__":
    unittest.main()
