"""
PULSE — Phase 5, Step 3: Validated Hinglish Clinical Expression Mapping Tests
Comprehensive unit and regression tests for Roman-Hindi clinical expression mapping,
context-sensitive disambiguation, evidence preservation, assertion/temporality analysis,
and pipeline compatibility.
"""

import unittest
from backend.extraction.contract import ClinicalEntity
from backend.extraction.context_extractor import clinical_context_extractor
from backend.extraction.hinglish_mapper import clinical_hinglish_mapper
from backend.extraction.entity_extractor import HybridClinicalEntityExtractor


class TestHinglishClinicalMapper(unittest.TestCase):
    def setUp(self):
        self.mapper = clinical_hinglish_mapper
        self.extractor = HybridClinicalEntityExtractor()

    # --------------------------------------------------------------------------
    # 1. Five Core Symptoms (chakkar, ulti, chest pain, abdominal pain, weakness)
    # --------------------------------------------------------------------------
    def test_01_core_symptoms_dizziness_chakkar(self):
        """chakkar aana / chakkar aa raha hai maps to Dizziness"""
        note = "Patient ko subah se chakkar aa raha hai."
        entities = self.mapper.extract_hinglish_symptoms(note)
        self.assertTrue(len(entities) >= 1)
        chakkar_ent = next((e for e in entities if "chakkar" in e.source_text.lower()), None)
        self.assertIsNotNone(chakkar_ent)
        self.assertEqual(chakkar_ent.normalized_value, "Dizziness")
        self.assertEqual(chakkar_ent.entity_type, "Symptom")
        self.assertEqual(chakkar_ent.review_status, "confirmed")
        self.assertEqual(chakkar_ent.attributes["rule_id"], "HINGLISH_SYM_DIZZINESS")

    def test_02_core_symptoms_vomiting_ulti(self):
        """ulti / ulti hui maps to Vomiting"""
        note = "Patient ko do baar ulti hui."
        entities = self.mapper.extract_hinglish_symptoms(note)
        self.assertTrue(len(entities) >= 1)
        ulti_ent = next((e for e in entities if "ulti" in e.source_text.lower()), None)
        self.assertIsNotNone(ulti_ent)
        self.assertEqual(ulti_ent.normalized_value, "Vomiting")
        self.assertEqual(ulti_ent.entity_type, "Symptom")
        self.assertEqual(ulti_ent.review_status, "confirmed")

    def test_03_core_symptoms_chest_pain(self):
        """chhati mein dard / seene mein dard maps to Chest Pain"""
        for phrase in ["chhati mein dard", "seene mein dard", "chaati me dard", "sine mein dard"]:
            note = f"Patient complaining of {phrase} since 2 hours."
            entities = self.mapper.extract_hinglish_symptoms(note)
            self.assertTrue(len(entities) >= 1, f"Failed to match: {phrase}")
            cp_ent = entities[0]
            self.assertEqual(cp_ent.normalized_value, "Chest Pain")
            self.assertEqual(cp_ent.attributes["rule_id"], "HINGLISH_SYM_CHEST_PAIN")

    def test_04_core_symptoms_abdominal_pain(self):
        """pet mein dard / pet dard maps to Abdominal Pain"""
        for phrase in ["pet mein dard", "pet dard", "pet me dard", "pait mein dard"]:
            note = f"Patient ko {phrase} ho raha hai."
            entities = self.mapper.extract_hinglish_symptoms(note)
            self.assertTrue(len(entities) >= 1, f"Failed to match: {phrase}")
            abd_ent = entities[0]
            self.assertEqual(abd_ent.normalized_value, "Abdominal Pain")
            self.assertEqual(abd_ent.attributes["rule_id"], "HINGLISH_SYM_ABDOMINAL_PAIN")

    def test_05_core_symptoms_weakness_kamzori(self):
        """kamzori / kamzori lagna maps to Weakness"""
        for phrase in ["kamzori", "kamzori lag rahi hai", "kamjori"]:
            note = f"Patient ko bahut {phrase} hai."
            entities = self.mapper.extract_hinglish_symptoms(note)
            self.assertTrue(len(entities) >= 1, f"Failed to match: {phrase}")
            wk_ent = entities[0]
            self.assertEqual(wk_ent.normalized_value, "Weakness")
            self.assertEqual(wk_ent.attributes["rule_id"], "HINGLISH_SYM_WEAKNESS")

    # --------------------------------------------------------------------------
    # 2. Additional Supported Symptom Mappings
    # --------------------------------------------------------------------------
    def test_06_additional_supported_symptoms(self):
        """bukhar -> Fever, saans phoolna -> Dyspnea, khansi -> Cough, sir dard -> Headache"""
        test_cases = [
            ("Patient ko tez bukhar hai.", "Fever", "HINGLISH_SYM_FEVER"),
            ("Patient ko saans lene mein dikkat hai.", "Breathing Difficulty (Dyspnea)", "HINGLISH_SYM_DYSPNEA"),
            ("Patient ko sookhi khansi hai.", "Cough", "HINGLISH_SYM_COUGH"),
            ("Patient ko sir mein dard ho raha hai.", "Headache", "HINGLISH_SYM_HEADACHE"),
            ("Patient ko patla dast ho raha hai.", "Diarrhea", "HINGLISH_SYM_DIARRHEA"),
            ("Patient ko kapkapi aur thand lag rahi hai.", "Chills / Rigors", "HINGLISH_SYM_CHILLS")
        ]
        for note, expected_concept, expected_rule in test_cases:
            entities = self.mapper.extract_hinglish_symptoms(note)
            self.assertTrue(len(entities) >= 1, f"Failed to match: {note}")
            matching = [e for e in entities if e.normalized_value == expected_concept]
            self.assertTrue(len(matching) >= 1, f"Expected {expected_concept} in {note}")
            self.assertEqual(matching[0].attributes["rule_id"], expected_rule)

    # --------------------------------------------------------------------------
    # 3. Uppercase, Lowercase, Mixed-case Variations
    # --------------------------------------------------------------------------
    def test_07_casing_variations(self):
        """Recognizes uppercase, lowercase, and mixed-case Hinglish expressions"""
        variations = [
            ("PATIENT KO CHHATI MEIN DARD HAI", "Chest Pain"),
            ("patient ko bukhar hai", "Fever"),
            ("Patient ko uLtI hui thi", "Vomiting"),
            ("Patient Ko KaMzOrI Lag Rahi Hai", "Weakness")
        ]
        for text, expected in variations:
            entities = self.mapper.extract_hinglish_symptoms(text)
            self.assertTrue(len(entities) >= 1, f"Failed for text: {text}")
            self.assertEqual(entities[0].normalized_value, expected)

    # --------------------------------------------------------------------------
    # 4. Spacing and Spelling Variations
    # --------------------------------------------------------------------------
    def test_08_spacing_and_spelling_variations(self):
        """Robust to common spelling variations in Roman Hindi"""
        variations = [
            ("chaati mein dard", "Chest Pain"),
            ("seene me dard", "Chest Pain"),
            ("sine mein dard", "Chest Pain"),
            ("pet dard", "Abdominal Pain"),
            ("pait mein dard", "Abdominal Pain"),
            ("bukhaar", "Fever"),
            ("kamjori", "Weakness"),
            ("sans phoolna", "Breathing Difficulty (Dyspnea)"),
            ("saans lene me takleef", "Breathing Difficulty (Dyspnea)")
        ]
        for text, expected in variations:
            note = f"Patient reports {text}."
            entities = self.mapper.extract_hinglish_symptoms(note)
            self.assertTrue(len(entities) >= 1, f"Failed on variation: {text}")
            self.assertEqual(entities[0].normalized_value, expected)

    # --------------------------------------------------------------------------
    # 5. Negated Symptoms
    # --------------------------------------------------------------------------
    def test_09_negated_symptoms_post_and_pre(self):
        """Explicitly handles post-negation and pre-negation in Hinglish syntax"""
        # Post-negation: "bukhar nahi hai"
        note1 = "Patient ko bukhar nahi hai."
        res1 = self.extractor.extract(note1)
        sym1 = next((s for s in res1["symptoms"] if s["normalized"] == "Fever"), None)
        self.assertIsNotNone(sym1)
        self.assertEqual(sym1["assertion"], "Negated")
        self.assertTrue(sym1["is_negated"])

        # Post-negation: "chakkar nahi aa raha"
        note2 = "Patient ko chakkar nahi aa raha."
        res2 = self.extractor.extract(note2)
        sym2 = next((s for s in res2["symptoms"] if s["normalized"] == "Dizziness"), None)
        self.assertIsNotNone(sym2)
        self.assertEqual(sym2["assertion"], "Negated")
        self.assertTrue(sym2["is_negated"])

        # Pre-negation / Denies
        note3 = "Patient denies ulti and has no pet dard."
        res3 = self.extractor.extract(note3)
        ulti_sym = next((s for s in res3["symptoms"] if s["normalized"] == "Vomiting"), None)
        abd_sym = next((s for s in res3["symptoms"] if s["normalized"] == "Abdominal Pain"), None)
        self.assertIsNotNone(ulti_sym)
        self.assertIsNotNone(abd_sym)
        self.assertTrue(ulti_sym["is_negated"])
        self.assertTrue(abd_sym["is_negated"])

    # --------------------------------------------------------------------------
    # 6. Historical Symptoms & Past Temporal Context
    # --------------------------------------------------------------------------
    def test_10_historical_symptoms(self):
        """Preserves historical temporality ('kal ulti hui thi' and 'pehle se khansi thi, ab nahi hai')"""
        # "Patient ko kal ulti hui thi." -> Historical vomiting
        note1 = "Patient ko kal ulti hui thi."
        res1 = self.extractor.extract(note1)
        ulti_sym = next((s for s in res1["symptoms"] if s["normalized"] == "Vomiting"), None)
        self.assertIsNotNone(ulti_sym)
        self.assertEqual(ulti_sym["temporality"], "Historical")
        self.assertTrue(ulti_sym["is_historical"])

        # "Patient ko pehle se khansi thi, ab nahi hai." -> Historical cough with resolution noted
        note2 = "Patient ko pehle se khansi thi, ab nahi hai."
        res2 = self.extractor.extract(note2)
        cough_sym = next((s for s in res2["symptoms"] if s["normalized"] == "Cough"), None)
        self.assertIsNotNone(cough_sym)
        self.assertEqual(cough_sym["temporality"], "Historical")
        self.assertTrue(cough_sym["is_historical"])
        # Attributes explicitly retain resolution information
        self.assertIn("ab nahi hai", cough_sym.get("resolution_cue", "ab nahi hai"))

    # --------------------------------------------------------------------------
    # 7. Uncertain Clinical Statements
    # --------------------------------------------------------------------------
    def test_11_uncertain_clinical_statements(self):
        """'Shayad' or hedging preserves uncertainty without converting into confirmed diagnosis"""
        note = "Shayad patient ko bukhar hai."
        res = self.extractor.extract(note)
        fever_sym = next((s for s in res["symptoms"] if s["normalized"] == "Fever"), None)
        self.assertIsNotNone(fever_sym)
        self.assertEqual(fever_sym["assertion"], "Possible")
        self.assertTrue(fever_sym["is_uncertain"])

        # "Shayad patient ko infection hai" -> infection is uncertain, not confirmed
        note_inf = "Shayad patient ko infection hai."
        ctx_inf = clinical_context_extractor.analyze_assertion("infection", 18, 27, note_inf)
        self.assertEqual(ctx_inf["assertion"], "Possible")
        self.assertTrue(ctx_inf["is_uncertain"])

    # --------------------------------------------------------------------------
    # 8. Multiple Distinct Symptoms in One Note
    # --------------------------------------------------------------------------
    def test_12_multiple_distinct_symptoms(self):
        """Extracts and preserves multiple distinct Hinglish symptoms from a single clinical handover"""
        note = "Patient c/o chakkar and ulti since morning, also has bukhar and kamzori."
        res = self.extractor.extract(note)
        sym_names = {s["normalized"] for s in res["symptoms"]}
        self.assertIn("Dizziness", sym_names)
        self.assertIn("Vomiting", sym_names)
        self.assertIn("Fever", sym_names)
        self.assertIn("Weakness", sym_names)

    # --------------------------------------------------------------------------
    # 9. Safety against Unrelated Words Resembling Mapped Phrases
    # --------------------------------------------------------------------------
    def test_13_unrelated_partial_words_safety(self):
        """Word boundaries prevent spurious matches on English words like 'chakravyuh', 'petition', 'sardine', 'ultimatum'"""
        negative_examples = [
            "Patient was caught in a difficult chakravyuh of procedures.",
            "Legal petition filed regarding insurance clearance.",
            "Patient was served sardines for lunch.",
            "Hospital management issued an ultimatum to the vendor.",
            "Patient prescribed oral paracetamol syrup 10ml."
        ]
        for note in negative_examples:
            entities = self.mapper.extract_hinglish_symptoms(note)
            self.assertEqual(len(entities), 0, f"Spurious match found in: {note}")

    # --------------------------------------------------------------------------
    # 10. Ambiguous Ghabrahat Handling (No Auto-Conversion to Anxiety / Cardiac)
    # --------------------------------------------------------------------------
    def test_14_ambiguous_ghabrahat_isolated(self):
        """Isolated 'ghabrahat' is preserved for human review without assuming anxiety or cardiac cause"""
        note = "Patient ko thodi ghabrahat ho rahi hai."
        entities = self.mapper.extract_hinglish_symptoms(note)
        self.assertEqual(len(entities), 1)
        ghab_ent = entities[0]
        self.assertEqual(ghab_ent.source_text, "ghabrahat ho rahi hai")
        # Must NOT infer anxiety or cardiac condition
        self.assertIsNone(ghab_ent.normalized_value)
        self.assertEqual(ghab_ent.review_status, "flagged_for_review")
        self.assertEqual(ghab_ent.attributes["rule_id"], "HINGLISH_GHABRAHAT_AMBIGUOUS")

    def test_15_contextual_ghabrahat_disambiguation(self):
        """'ghabrahat' disambiguated ONLY when context explicitly justifies cardiac or anxiety concept"""
        # Cardiac context
        cardiac_note = "Patient ko ghabrahat ho rahi hai with palpitations and fast pulse."
        c_ents = self.mapper.extract_hinglish_symptoms(cardiac_note)
        self.assertTrue(len(c_ents) >= 1)
        c_ghab = next((e for e in c_ents if "ghabrahat" in e.source_text.lower()), None)
        self.assertIsNotNone(c_ghab)
        self.assertEqual(c_ghab.normalized_value, "Palpitations / Cardiac Sensation")
        self.assertEqual(c_ghab.review_status, "confirmed")
        self.assertEqual(c_ghab.attributes["rule_id"], "HINGLISH_GHABRAHAT_CARDIAC_CONTEXT")

        # Anxiety / Panic context
        anxiety_note = "Patient ko severe anxiety, panic and ghabrahat ho rahi hai."
        a_ents = self.mapper.extract_hinglish_symptoms(anxiety_note)
        self.assertTrue(len(a_ents) >= 1)
        a_ghab = next((e for e in a_ents if "ghabrahat" in e.source_text.lower()), None)
        self.assertIsNotNone(a_ghab)
        self.assertEqual(a_ghab.normalized_value, "Anxiety / Agitation")
        self.assertEqual(a_ghab.review_status, "confirmed")
        self.assertEqual(a_ghab.attributes["rule_id"], "HINGLISH_GHABRAHAT_ANXIETY_CONTEXT")

    # --------------------------------------------------------------------------
    # 11. Unknown Hinglish Expression Preservation for Review
    # --------------------------------------------------------------------------
    def test_16_unknown_hinglish_candidate_preservation(self):
        """Unmapped Hinglish complaint phrases are preserved for review, not silently discarded"""
        note = "Patient ko badan dard ho raha hai."
        res = self.extractor.extract(note)
        # Verify that either as symptom candidate or unclassified candidate it is preserved
        all_candidates = res["unclassified_candidates"] + res["symptoms"]
        badan_match = next((c for c in all_candidates if "badan dard" in c["text"].lower()), None)
        self.assertIsNotNone(badan_match, "Unmapped Hinglish complaint 'badan dard' was dropped!")
        self.assertEqual(badan_match["review_status"], "flagged_for_review")

    # --------------------------------------------------------------------------
    # 12. Exact Source Text Preservation & Span Alignment
    # --------------------------------------------------------------------------
    def test_17_evidence_preservation_and_offsets(self):
        """Exact character spans match the raw source slice without in-place string replacement"""
        note = "At 0800, patient complained of tez bukhar and chakkar."
        entities = self.mapper.extract_hinglish_symptoms(note)
        self.assertEqual(len(entities), 2)
        for ent in entities:
            extracted_slice = note[ent.source_start:ent.source_end]
            self.assertEqual(extracted_slice, ent.source_text)
            self.assertEqual(ent.evidence_text, note)

    # --------------------------------------------------------------------------
    # 13. Duplicate Extraction Prevention
    # --------------------------------------------------------------------------
    def test_18_duplicate_extraction_prevention(self):
        """Ensure identical spans are not extracted multiple times when pipeline runs"""
        note = "Patient has severe chhati mein dard since morning."
        res = self.extractor.extract(note)
        # Check that there is only one entity for this span
        cp_entities = [s for s in res["symptoms"] if s["normalized"] == "Chest Pain"]
        self.assertEqual(len(cp_entities), 1)

    # --------------------------------------------------------------------------
    # 14. ClinicalEntity Contract Parity
    # --------------------------------------------------------------------------
    def test_19_clinical_entity_contract_compatibility(self):
        """Hinglish entities provide both standard contract and legacy keys via to_dict()"""
        note = "Patient ko pet dard hai."
        entities = self.mapper.extract_hinglish_symptoms(note)
        ent = entities[0]
        d = ent.to_dict()

        # Contract keys
        self.assertIn("entity_type", d)
        self.assertIn("source_text", d)
        self.assertIn("normalized_value", d)
        self.assertIn("source_start", d)
        self.assertIn("source_end", d)
        self.assertIn("attributes", d)
        self.assertIn("extraction_method", d)
        self.assertIn("review_status", d)

        # Legacy keys
        self.assertIn("category", d)
        self.assertIn("text", d)
        self.assertIn("normalized", d)
        self.assertIn("start_char", d)
        self.assertIn("end_char", d)
        self.assertIn("source_sentence", d)
        self.assertIn("assertion", d)
        self.assertIn("temporality", d)
        self.assertIn("is_negated", d)

    # --------------------------------------------------------------------------
    # 15. Regression Tests: Decimal Doses, Investigation Status, K/C/O, Acute Ward
    # --------------------------------------------------------------------------
    def test_20_regressions_dosage_investigation_kco_acuteward(self):
        """Verify no regressions in decimal dosages, investigations, shorthand, or acute ward"""
        # Decimal dosage fidelity
        res_med = self.extractor.extract("Administer Digoxin 0.25 mg mane and Metoprolol 12.5 mg BD.")
        digoxin = next((m for m in res_med["medications"] if m["text"].lower() == "digoxin"), None)
        self.assertIsNotNone(digoxin)
        self.assertEqual(digoxin["dosage"], "0.25 mg")
        self.assertIn(digoxin["frequency"], ["MANE", "mane"])

        # Investigation status
        res_inv = self.extractor.extract("CT head is pending.")
        ct_head = next((i for i in res_inv["investigations"] if "ct" in i["text"].lower()), None)
        self.assertIsNotNone(ct_head)
        self.assertEqual(ct_head["status"], "Pending")

        # Shorthand K/C/O
        res_kco = self.extractor.extract("Patient is K/C/O Type 2 Diabetes and HTN.")
        dm_cond = next((c for c in res_kco["conditions"] if "diabetes" in c["normalized"].lower()), None)
        self.assertIsNotNone(dm_cond)
        self.assertTrue(dm_cond["is_historical"])
        self.assertEqual(dm_cond["temporality"], "Historical")

        # Acute ward safety: must not extract headache
        res_ward = self.extractor.extract("Patient admitted to acute ward yesterday.")
        ha = next((s for s in res_ward["symptoms"] if "headache" in s["normalized"].lower()), None)
        self.assertIsNone(ha, "Regression: 'acute ward' triggered headache!")


if __name__ == "__main__":
    unittest.main()
