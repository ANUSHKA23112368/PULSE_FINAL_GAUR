"""
PULSE Open-Vocabulary Clinical Candidate Extractor
Phase 5 — Step 1: Generalized Clinical Extraction Architecture

Architectural component supporting open-vocabulary candidate extraction:
1. Recognizes candidate clinical entities (medications, investigations, complaints)
   from contextual syntax without requiring hardcoded dictionary membership.
2. Preserves exact source text and character spans.
3. Sets normalized_value = None when canonical mapping is not adequately supported,
   preventing fabricated identities or unsupported diagnoses.
4. Marks all candidate and unclassified entities with review_status="flagged_for_review".
5. Captures unclassified clinical narrative sentences so that novel clinical facts
   are preserved rather than silently dropped.
"""

import re
from typing import Dict, Any, List, Optional, Tuple, Set

from backend.extraction.contract import ClinicalEntity, BaseClinicalExtractor
from backend.extraction.context_extractor import clinical_context_extractor


DISALLOWED_DRUG_WORDS = {
    "bed", "rest", "walk", "exercise", "air", "diet", "fluids", "line",
    "observation", "monitoring", "review", "assistance", "care", "consultation",
    "ward", "hospital", "patient", "morning", "night", "day", "shift"
}

DOSAGE_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?\s*(?:mg|g|mcg|ml|units?|iu|tablets?|capsules?|drops?|puffs?|nitros?))\b",
    re.IGNORECASE
)
FREQUENCY_PATTERN = re.compile(
    r"\b(qid|bd|tds|prn|daily|mane|nocte|hourly|od|hs|bbf|pc|ac|weekly|monthly)\b",
    re.IGNORECASE
)
ROUTE_PATTERN = re.compile(
    r"\b(iv|oral|po|subcut|sc|topical|sublingual|inhal(?:er|ation)|im|pr)\b",
    re.IGNORECASE
)


