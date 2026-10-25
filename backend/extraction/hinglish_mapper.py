"""
PULSE Validated Hinglish Clinical Expression Mapping Layer
Phase 5 — Step 3: Safe, Auditable Roman-Hindi / Hinglish Clinical Expression Normalizer

Architecture & Clinical Safety Principles:
1. Standardizes clinically validated Hindi/Hinglish expressions written in Roman script
   into structured clinical concepts conforming to the ClinicalEntity contract.
2. Preserves the original source text, exact character offsets, and containing sentence.
3. Sentence-level and clause-level context analysis preserves clinical assertion
   (affirmative, negated, uncertain) and temporality (current, historical, planned).
4. Strictly context-sensitive disambiguation for ambiguous expressions such as 'ghabrahat':
   does NOT automatically equate it with anxiety or cardiac symptoms without explicit cues.
5. Captures unmapped candidate complaints as flagged for review, never silently dropping
   or hallucinating clinical facts.
6. Word-boundary-aware matching prevents false positive collisions on unrelated English words
   (e.g., 'petition', 'ultimatum', 'chakravyuh', 'sardine', 'acute ward').
"""

import re
from typing import Dict, Any, List, Optional, Tuple, Set

from backend.extraction.contract import ClinicalEntity
from backend.extraction.context_extractor import clinical_context_extractor


# ==============================================================================
# Hinglish Clinical Expression Knowledge Base
# ==============================================================================

