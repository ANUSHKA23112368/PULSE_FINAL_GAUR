"""
PULSE Phase 5 — Step 1: Generalized Clinical Extraction Architecture Regression Tests
Tests:
1. Unified Extraction Contract:
   - entity_type, source_text, normalized_value, source_start, source_end,
     attributes, evidence_text, extraction_method, review_status.
2. Backward Compatibility:
   - Preserves all legacy dictionary keys and values for existing APIs and UI.
3. Open-Vocabulary Candidate Extraction:
   - Recognition of candidate medications and investigations not in hardcoded lexicons.
   - Preserves exact source text without inventing normalized identities or diagnoses.
4. Preservation of Unknown Clinical Narrative Phrases:
   - Non-dictionary clinical sentences are preserved in unclassified_candidates
     and in the structured handover rather than silently dropped.
5. Preservation of P0 & Phase 3 Safety Guardrails:
   - Decimal dosage precision (0.25 mg vs 25 mg), localized attribute binding.
   - Investigation status fidelity (Pending, Sent, Awaiting Results, Completed, Not Ordered).
6. Extractor Registry and BaseClinicalExtractor interface.
"""

import unittest
import sys
import os

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.preprocessing.preprocessor import clinical_preprocessor
from backend.extraction.entity_extractor import clinical_entity_extractor, HybridClinicalEntityExtractor
from backend.extraction.clinical_bert_extractor import clinical_bert_extractor
from backend.extraction.open_vocabulary_extractor import open_vocabulary_extractor
from backend.extraction.contract import ClinicalEntity, BaseClinicalExtractor, ExtractorRegistry
from backend.extraction.event_extractor import clinical_event_extractor
from backend.extraction.temporal_extractor import clinical_temporal_extractor
from backend.extraction.structured_generator import structured_handover_generator


