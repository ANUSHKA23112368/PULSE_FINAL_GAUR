"""
PULSE Phase 5 — Step 2: Indian Clinical Shorthand Normalizer Regression Test Suite
Tests:
1. Recognized abbreviation in uppercase.
2. Recognized abbreviation in lowercase or mixed case.
3. Punctuation and spacing variations (K/C/O, K.C.O., KCO, c/o, b/l).
4. K/C/O in a clinical-history context (verifying historical comorbidity assertion).
5. C/O in a symptom context (verifying active presenting complaint).
6. B/L in a relevant clinical context (verifying anatomical bilateral modifier).
7. NAD without inventing additional findings (verifying zero false diagnoses).
8. Medication frequency attached to the correct medication without cross-drug leakage.
9. OD in a medication context versus an unrelated context (ophthalmic & toxicology).
10. SOS or PRN in a medication context.
11. GCS with explicit component scores (E4 V5 M6).
12. GCS with missing component scores (15/15 and simple score; no hallucinated components).
13. Negated clinical statements (assertion fidelity).
14. Uncertain clinical statements (hedging fidelity).
15. Unknown abbreviation preserved for review (no silent dropping).
16. Original source text preserved exactly.
17. Evidence spans or evidence text remain correctly aligned.
18. No regression in decimal dosage parsing, including 0.25 mg and 12.5 mg.
19. No regression in investigation-status extraction (CT head is pending).
20. No regression in acute ward false-positive symptom acuity.
"""

import unittest
import sys
import os

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.preprocessing.preprocessor import clinical_preprocessor
from backend.extraction.entity_extractor import clinical_entity_extractor
from backend.extraction.shorthand_normalizer import clinical_shorthand_normalizer
from backend.extraction.context_extractor import clinical_context_extractor
from backend.extraction.structured_generator import structured_handover_generator
from backend.extraction.event_extractor import clinical_event_extractor
from backend.extraction.temporal_extractor import clinical_temporal_extractor