HINGLISH_CLINICAL_SYMPTOM_MAPPINGS: List[Dict[str, Any]] = [
    # --------------------------------------------------------------------------
    # 1. Core Symptoms (Phase 5, Step 3 Required)
    # --------------------------------------------------------------------------
    {
        "pattern": r"\bchakkar(?:\s+(?:aana|aa\s*rah[aei]|aate\s*hain|aata\s*hai|aane\s*laga|lag\s*rah[aei]|laga|ana|hai|tha|thi))?\b",
        "canonical_concept": "Dizziness",
        "entity_type": "Symptom",
        "rule_id": "HINGLISH_SYM_DIZZINESS",
        "clinical_category": "Neurological / Vestibular",
        "review_status": "confirmed",
        "description": "Roman-Hindi expression for dizziness / vertigo"
    },
    {
        "pattern": r"\b(?:ulti(?:\s+(?:hui|aa\s*rah[aei]|ho\s*rah[aei]|aana|hone\s*laga|lagi|hui\s*thi|hai|tha|thi))?|ultiy?a(?:n)?)\b",
        "canonical_concept": "Vomiting",
        "entity_type": "Symptom",
        "rule_id": "HINGLISH_SYM_VOMITING",
        "clinical_category": "Gastrointestinal",
        "review_status": "confirmed",
        "description": "Roman-Hindi expression for vomiting / emesis"
    },
    {
        "pattern": r"\b(?:ch+a+t+i|seene|sine)\s*(?:m[ei]+n?\s*)?dard\b",
        "canonical_concept": "Chest Pain",
        "entity_type": "Symptom",
        "rule_id": "HINGLISH_SYM_CHEST_PAIN",
        "clinical_category": "Cardiovascular / Thoracic",
        "review_status": "confirmed",
        "description": "Roman-Hindi expression for chest pain / discomfort"
    },
    {
        "pattern": r"\b(?:pet|pait)\s*(?:m[ei]+n?\s*)?dard\b|\b(?:pet|pait)\s*kharab\b",
        "canonical_concept": "Abdominal Pain",
        "entity_type": "Symptom",
        "rule_id": "HINGLISH_SYM_ABDOMINAL_PAIN",
        "clinical_category": "Gastrointestinal",
        "review_status": "confirmed",
        "description": "Roman-Hindi expression for abdominal pain / stomach upset"
    },
    {
        "pattern": r"\b(?:tez\s+|halka\s+|tez\s+sa\s+)?bukha+r(?:\s+(?:aana|aa\s*rah[aei]|hai|tha|thi))?\b",
        "canonical_concept": "Fever",
        "entity_type": "Symptom",
        "rule_id": "HINGLISH_SYM_FEVER",
        "clinical_category": "Constitutional",
        "review_status": "confirmed",
        "description": "Roman-Hindi expression for fever / pyrexia"
    },
    {
        "pattern": r"\b(?:sa+ns|dum)\s+(?:lene\s*(?:m[ei]+n?\s*)?(?:dikkat|takleef|pareshani)|phool(?:na|\s+rah[aei]\s*hai|\s+rahe\s*hain)?|ghutna)\b",
        "canonical_concept": "Breathing Difficulty (Dyspnea)",
        "entity_type": "Symptom",
        "rule_id": "HINGLISH_SYM_DYSPNEA",
        "clinical_category": "Respiratory",
        "review_status": "confirmed",
        "description": "Roman-Hindi expression for shortness of breath / breathing difficulty"
    },
    {
        "pattern": r"\b(?:tez\s+|so?okh[ie]\s+|balgam\s+wali\s+)?kha[n]?si(?:\s+(?:aana|aa\s*rah[aei]|chal\s*rah[aei]|hai|thi))?\b",
        "canonical_concept": "Cough",
        "entity_type": "Symptom",
        "rule_id": "HINGLISH_SYM_COUGH",
        "clinical_category": "Respiratory",
        "review_status": "confirmed",
        "description": "Roman-Hindi expression for cough (productive or dry)"
    },
    {
        "pattern": r"\b(?:s[ai]r)\s*(?:m[ei]+n?\s*)?dard(?:\s+ho\s*rah[aei])?\b",
        "canonical_concept": "Headache",
        "entity_type": "Symptom",
        "rule_id": "HINGLISH_SYM_HEADACHE",
        "clinical_category": "Neurological",
        "review_status": "confirmed",
        "description": "Roman-Hindi expression for headache / cephalea"
    },
    {
        "pattern": r"\b(?:bahut\s+)?kam[zj]ori(?:\s+(?:lagna|lag\s*rah[aei]|mehsus\s+hona|aana|hai|thi))?\b",
        "canonical_concept": "Weakness",
        "entity_type": "Symptom",
        "rule_id": "HINGLISH_SYM_WEAKNESS",
        "clinical_category": "Constitutional",
        "review_status": "confirmed",
        "description": "Roman-Hindi expression for generalized weakness / asthenia"
    },

    # --------------------------------------------------------------------------
    # 2. Additional Clinically Justified Hinglish Symptoms
    # --------------------------------------------------------------------------
    {
        "pattern": r"\b(?:dast|patla\s+dast|loose\s+motions?)\b",
        "canonical_concept": "Diarrhea",
        "entity_type": "Symptom",
        "rule_id": "HINGLISH_SYM_DIARRHEA",
        "clinical_category": "Gastrointestinal",
        "review_status": "confirmed",
        "description": "Roman-Hindi expression for loose stools / diarrhea"
    },
    {
        "pattern": r"\b(?:thand\s+lagna|thand\s+lag\s*rah[aei]|kapkapi)\b",
        "canonical_concept": "Chills / Rigors",
        "entity_type": "Symptom",
        "rule_id": "HINGLISH_SYM_CHILLS",
        "clinical_category": "Constitutional",
        "review_status": "confirmed",
        "description": "Roman-Hindi expression for chills or rigors"
    },
    {
        "pattern": r"\b(?:soojan|sujan)(?:\s+(?:hai|aayi|aa\s*gayi))?\b",
        "canonical_concept": "Swelling / Edema",
        "entity_type": "Symptom",
        "rule_id": "HINGLISH_SYM_SWELLING",
        "clinical_category": "Constitutional",
        "review_status": "confirmed",
        "description": "Roman-Hindi expression for peripheral swelling / edema"
    },
    {
        "pattern": r"\b(?:(?:ch+a+t+i|seene|sine|pet|gale)\s*(?:m[ei]+n?\s*))?jalan\b",
        "canonical_concept": "Heartburn / Burning Sensation",
        "entity_type": "Symptom",
        "rule_id": "HINGLISH_SYM_HEARTBURN",
        "clinical_category": "Gastrointestinal",
        "review_status": "confirmed",
        "description": "Roman-Hindi expression for retrosternal burning or heartburn"
    },
    {
        "pattern": r"\bneend\s+n[ae]h?i\s+(?:aana|aati|aa\s*rahi)\b",
        "canonical_concept": "Insomnia / Sleep Disturbance",
        "entity_type": "Symptom",
        "rule_id": "HINGLISH_SYM_INSOMNIA",
        "clinical_category": "Constitutional",
        "review_status": "confirmed",
        "description": "Roman-Hindi expression for inability to sleep"
    },
    {
        "pattern": r"\bbhook\s+(?:kam\s+lagna|n[ae]h?i\s+lagna|mar\s+jana)\b",
        "canonical_concept": "Loss of Appetite (Anorexia)",
        "entity_type": "Symptom",
        "rule_id": "HINGLISH_SYM_ANOREXIA",
        "clinical_category": "Constitutional",
        "review_status": "confirmed",
        "description": "Roman-Hindi expression for poor appetite / anorexia"
    },
    {
        "pattern": r"\bbechaini(?:\s+(?:hai|ho\s*rah[aei]))?\b",
        "canonical_concept": "Restlessness / Agitation",
        "entity_type": "Symptom",
        "rule_id": "HINGLISH_SYM_RESTLESSNESS",
        "clinical_category": "Psychological / Constitutional",
        "review_status": "confirmed",
        "description": "Roman-Hindi expression for motor or subjective restlessness"
    }
]