class TestGeneralizedExtractionArchitecture(unittest.TestCase):
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
            "temporal": temporal,
            "pending_tasks": pending,
            "follow_up": follow_up,
            "structured": structured
        }

    # =========================================================================
    # 1. Common Extraction Contract Tests
    # =========================================================================

    def test_common_extraction_contract_fields_presence(self):
        """
        Every entity record must contain all required contract fields:
        entity_type, source_text, normalized_value, source_start, source_end,
        attributes, evidence_text, extraction_method, review_status.
        """
        text = "Administered Digoxin 0.25 mg mane."
        res = self._run_pipeline(text)
        meds = res["entities"]["medications"]
        self.assertTrue(len(meds) > 0, "Expected Digoxin to be extracted")

        entity = meds[0]
        # Standard contract keys
        self.assertIn("entity_type", entity)
        self.assertIn("source_text", entity)
        self.assertIn("normalized_value", entity)
        self.assertIn("source_start", entity)
        self.assertIn("source_end", entity)
        self.assertIn("attributes", entity)
        self.assertIn("evidence_text", entity)
        self.assertIn("extraction_method", entity)
        self.assertIn("review_status", entity)

        self.assertEqual(entity["entity_type"], "Medication")
        self.assertIn("Digoxin", entity["source_text"])
        self.assertIsInstance(entity["attributes"], dict)
        self.assertEqual(entity["attributes"].get("dosage"), "0.25 mg")
        self.assertEqual(entity["attributes"].get("frequency"), "MANE")

    def test_clinical_entity_dataclass_bidirectional_conversion(self):
        """
        ClinicalEntity dataclass to_dict() and from_dict() must preserve contract
        fields as well as legacy fields seamlessly.
        """
        ent = ClinicalEntity(
            entity_type="Medication",
            source_text="Levetiracetam",
            evidence_text="Prescribed Levetiracetam 500mg BD.",
            normalized_value=None,
            source_start=11,
            source_end=24,
            attributes={"dosage": "500mg", "frequency": "BD", "route": "PO", "is_negated": False},
            extraction_method="open_vocabulary_prescription_pattern",
            review_status="flagged_for_review"
        )
        d = ent.to_dict()

        # Contract checks
        self.assertEqual(d["entity_type"], "Medication")
        self.assertEqual(d["source_text"], "Levetiracetam")
        self.assertIsNone(d["normalized_value"])
        self.assertEqual(d["source_start"], 11)
        self.assertEqual(d["source_end"], 24)
        self.assertEqual(d["review_status"], "flagged_for_review")

        # Legacy backward-compatibility checks
        self.assertEqual(d["category"], "Medication")
        self.assertEqual(d["text"], "Levetiracetam")
        self.assertEqual(d["start_char"], 11)
        self.assertEqual(d["end_char"], 24)
        self.assertEqual(d["dosage"], "500mg")
        self.assertEqual(d["frequency"], "BD")
        self.assertEqual(d["route"], "PO")
        self.assertFalse(d["is_negated"])

        # Reconstruct from dict
        reconstructed = ClinicalEntity.from_dict(d)
        self.assertEqual(reconstructed.entity_type, ent.entity_type)
        self.assertEqual(reconstructed.source_text, ent.source_text)
        self.assertEqual(reconstructed.attributes["dosage"], "500mg")

    def test_backward_compatibility_with_existing_legacy_keys(self):
        """
        Legacy keys (category, text, normalized, start_char, end_char, source_sentence,
        is_negated, is_uncertain, etc.) must remain populated on all extracted entities.
        """
        text = "Patient denies headache. CT head completed."
        res = self._run_pipeline(text)
        symps = res["entities"]["symptoms"]
        invs = res["entities"]["investigations"]

        self.assertTrue(len(symps) > 0)
        s = symps[0]
        self.assertEqual(s["category"], "Symptom")
        self.assertEqual(s["text"].lower(), "headache")
        self.assertTrue(s["is_negated"])
        self.assertIn("start_char", s)
        self.assertIn("end_char", s)
        self.assertIn("source_sentence", s)

        self.assertTrue(len(invs) > 0)
        inv = invs[0]
        self.assertEqual(inv["category"], "Investigation")
        self.assertEqual(inv["status"], "Completed")

    # =========================================================================
    # 2. Open-Vocabulary Candidate Extraction Tests
    # =========================================================================

    def test_open_vocabulary_candidate_medication_unseen_in_dictionary(self):
        """
        Unseen medication (e.g. 'Pantoprazole') in a prescription pattern:
        - Must be recognized as a candidate Medication.
        - Must extract supported dosage '40mg', frequency 'OD', route 'PO' (from tab).
        - Must NOT invent a canonical normalized identity (normalized_value is None).
        - Must be marked review_status='flagged_for_review'.
        """
        text = "Started on tab Pantoprazole 40mg OD."
        res = self._run_pipeline(text)
        meds = res["entities"]["medications"]

        panto_matches = [m for m in meds if "pantoprazole" in m.get("source_text", "").lower() or "pantoprazole" in m.get("text", "").lower()]
        self.assertTrue(len(panto_matches) > 0, f"Expected unseen drug Pantoprazole to be recognized as candidate, got: {meds}")

        cand = panto_matches[0]
        self.assertEqual(cand.get("entity_type"), "Medication")
        self.assertEqual(cand.get("source_text"), "Pantoprazole")
        self.assertIsNone(cand.get("normalized_value"), "Must not invent/hallucinate normalized identity for unmapped drug")
        self.assertEqual(cand.get("review_status"), "flagged_for_review")
        self.assertEqual(cand.get("extraction_method"), "open_vocabulary_prescription_pattern")

        # Supported attributes
        attrs = cand.get("attributes", {})
        self.assertEqual(attrs.get("dosage"), "40mg")
        self.assertEqual(attrs.get("frequency"), "OD")
        self.assertEqual(attrs.get("route"), "PO")

    def test_open_vocabulary_candidate_investigation_unseen_in_dictionary(self):
        """
        Unseen diagnostic test (e.g. 'serum ferritin', 'D-dimer'):
        - Must be recognized as candidate Investigation.
        - Must preserve status ('Awaiting Results' or 'Pending').
        - Must NOT invent normalized identity.
        - Must be marked review_status='flagged_for_review'.
        """
        text = "Awaiting results of serum ferritin."
        res = self._run_pipeline(text)
        invs = res["entities"]["investigations"]

        ferritin_matches = [i for i in invs if "ferritin" in i.get("source_text", "").lower() or "ferritin" in i.get("text", "").lower()]
        self.assertTrue(len(ferritin_matches) > 0, f"Expected unseen test serum ferritin to be captured, got: {invs}")

        cand = ferritin_matches[0]
        self.assertEqual(cand.get("entity_type"), "Investigation")
        self.assertIn("ferritin", cand.get("source_text").lower())
        self.assertIsNone(cand.get("normalized_value"), "Must not invent normalized identity for unmapped investigation")
        self.assertEqual(cand.get("review_status"), "flagged_for_review")
        self.assertEqual(cand.get("status"), "Awaiting Results")

    # =========================================================================
    # 3. Preservation of Unknown Clinical Narrative (No Silent Drops)
    # =========================================================================

    def test_preserve_unclassified_clinical_narrative_clauses(self):
        """
        Clinical narrative statements that match no hardcoded dictionary:
        - Must be preserved in entities['unclassified_candidates'].
        - Must be preserved in structured handover under unclassified_observations.
        - Must NOT be silently discarded from the generated summary.
        """
        text = "Patient experienced unexplained progressive tingling in extremities during afternoon shift."
        res = self._run_pipeline(text)
        unclassified = res["entities"].get("unclassified_candidates", [])
        structured = res["structured"]

        self.assertTrue(len(unclassified) > 0, f"Expected unclassified narrative clause to be preserved, got: {res['entities']}")
        unc = unclassified[0]
        self.assertEqual(unc.get("entity_type"), "Unclassified_Candidate")
        self.assertIn("progressive tingling", unc.get("source_text"))
        self.assertEqual(unc.get("review_status"), "flagged_for_review")

        # Must be present in structured handover
        unclassified_obs = structured.get("unclassified_observations", [])
        self.assertTrue(len(unclassified_obs) > 0, f"Expected unclassified observations in structured handover: {structured}")
        self.assertTrue(any("tingling" in obs for obs in unclassified_obs))

    # =========================================================================
    # 4. Preservation of P0 Dosage Fixes and Phase 3 Investigation Safety
    # =========================================================================

    def test_p0_dosage_and_binding_safety_intact(self):
        """
        P0 regression checks must remain 100% intact:
        - Digoxin 0.25 mg mane must extract 0.25 mg and bind mane.
        - Metoprolol 25mg BD must bind BD and not leak mane.
        - Paracetamol 1g PO must extract 1g and route PO.
        """
        text = "Started on Digoxin 0.25mg mane and Metoprolol 25mg BD. Paracetamol 1g PO given for pain."
        res = self._run_pipeline(text)
        meds = res["entities"]["medications"]

        digoxin = next((m for m in meds if "digoxin" in m.get("text", "").lower()), None)
        metoprolol = next((m for m in meds if "metoprolol" in m.get("text", "").lower()), None)
        pcm = next((m for m in meds if "paracetamol" in m.get("text", "").lower()), None)

        self.assertIsNotNone(digoxin)
        self.assertEqual(digoxin.get("dosage"), "0.25mg")
        self.assertEqual(digoxin.get("frequency"), "MANE")

        self.assertIsNotNone(metoprolol)
        self.assertEqual(metoprolol.get("dosage"), "25mg")
        self.assertEqual(metoprolol.get("frequency"), "BD")

        self.assertIsNotNone(pcm)
        self.assertIn("1g", pcm.get("dosage", "").replace(" ", "").lower())
        self.assertEqual(pcm.get("route"), "PO")

    def test_phase_3_investigation_status_safety_intact(self):
        """
        Phase 3 status checks must remain 100% intact:
        - CT head is pending -> status: Pending
        - Awaiting blood culture results -> status: Awaiting Results
        - Blood cultures sent -> status: Sent (not completed)
        - No CT scan ordered -> negated, no pending task created.
        """
        t1 = self._run_pipeline("CT head is pending.")
        ct_inv = next((i for i in t1["entities"]["investigations"] if "ct" in i["text"].lower()), None)
        self.assertEqual(ct_inv.get("status"), "Pending")

        t2 = self._run_pipeline("Awaiting blood culture results.")
        bc_inv = next((i for i in t2["entities"]["investigations"] if "blood culture" in i["text"].lower()), None)
        self.assertEqual(bc_inv.get("status"), "Awaiting Results")

        t3 = self._run_pipeline("Blood cultures sent.")
        bc_sent = next((i for i in t3["entities"]["investigations"] if "blood culture" in i["text"].lower()), None)
        self.assertEqual(bc_sent.get("status"), "Sent")

        t4 = self._run_pipeline("No CT scan has been ordered.")
        ct_neg = next((i for i in t4["entities"]["investigations"] if "ct" in i["text"].lower()), None)
        self.assertTrue(ct_neg.get("is_negated"))
        ct_tasks = [t for t in t4["pending_tasks"] if "ct" in t["task"].lower()]
        self.assertEqual(len(ct_tasks), 0)

    # =========================================================================
    # 5. Extractor Registry and Interface Compliance
    # =========================================================================

    def test_extractor_registry_interface(self):
        """
        ExtractorRegistry must provide registered extractors behind BaseClinicalExtractor.
        """
        avail = ExtractorRegistry.list_available()
        self.assertIn("rule", avail)
        self.assertIn("hybrid", avail)
        self.assertIn("open_vocabulary", avail)

        rule_ext = ExtractorRegistry.get("rule")
        self.assertIsInstance(rule_ext, BaseClinicalExtractor)
        self.assertTrue(rule_ext.supports_open_vocabulary)

        # Flat entity list test
        flat_ents = rule_ext.extract_entities("Administered Digoxin 0.25 mg mane.")
        self.assertTrue(len(flat_ents) > 0)
        self.assertTrue(all(isinstance(e, ClinicalEntity) for e in flat_ents))
        med_ent = next((e for e in flat_ents if e.entity_type == "Medication"), None)
        self.assertIsNotNone(med_ent, "Expected Medication entity in extracted flat entities")
        self.assertEqual(med_ent.source_text, "Digoxin")


if __name__ == "__main__":
    unittest.main()