class OpenVocabularyExtractor(BaseClinicalExtractor):
    """
    Candidate clinical entity extractor operating beyond fixed dictionaries.
    """
    def __init__(self):
        super().__init__(name="open_vocabulary", version="1.0.0", supports_open_vocabulary=True)

        # Contextual prescription patterns (recognizes unseen drugs by prescription framing)
        self.prescription_prefix_pattern = re.compile(
            r"\b(?:tab|tablet|inj|injection|syrup|capsule|cap|infusion\s+of|drops?)\s+([a-zA-Z][a-zA-Z0-9\-\/]{2,})\b",
            re.IGNORECASE
        )
        self.prescription_verb_pattern = re.compile(
            r"\b(?:started\s+on|commenced\s+on|prescribed|administered|dose\s+of)\s+([a-zA-Z][a-zA-Z0-9\-\/]{2,})\b",
            re.IGNORECASE
        )

        # Contextual investigation triggers
        self.investigation_trigger_pattern = re.compile(
            r"\b(?:test\s+(?:of|for)|ordered\s+(?:a|an)?|order\s+for|awaiting\s+(?:results?\s+of|report\s+of|findings?\s+of)|scheduled\s+for|sent\s+for)\s+([a-zA-Z0-9\-\s]{2,35}?)(?=\s+(?:is\s+pending|pending|completed|done|ordered|next\s+shift)|[.,;\n]|$)",
            re.IGNORECASE
        )

    def _split_into_sentences(self, text: str) -> List[Tuple[str, int, int]]:
        return clinical_context_extractor.split_sentences_protected(text)

    def _find_source_sentence(self, match_start: int, sentence_spans: List[Tuple[str, int, int]]) -> str:
        for sent_text, s_start, s_end in sentence_spans:
            if s_start <= match_start <= s_end:
                return sent_text
        return sentence_spans[0][0] if sentence_spans else ""

    def _determine_investigation_status(self, source_sent: str, is_negated: bool) -> str:
        if is_negated:
            return "Not Ordered / Denied"
        s_lower = source_sent.lower()
        if (
            re.search(r"\b(?:awaiting|waiting\s+for)\b.*?\b(?:results?|reports?|findings?)\b", s_lower)
            or re.search(r"\b(?:awaiting|waiting\s+for)\b", s_lower)
            or re.search(r"\b(?:results?|reports?|findings?)\s+(?:are\s+)?(?:awaited|pending)\b", s_lower)
        ):
            return "Awaiting Results"
        if re.search(r"\b(?:sent(?:\s+off|\s+to\s+lab|\s+for\s+testing)?|collected)\b", s_lower) and not re.search(r"\b(?:completed|returned|received)\b", s_lower):
            return "Sent"
        if re.search(r"\b(?:completed|done|returned\s+from|came\s+back\s+from|had\s+a)\b", s_lower) and not re.search(r"\b(?:is\s+pending|pending|planned(?:\s+for)?|scheduled(?:\s+for)?|booked(?:\s+for)?)\b", s_lower):
            return "Completed"
        if re.search(r"\b(?:is\s+pending|pending|planned(?:\s+for)?|scheduled(?:\s+for)?|booked(?:\s+for)?|to\s+be\s+done|needs\s+another|ordered|order\s+test)\b", s_lower):
            return "Pending"
        return "Unspecified"

    def extract_candidate_medications(
        self,
        text: str,
        sentence_spans: List[Tuple[str, int, int]],
        known_med_spans: Set[Tuple[int, int]]
    ) -> List[ClinicalEntity]:
        """
        Extracts open-vocabulary candidate medications that are not present in fixed lexicons.
        """
        candidates = []
        seen_spans = set(known_med_spans)

        # 1. Prefix matches (e.g., 'tab Pantoprazole 40mg', 'inj Levetiracetam')
        for pat in [self.prescription_prefix_pattern, self.prescription_verb_pattern]:
            for m in pat.finditer(text):
                drug_name = m.group(1).strip()
                start_c = m.start(1)
                end_c = m.end(1)

                if any(start_c >= s and end_c <= e for s, e in seen_spans):
                    continue
                if drug_name.lower() in DISALLOWED_DRUG_WORDS or len(drug_name) < 3:
                    continue

                source_sent = self._find_source_sentence(start_c, sentence_spans)
                ctx = clinical_context_extractor.analyze_assertion(drug_name, start_c, end_c, text)

                # Search local sentence for dose, route, freq
                from backend.extraction.shorthand_normalizer import clinical_shorthand_normalizer
                dose_m = DOSAGE_PATTERN.search(source_sent)
                freq_info = clinical_shorthand_normalizer.extract_medication_frequency(source_sent, text, start_c, end_c)
                route_m = ROUTE_PATTERN.search(source_sent)

                # Infer oral route from 'tab' or 'tablet'
                inferred_route = route_m.group(0).upper() if route_m else ("PO" if "tab" in m.group(0).lower() or "cap" in m.group(0).lower() else "Unspecified route")
                inferred_dose = dose_m.group(0) if dose_m else "Unspecified dose in text"
                if freq_info:
                    inferred_freq = freq_info["canonical_token"]
                else:
                    freq_m = FREQUENCY_PATTERN.search(source_sent)
                    inferred_freq = freq_m.group(0).upper() if freq_m else "Unspecified frequency"

                seen_spans.add((start_c, end_c))
                candidates.append(ClinicalEntity(
                    entity_type="Medication",
                    source_text=drug_name,
                    evidence_text=source_sent,
                    normalized_value=None,  # Do not invent a normalized identity
                    source_start=start_c,
                    source_end=end_c,
                    attributes={
                        "dosage": inferred_dose,
                        "frequency": inferred_freq,
                        "route": inferred_route,
                        "assertion": ctx["assertion"],
                        "temporality": ctx["temporality"],
                        "is_negated": ctx["is_negated"],
                        "is_uncertain": ctx["is_uncertain"],
                        "context_cue": ctx["cue"],
                        "is_candidate": True,
                        "normalization_confidence": "unmapped_open_vocabulary"
                    },
                    extraction_method="open_vocabulary_prescription_pattern",
                    review_status="flagged_for_review",
                    confidence_score=0.75,
                    all_spans=[(start_c, end_c)],
                    occurrences=1
                ))

        return candidates

    def extract_candidate_investigations(
        self,
        text: str,
        sentence_spans: List[Tuple[str, int, int]],
        known_inv_spans: Set[Tuple[int, int]]
    ) -> List[ClinicalEntity]:
        """
        Extracts open-vocabulary candidate investigations (e.g., 'ordered serum ferritin', 'awaiting D-dimer').
        """
        candidates = []
        seen_spans = set(known_inv_spans)

        for m in self.investigation_trigger_pattern.finditer(text):
            inv_name = m.group(1).strip()
            start_c = m.start(1)
            end_c = m.end(1)

            if not inv_name or len(inv_name) < 2 or inv_name.lower() in DISALLOWED_DRUG_WORDS:
                continue
            if any(start_c >= s and end_c <= e for s, e in seen_spans):
                continue

            source_sent = self._find_source_sentence(start_c, sentence_spans)
            ctx = clinical_context_extractor.analyze_assertion(inv_name, start_c, end_c, text)
            inv_status = self._determine_investigation_status(source_sent, ctx["is_negated"])

            seen_spans.add((start_c, end_c))
            candidates.append(ClinicalEntity(
                entity_type="Investigation",
                source_text=inv_name,
                evidence_text=source_sent,
                normalized_value=None,  # Do not invent normalized identity
                source_start=start_c,
                source_end=end_c,
                attributes={
                    "status": inv_status,
                    "assertion": ctx["assertion"],
                    "temporality": ctx["temporality"],
                    "is_negated": ctx["is_negated"],
                    "is_uncertain": ctx["is_uncertain"],
                    "context_cue": ctx["cue"],
                    "is_candidate": True,
                    "normalization_confidence": "unmapped_open_vocabulary"
                },
                extraction_method="open_vocabulary_investigation_pattern",
                review_status="flagged_for_review",
                confidence_score=0.70,
                all_spans=[(start_c, end_c)],
                occurrences=1
            ))

        return candidates

    def extract_unclassified_clauses(
        self,
        text: str,
        sentence_spans: List[Tuple[str, int, int]],
        matched_char_spans: Set[Tuple[int, int]]
    ) -> List[ClinicalEntity]:
        """
        Preserves clinical sentences/clauses that did not match any known dictionary entity,
        ensuring novel clinical narrative is not silently dropped.
        """
        unclassified = []
        for sent_text, s_start, s_end in sentence_spans:
            s_clean = sent_text.strip()
            if len(s_clean) < 15:
                continue

            # Check if this sentence contains any matched entity span
            has_matched_entity = any(
                max(s_start, m_s) < min(s_end, m_e)
                for m_s, m_e in matched_char_spans
            )

            # If no entity from dictionaries was found in this sentence, check if it contains clinical narrative
            if not has_matched_entity:
                lead_spaces = len(sent_text) - len(sent_text.lstrip())
                trail_spaces = len(sent_text) - len(sent_text.rstrip())
                actual_start = s_start + lead_spaces
                actual_end = s_end - trail_spaces

                ctx = clinical_context_extractor.analyze_assertion(s_clean, actual_start, actual_end, text)
                unclassified.append(ClinicalEntity(
                    entity_type="Unclassified_Candidate",
                    source_text=s_clean,
                    evidence_text=s_clean,
                    normalized_value=None,
                    source_start=actual_start,
                    source_end=actual_end,
                    attributes={
                        "assertion": ctx["assertion"],
                        "temporality": ctx["temporality"],
                        "is_negated": ctx["is_negated"],
                        "is_uncertain": ctx["is_uncertain"],
                        "context_cue": ctx["cue"],
                        "unclassified_narrative": True
                    },
                    extraction_method="open_vocabulary_unclassified_phrase",
                    review_status="flagged_for_review",
                    confidence_score=0.50,
                    all_spans=[(actual_start, actual_end)],
                    occurrences=1
                ))

        return unclassified

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Executes open-vocabulary candidate extraction over text.
        """
        if not text:
            return {
                "patient_information": [],
                "conditions": [],
                "symptoms": [],
                "medications": [],
                "investigations": [],
                "treatments": [],
                "measurements": [],
                "abbreviations": [],
                "clinical_risks": [],
                "unclassified_candidates": [],
                "all_entities": []
            }

        sentence_spans = self._split_into_sentences(text)
        known_spans: Set[Tuple[int, int]] = set()

        cand_meds = self.extract_candidate_medications(text, sentence_spans, known_spans)
        for cm in cand_meds:
            if cm.source_start is not None and cm.source_end is not None:
                known_spans.add((cm.source_start, cm.source_end))

        cand_invs = self.extract_candidate_investigations(text, sentence_spans, known_spans)
        for ci in cand_invs:
            if ci.source_start is not None and ci.source_end is not None:
                known_spans.add((ci.source_start, ci.source_end))

        unclassified = self.extract_unclassified_clauses(text, sentence_spans, known_spans)

        all_ents = cand_meds + cand_invs + unclassified

        return {
            "patient_information": [],
            "conditions": [],
            "symptoms": [],
            "medications": [m.to_dict() for m in cand_meds],
            "investigations": [i.to_dict() for i in cand_invs],
            "treatments": [],
            "measurements": [],
            "abbreviations": [],
            "clinical_risks": [],
            "unclassified_candidates": [u.to_dict() for u in unclassified],
            "all_entities": [e.to_dict() for e in all_ents]
        }


# Global singleton
open_vocabulary_extractor = OpenVocabularyExtractor()
from backend.extraction.contract import ExtractorRegistry
ExtractorRegistry.register("open_vocabulary", open_vocabulary_extractor)