class HinglishClinicalMapper:
    """
    Dedicated mapper for recognizing Roman-Hindi and Hinglish clinical expressions,
    performing context-sensitive disambiguation, and converting to standard ClinicalEntity
    contracts without in-place narrative corruption.
    """

    def __init__(self):
        # Compile symptom patterns
        self.symptom_rules = []
        for r in HINGLISH_CLINICAL_SYMPTOM_MAPPINGS:
            compiled = re.compile(r["pattern"], re.IGNORECASE)
            self.symptom_rules.append((compiled, r))

        # Specialized regex for Ghabrahat
        self.ghabrahat_pattern = re.compile(
            r"\bghabrahat(?:\s+(?:hona|ho\s*rah[aei](?:\s+(?:hai|tha|thi|the))?|hai|thi))?\b",
            re.IGNORECASE
        )

        # Context cues for Ghabrahat disambiguation
        self.ghabrahat_cardiac_cues = re.compile(
            r"\b(?:palpitation|palpitations|tachycardia|dil\s+ki\s+dhadkan|dhadkan|pulse\s+(?:high|fast|elevated|running)|chest\s+tightness|arrhythmia|ecg)\b",
            re.IGNORECASE
        )
        self.ghabrahat_anxiety_cues = re.compile(
            r"\b(?:anxiety|panic|panic\s+attack|bechaini|nervous|nervousness|stress|tension|dar\s+lagna|fear)\b",
            re.IGNORECASE
        )

        # Candidate complaint structure in Hinglish narrative
        self.candidate_complaint_pattern = re.compile(
            r"\b(?:patient\s+ko|mariz\s+ko|pt\s+ko|c/o)\s+([a-zA-Z\s]{3,35}?)\s+(?:ho\s+raha\s+hai|hai|tha|thi|shikayat\s+hai)\b",
            re.IGNORECASE
        )

        # Resolution clause check (e.g., 'pehle se ... thi, ab nahi hai')
        self.resolution_clause_pattern = re.compile(
            r"\b(?:ab\s+n[ae]h?i\s+(?:hai|rahi|raha)?|ab\s+theek\s+hai|ab\s+band\s+hai|resolved|now\s+resolved|not\s+now)\b",
            re.IGNORECASE
        )

    def _find_source_sentence(self, match_start: int, sentence_spans: List[Tuple[str, int, int]]) -> Tuple[str, int, int]:
        for sent_text, s_start, s_end in sentence_spans:
            if s_start <= match_start <= s_end:
                return sent_text, s_start, s_end
        if sentence_spans:
            return sentence_spans[0][0], sentence_spans[0][1], sentence_spans[0][2]
        return "", 0, 0

    def disambiguate_ghabrahat(
        self,
        sentence_text: str,
        full_text: str
    ) -> Tuple[Optional[str], str, str, Dict[str, Any]]:
        """
        Disambiguates the polysemous Roman-Hindi term 'ghabrahat'.
        Rules:
        - If explicit cardiac cues (palpitations, tachycardia, dhadkan) are present:
          maps to 'Palpitations / Cardiac Sensation', rule_id: 'HINGLISH_GHABRAHAT_CARDIAC_CONTEXT', confirmed.
        - If explicit anxiety / panic cues (panic, anxiety, bechaini) are present:
          maps to 'Anxiety / Agitation', rule_id: 'HINGLISH_GHABRAHAT_ANXIETY_CONTEXT', confirmed.
        - Otherwise (ambiguous presentation):
          preserves normalized_value = None, review_status = 'flagged_for_review',
          rule_id: 'HINGLISH_GHABRAHAT_AMBIGUOUS'. Strictly avoids hallucinating cardiac or anxiety etiology.
        """
        # 1. Check for cardiac cues in sentence or full text
        if self.ghabrahat_cardiac_cues.search(sentence_text) or self.ghabrahat_cardiac_cues.search(full_text):
            return (
                "Palpitations / Cardiac Sensation",
                "HINGLISH_GHABRAHAT_CARDIAC_CONTEXT",
                "confirmed",
                {
                    "clinical_domain": "Cardiovascular",
                    "contextual_support": "Explicit cardiac / pulse / palpitation cue in clinical narrative"
                }
            )

        # 2. Check for anxiety cues in sentence or full text
        if self.ghabrahat_anxiety_cues.search(sentence_text) or self.ghabrahat_anxiety_cues.search(full_text):
            return (
                "Anxiety / Agitation",
                "HINGLISH_GHABRAHAT_ANXIETY_CONTEXT",
                "confirmed",
                {
                    "clinical_domain": "Psychiatric / Behavioral",
                    "contextual_support": "Explicit anxiety / panic / stress cue in clinical narrative"
                }
            )

        # 3. Ambiguous - do not infer clinical meaning
        return (
            None,
            "HINGLISH_GHABRAHAT_AMBIGUOUS",
            "flagged_for_review",
            {
                "clinical_domain": "Unspecified Symptom",
                "audit_note": "Ambiguous Roman-Hindi term: preserved as documented without inferring anxiety or cardiac etiology"
            }
        )

    def extract_hinglish_symptoms(
        self,
        text: str,
        sentence_spans: Optional[List[Tuple[str, int, int]]] = None
    ) -> List[ClinicalEntity]:
        """
        Extracts mapped Hinglish clinical symptoms from text with character-accurate offsets,
        sentence-level assertion analysis, and audit trails.
        """
        if not text:
            return []

        if sentence_spans is None:
            sentence_spans = clinical_context_extractor.split_sentences_protected(text)

        entities: List[ClinicalEntity] = []
        seen_spans: Set[Tuple[int, int]] = set()

        # 1. Standard Mapped Hinglish Symptoms
        for compiled_pat, meta in self.symptom_rules:
            for m in compiled_pat.finditer(text):
                span = (m.start(), m.end())
                if span in seen_spans:
                    continue

                matched_text = m.group(0).strip()
                sent_text, s_start, s_end = self._find_source_sentence(m.start(), sentence_spans)

                # Context & Assertion analysis via clinical context extractor
                ctx = clinical_context_extractor.analyze_assertion(matched_text, m.start(), m.end(), text)

                # Build audit attributes
                attributes = {
                    "assertion": ctx["assertion"],
                    "temporality": ctx["temporality"],
                    "is_negated": ctx["is_negated"],
                    "is_uncertain": ctx["is_uncertain"],
                    "is_historical": ctx["is_historical"],
                    "is_planned": ctx["is_planned"],
                    "assertion_cue": ctx.get("cue"),
                    "rule_id": meta["rule_id"],
                    "canonical_concept": meta["canonical_concept"],
                    "clinical_category": meta["clinical_category"],
                    "language_script": "Roman-Hindi (Hinglish)",
                    "description": meta["description"]
                }

                # Check for historical + current resolution distinction
                # e.g., "Patient ko pehle se khansi thi, ab nahi hai."
                if ctx["is_historical"] and self.resolution_clause_pattern.search(sent_text):
                    res_m = self.resolution_clause_pattern.search(sent_text)
                    attributes["historical_context"] = "documented past episode"
                    attributes["current_status"] = "absent / resolved"
                    attributes["resolution_cue"] = res_m.group(0) if res_m else "ab nahi hai"

                ent = ClinicalEntity(
                    entity_type=meta["entity_type"],
                    source_text=matched_text,
                    normalized_value=meta["canonical_concept"],
                    source_start=m.start(),
                    source_end=m.end(),
                    attributes=attributes,
                    evidence_text=sent_text,
                    extraction_method="hinglish_expression_mapper",
                    review_status=meta["review_status"],
                    confidence_score=0.95
                )

                entities.append(ent)
                seen_spans.add(span)

        # 2. Context-Sensitive Ghabrahat Handling
        for m in self.ghabrahat_pattern.finditer(text):
            span = (m.start(), m.end())
            if span in seen_spans:
                continue

            matched_text = m.group(0).strip()
            sent_text, s_start, s_end = self._find_source_sentence(m.start(), sentence_spans)
            ctx = clinical_context_extractor.analyze_assertion(matched_text, m.start(), m.end(), text)

            concept, rule_id, rev_status, extra_attrs = self.disambiguate_ghabrahat(sent_text, text)

            attributes = {
                "assertion": ctx["assertion"],
                "temporality": ctx["temporality"],
                "is_negated": ctx["is_negated"],
                "is_uncertain": ctx["is_uncertain"],
                "is_historical": ctx["is_historical"],
                "is_planned": ctx["is_planned"],
                "assertion_cue": ctx.get("cue"),
                "rule_id": rule_id,
                "canonical_concept": concept,
                "language_script": "Roman-Hindi (Hinglish)",
                **extra_attrs
            }

            ent = ClinicalEntity(
                entity_type="Symptom",
                source_text=matched_text,
                normalized_value=concept,
                source_start=m.start(),
                source_end=m.end(),
                attributes=attributes,
                evidence_text=sent_text,
                extraction_method="hinglish_expression_mapper",
                review_status=rev_status,
                confidence_score=0.85 if rev_status == "confirmed" else None
            )

            entities.append(ent)
            seen_spans.add(span)

        return entities

    def extract_unknown_hinglish_candidates(
        self,
        text: str,
        sentence_spans: Optional[List[Tuple[str, int, int]]] = None,
        existing_spans: Optional[Set[Tuple[int, int]]] = None
    ) -> List[ClinicalEntity]:
        """
        Captures unmapped candidate clinical complaints framed in Roman-Hindi syntax
        (e.g., 'Patient ko <phrase> ho raha hai'). Preserves them as flagged for review
        with normalized_value=None, preventing silent omission while strictly avoiding
        fabricated medical concepts.
        """
        if not text:
            return []

        if sentence_spans is None:
            sentence_spans = clinical_context_extractor.split_sentences_protected(text)

        if existing_spans is None:
            existing_spans = set()

        candidates: List[ClinicalEntity] = []

        # List of words to reject if extracted as candidate complaints
        stopwords = {
            "koi", "kuch", "bahut", "thoda", "problem", "takleef", "dikkat", "itna",
            "yeh", "woh", "ab", "pehle", "doctor", "hospital", "ward", "admission"
        }

        for m in self.candidate_complaint_pattern.finditer(text):
            phrase = m.group(1).strip()
            p_start = m.start(1)
            p_end = m.end(1)

            # Check if this span overlaps with any known span
            overlap = any(
                not (p_end <= e_start or p_start >= e_end)
                for e_start, e_end in existing_spans
            )
            if overlap:
                continue

            if phrase.lower() in stopwords or len(phrase) < 3:
                continue

            sent_text, _, _ = self._find_source_sentence(p_start, sentence_spans)
            ctx = clinical_context_extractor.analyze_assertion(phrase, p_start, p_end, text)

            ent = ClinicalEntity(
                entity_type="Symptom",
                source_text=phrase,
                normalized_value=None,  # No supported dictionary mapping
                source_start=p_start,
                source_end=p_end,
                attributes={
                    "assertion": ctx["assertion"],
                    "temporality": ctx["temporality"],
                    "is_negated": ctx["is_negated"],
                    "is_uncertain": ctx["is_uncertain"],
                    "is_historical": ctx["is_historical"],
                    "is_planned": ctx["is_planned"],
                    "assertion_cue": ctx.get("cue"),
                    "rule_id": "HINGLISH_UNKNOWN_CANDIDATE",
                    "language_script": "Roman-Hindi (Hinglish)",
                    "audit_note": "Candidate Hinglish complaint preserved for clinical review without normalization"
                },
                evidence_text=sent_text,
                extraction_method="hinglish_expression_mapper",
                review_status="flagged_for_review",
                confidence_score=None
            )
            candidates.append(ent)
            existing_spans.add((p_start, p_end))

        return candidates

    def normalize_hinglish_expressions(self, text: str) -> List[Dict[str, Any]]:
        """
        Audit-oriented serialization of all extracted Hinglish expressions.
        """
        entities = self.extract_hinglish_symptoms(text)
        return [e.to_dict() for e in entities]


# Global singleton instance
clinical_hinglish_mapper = HinglishClinicalMapper()