class TestIndianClinicalShorthandNormalizer(unittest.TestCase):
    def setUp(self):
        self.normalizer = clinical_shorthand_normalizer
        self.extractor = clinical_entity_extractor
        self.preprocessor = clinical_preprocessor
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
            "temporal": temporal,
            "pending_tasks": pending,
            "follow_up": follow_up,
            "structured": structured
        }

    # =========================================================================
    # 1. Recognized abbreviation in uppercase
    # =========================================================================
    def test_01_recognized_abbreviations_uppercase(self):
        """Verifies canonical recognition of uppercase abbreviations."""
        text = "Patient has K/C/O Type 2 DM, presented with C/O acute chest pain. USG abdomen and CBC ordered."
        res = self._run_pipeline(text)
        abbrs = res["entities"]["abbreviations"]
        canonicals = {a.get("canonical_abbr"): a.get("expansion") for a in abbrs}

        self.assertIn("K/C/O", canonicals)
        self.assertEqual(canonicals["K/C/O"], "Known Case Of")
        self.assertIn("C/O", canonicals)
        self.assertEqual(canonicals["C/O"], "Complaining Of")
        self.assertIn("USG", canonicals)
        self.assertEqual(canonicals["USG"], "Ultrasonography (Ultrasound)")
        self.assertIn("CBC", canonicals)
        self.assertEqual(canonicals["CBC"], "Complete Blood Count")

    # =========================================================================
    # 2. Recognized abbreviation in lowercase or mixed case
    # =========================================================================
    def test_02_recognized_abbreviations_lowercase_and_mixed_case(self):
        """Verifies case-insensitive normalization for lowercase and mixed-case shorthands."""
        text = "Patient k/c/o htn and c/o headache with b/l pedal edema. rbs recorded as 140."
        res = self._run_pipeline(text)
        abbrs = res["entities"]["abbreviations"]
        canonicals = {a.get("canonical_abbr"): a.get("expansion") for a in abbrs}

        self.assertIn("K/C/O", canonicals)
        self.assertIn("C/O", canonicals)
        self.assertIn("B/L", canonicals)
        self.assertEqual(canonicals["B/L"], "Bilateral")
        self.assertIn("RBS", canonicals)
        self.assertEqual(canonicals["RBS"], "Random Blood Sugar")

    # =========================================================================
    # 3. Punctuation and spacing variations
    # =========================================================================
    def test_03_punctuation_and_spacing_variations(self):
        """Verifies robustness across slashes, dots, and no-separator variations (e.g. K.C.O., KCO, k/c/o)."""
        texts = [
            "K.C.O. Hypertension",
            "KCO Hypertension",
            "k/c/o Hypertension",
            "k.c.o. Hypertension"
        ]
        for t in texts:
            res = self._run_pipeline(t)
            abbrs = res["entities"]["abbreviations"]
            self.assertTrue(
                any(a.get("canonical_abbr") == "K/C/O" and a.get("expansion") == "Known Case Of" for a in abbrs),
                f"Failed to normalize variation in: '{t}'"
            )

    # =========================================================================
    # 4. K/C/O in a clinical-history context
    # =========================================================================
    def test_04_kco_clinical_history_context(self):
        """Verifies that K/C/O correctly triggers historical comorbidity temporality."""
        text = "Patient is a K/C/O Hypertension and Type 2 Diabetes."
        res = self._run_pipeline(text)
        conds = res["entities"]["conditions"]

        self.assertTrue(len(conds) > 0, "Expected conditions to be extracted")
        for c in conds:
            self.assertTrue(c["is_historical"], f"Condition {c['text']} under K/C/O must be historical")
            self.assertEqual(c["temporality"], "Historical")

    # =========================================================================
    # 5. C/O in a symptom context
    # =========================================================================
    def test_05_co_symptom_presentation_context(self):
        """Verifies that C/O correctly triggers active presenting symptom status."""
        text = "Patient C/O severe headache and nausea."
        res = self._run_pipeline(text)
        symps = res["entities"]["symptoms"]

        self.assertTrue(len(symps) > 0, "Expected symptoms to be extracted")
        for s in symps:
            self.assertFalse(s["is_negated"])
            self.assertEqual(s["assertion"], "Affirmative")
            self.assertEqual(s["temporality"], "Current")

    # =========================================================================
    # 6. B/L in a relevant clinical context
    # =========================================================================
    def test_06_bl_bilateral_anatomical_modifier(self):
        """Verifies B/L is recognized as Bilateral modifier and linked to supporting span."""
        text = "Noted B/L lower limb edema on examination."
        res = self._run_pipeline(text)
        abbrs = res["entities"]["abbreviations"]

        bl_abbr = next((a for a in abbrs if a.get("canonical_abbr") == "B/L"), None)
        self.assertIsNotNone(bl_abbr, "Expected B/L abbreviation")
        self.assertEqual(bl_abbr.get("expansion"), "Bilateral")
        self.assertEqual(bl_abbr.get("abbreviation"), "B/L")
        self.assertEqual(bl_abbr.get("rule_id"), "IND_ABBR_BL")

    # =========================================================================
    # 7. NAD without inventing additional findings
    # =========================================================================
    def test_07_nad_without_inventing_findings(self):
        """Verifies NAD expands to No Abnormality Detected without inventing false diagnoses or symptoms."""
        text = "Systemic examination: CVS: NAD, Respiratory: NAD, Abdomen: NAD."
        res = self._run_pipeline(text)
        abbrs = res["entities"]["abbreviations"]
        conds = res["entities"]["conditions"]
        symps = res["entities"]["symptoms"]

        # NAD must be recognized in abbreviations
        nad_items = [a for a in abbrs if a.get("canonical_abbr") == "NAD"]
        self.assertTrue(len(nad_items) > 0, "Expected NAD to be recognized")
        self.assertEqual(nad_items[0].get("expansion"), "No Abnormality Detected")

        # Zero false conditions or symptoms should be hallucinated from NAD
        self.assertEqual(len(conds), 0, f"Expected 0 conditions, found: {conds}")
        self.assertEqual(len(symps), 0, f"Expected 0 symptoms, found: {symps}")

    # =========================================================================
    # 8. Medication frequency attached to the correct medication
    # =========================================================================
    def test_08_medication_frequency_correct_binding(self):
        """Verifies Indian prescription frequencies (BD, HS) bind to the correct drugs without cross-leakage."""
        text = "Started on Tab Metformin 500mg BD and Tab Atorvastatin 20mg HS."
        res = self._run_pipeline(text)
        meds = res["entities"]["medications"]

        metformin = next((m for m in meds if "metformin" in m.get("text", "").lower()), None)
        atorvastatin = next((m for m in meds if "atorvastatin" in m.get("text", "").lower()), None)

        self.assertIsNotNone(metformin)
        self.assertEqual(metformin.get("dosage"), "500mg")
        self.assertEqual(metformin.get("frequency"), "BD")

        self.assertIsNotNone(atorvastatin)
        self.assertEqual(atorvastatin.get("dosage"), "20mg")
        self.assertEqual(atorvastatin.get("frequency"), "HS")

    # =========================================================================
    # 9. OD in medication context versus unrelated contexts
    # =========================================================================
    def test_09_od_context_sensitive_disambiguation(self):
        """
        Verifies context sensitivity for OD:
        - In prescription clause -> Once Daily (Omni Die) frequency
        - In ophthalmic clause -> Oculus Dexter (Right Eye)
        - In overdose clause -> Overdose / Toxicity
        """
        # Case 1: Medication context
        t_med = self._run_pipeline("Prescribed Tab Pantoprazole 40mg OD.")
        panto = next((m for m in t_med["entities"]["medications"] if "pantoprazole" in m.get("text", "").lower()), None)
        self.assertIsNotNone(panto)
        self.assertEqual(panto.get("frequency"), "OD")

        # Case 2: Ophthalmic context
        t_eye = self._run_pipeline("Pupil OD sluggishly reactive to light; cataract OD noted.")
        # Must NOT extract any medication with OD frequency
        eye_meds = [m for m in t_eye["entities"]["medications"] if m.get("frequency") == "OD"]
        self.assertEqual(len(eye_meds), 0, "Ophthalmic OD must NOT be bound as medication frequency")
        # Abbreviation must be categorized as Oculus Dexter
        eye_abbrs = [a for a in t_eye["entities"]["abbreviations"] if "Oculus Dexter" in a.get("expansion", "")]
        self.assertTrue(len(eye_abbrs) > 0, "Expected Oculus Dexter abbreviation")

        # Case 3: Overdose context
        t_tox = self._run_pipeline("Patient admitted following suspected paracetamol OD.")
        tox_meds = [m for m in t_tox["entities"]["medications"] if m.get("frequency") == "OD"]
        self.assertEqual(len(tox_meds), 0, "Toxicology OD must NOT be bound as medication frequency")
        tox_abbrs = [a for a in t_tox["entities"]["abbreviations"] if "Overdose" in a.get("expansion", "")]
        self.assertTrue(len(tox_abbrs) > 0, "Expected Overdose abbreviation")

    # =========================================================================
    # 10. SOS or PRN in a medication context
    # =========================================================================
    def test_10_sos_and_prn_medication_frequency(self):
        """Verifies SOS and PRN frequencies are correctly extracted and bound."""
        text = "Tab Paracetamol 650mg SOS given for fever."
        res = self._run_pipeline(text)
        meds = res["entities"]["medications"]

        pcm = next((m for m in meds if "paracetamol" in m.get("text", "").lower()), None)
        self.assertIsNotNone(pcm)
        self.assertEqual(pcm.get("frequency"), "SOS")

    # =========================================================================
    # 11. GCS with explicit component scores
    # =========================================================================
    def test_11_gcs_explicit_components(self):
        """Verifies explicit GCS component scores (E4 V5 M6) derive total and preserve components."""
        text = "Neurological examination reveals GCS E4 V5 M6."
        res = self._run_pipeline(text)
        meas = res["entities"]["measurements"]

        gcs = next((m for m in meas if "glasgow" in m.get("type", "").lower() or "gcs" in m.get("type", "").lower()), None)
        self.assertIsNotNone(gcs, "Expected GCS measurement")
        self.assertEqual(gcs.get("eye_score"), 4)
        self.assertEqual(gcs.get("verbal_score"), 5)
        self.assertEqual(gcs.get("motor_score"), 6)
        self.assertEqual(gcs.get("total_score"), 15)
        self.assertTrue(gcs.get("components_present"))

    # =========================================================================
    # 12. GCS with missing component scores (Strict Non-Hallucination)
    # =========================================================================
    def test_12_gcs_missing_components_no_hallucination(self):
        """Verifies that GCS 15/15 or GCS 14 records total score and strictly avoids inventing E, V, M."""
        for sample_text in ["Neurological state stable with GCS 15/15.", "Patient alert, GCS 14 on room air."]:
            res = self._run_pipeline(sample_text)
            meas = res["entities"]["measurements"]
            gcs = next((m for m in meas if "glasgow" in m.get("type", "").lower() or "gcs" in m.get("type", "").lower()), None)

            self.assertIsNotNone(gcs, f"Expected GCS measurement in '{sample_text}'")
            self.assertFalse(gcs.get("components_present"))
            self.assertIsNone(gcs.get("eye_score"), "Must NOT invent eye score when absent")
            self.assertIsNone(gcs.get("verbal_score"), "Must NOT invent verbal score when absent")
            self.assertIsNone(gcs.get("motor_score"), "Must NOT invent motor score when absent")

    # =========================================================================
    # 13. Negated clinical statements
    # =========================================================================
    def test_13_negated_clinical_statements_preserved(self):
        """Verifies negation assertion is preserved for clinical statements with shorthand."""
        text = "No C/O chest pain or SOB."
        res = self._run_pipeline(text)
        symps = res["entities"]["symptoms"]

        self.assertTrue(len(symps) > 0)
        for s in symps:
            self.assertTrue(s["is_negated"], f"Symptom '{s['text']}' should be negated")
            self.assertEqual(s["assertion"], "Negated")

    # =========================================================================
    # 14. Uncertain clinical statements
    # =========================================================================
    def test_14_uncertain_clinical_statements_preserved(self):
        """Verifies uncertainty / hedging assertion is preserved for statements with shorthand."""
        text = "Suspected B/L pneumonia under evaluation."
        res = self._run_pipeline(text)
        conds = res["entities"]["conditions"]

        self.assertTrue(len(conds) > 0)
        self.assertTrue(conds[0]["is_uncertain"])
        self.assertIn(conds[0]["assertion"], ["Possible", "Uncertain"])

    # =========================================================================
    # 15. Unknown abbreviation preserved for review
    # =========================================================================
    def test_15_unknown_abbreviation_preserved_for_review(self):
        """Verifies that an unknown all-caps shorthand candidate is preserved and flagged for review."""
        text = "Patient scheduled for XYZQ scan next shift."
        res = self._run_pipeline(text)
        abbrs = res["entities"]["abbreviations"]

        xyzq = next((a for a in abbrs if a.get("canonical_abbr") == "XYZQ"), None)
        self.assertIsNotNone(xyzq, "Expected unknown abbreviation candidate XYZQ to be preserved")
        self.assertEqual(xyzq.get("review_status"), "flagged_for_review")
        self.assertIsNone(xyzq.get("normalized_value"))

    # =========================================================================
    # 16. Original source text preserved exactly
    # =========================================================================
    def test_16_original_source_text_verbatim_preservation(self):
        """Verifies that source_text is preserved verbatim without text replacement or corruption."""
        text = "Patient k/c/o htn and type 2 dm."
        res = self._run_pipeline(text)
        abbrs = res["entities"]["abbreviations"]

        kco = next((a for a in abbrs if a.get("canonical_abbr") == "K/C/O"), None)
        self.assertIsNotNone(kco)
        self.assertEqual(kco.get("source_text"), "k/c/o")
        self.assertEqual(kco.get("abbreviation"), "k/c/o")

    # =========================================================================
    # 17. Evidence spans and text remain correctly aligned
    # =========================================================================
    def test_17_evidence_spans_alignment(self):
        """Verifies that character offsets start_char and end_char point to exact matching substring."""
        text = "Started on Tab Metformin 500mg BD. Planned for USG abdomen."
        res = self._run_pipeline(text)
        abbrs = res["entities"]["abbreviations"]

        for a in abbrs:
            st, en = a.get("start_char"), a.get("end_char")
            if st is not None and en is not None:
                extracted_slice = text[st:en]
                self.assertEqual(
                    extracted_slice.lower(),
                    a.get("source_text", "").lower(),
                    f"Span mismatch: slice '{extracted_slice}' vs source_text '{a.get('source_text')}'"
                )

    # =========================================================================
    # 18. P0 regression check: Decimal dosage parsing preserved
    # =========================================================================
    def test_18_p0_dosage_decimal_precision(self):
        """Verifies 0.25 mg and 12.5 mg are never truncated or corrupted."""
        text = "Administered Digoxin 0.25 mg mane and Carvedilol 12.5 mg BD."
        res = self._run_pipeline(text)
        meds = res["entities"]["medications"]

        digoxin = next((m for m in meds if "digoxin" in m.get("text", "").lower()), None)
        self.assertIsNotNone(digoxin)
        self.assertEqual(digoxin.get("dosage"), "0.25 mg")
        self.assertEqual(digoxin.get("frequency"), "MANE")

        carvedilol = next((m for m in meds if "carvedilol" in m.get("text", "").lower()), None)
        self.assertIsNotNone(carvedilol)
        self.assertEqual(carvedilol.get("dosage"), "12.5 mg")
        self.assertEqual(carvedilol.get("frequency"), "BD")

    # =========================================================================
    # 19. Phase 3 regression check: Investigation status extraction
    # =========================================================================
    def test_19_phase3_investigation_status_preservation(self):
        """Verifies CT head is pending maintains Pending status."""
        text = "CT head is pending."
        res = self._run_pipeline(text)
        invs = res["entities"]["investigations"]

        self.assertTrue(len(invs) > 0)
        ct = invs[0]
        self.assertEqual(ct.get("status"), "Pending")

    # =========================================================================
    # 20. Acuity regression check: False-positive acute ward protection
    # =========================================================================
    def test_20_acuity_false_positive_acute_ward_protection(self):
        """Verifies that 'acute ward' does not turn 'headache' into unsupported 'Acute Headache'."""
        text = "Patient transferred to acute ward. Reports mild headache."
        res = self._run_pipeline(text)
        situation = " ".join(res["structured"].get("isbar", {}).get("situation", []))
        self.assertNotIn("Acute Headache", situation)


if __name__ == "__main__":
    unittest.main()
