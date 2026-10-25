"""
PULSE Indian Clinical Shorthand Normalizer
Phase 5 — Step 2: Safe, Auditable Clinical Abbreviation & Shorthand Normalization

Architecture & Clinical Safety Principles:
1. Normalizes standard Indian and Commonwealth clinical shorthand without in-place text mutation.
2. Context-sensitive disambiguation for polysemous abbreviations (e.g. 'OD' as Once Daily vs Oculus Dexter vs Overdose).
3. Structured Glasgow Coma Scale (GCS) notation parser preserving component scores only when explicitly documented,
   strictly avoiding component hallucination from total scores.
4. Maintains complete auditability: every normalized term preserves source text, character span, source sentence,
   canonical expansion, rule ID, and review status conforming to the ClinicalEntity contract.
5. Unknown clinical abbreviation candidate preservation (flagged for human review, never silently dropped).
"""

import re
from typing import Dict, Any, List, Optional, Tuple, Set

from backend.extraction.contract import ClinicalEntity


# ==============================================================================
# Master Shorthand Knowledge Base with Validated Medical Expansions
# ==============================================================================

COMMON_CLINICAL_SHORTHANDS: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # A. Indian & Commonwealth Clinical Workflow Shorthands
    # -------------------------------------------------------------------------
    {
        "pattern": r"\b(?:k\s*[\/\.]?\s*c\s*[\/\.]?\s*o|kco)\b",
        "canonical_abbr": "K/C/O",
        "expansion": "Known Case Of",
        "category": "Clinical History / Comorbidity Shorthand",
        "rule_id": "IND_ABBR_KCO",
        "clinical_role": "history_indicator"
    },
    {
        "pattern": r"\b(?:c\s*[\/\.]\s*o)\b",
        "canonical_abbr": "C/O",
        "expansion": "Complaining Of",
        "category": "Symptom / Presentation Shorthand",
        "rule_id": "IND_ABBR_CO",
        "clinical_role": "symptom_indicator"
    },
    {
        "pattern": r"\b(?:s\s*[\/\.]\s*b)\b",
        "canonical_abbr": "S/B",
        "expansion": "Seen By",
        "category": "Clinician Review Shorthand",
        "rule_id": "IND_ABBR_SB",
        "clinical_role": "review_indicator"
    },
    {
        "pattern": r"\b(?:b\s*[\/\.]\s*l|bilat(?:eral)?)\b",
        "canonical_abbr": "B/L",
        "expansion": "Bilateral",
        "category": "Anatomical Modifier Shorthand",
        "rule_id": "IND_ABBR_BL",
        "clinical_role": "anatomical_modifier"
    },
    {
        "pattern": r"\b(?:n\s*[\/\.]?\s*a\s*[\/\.]?\s*d)\b",
        "canonical_abbr": "NAD",
        "expansion": "No Abnormality Detected",
        "category": "Clinical Examination Shorthand",
        "rule_id": "IND_ABBR_NAD",
        "clinical_role": "negative_finding"
    },
    {
        "pattern": r"\b(?:r\s*[\/\.]?\s*b\s*[\/\.]?\s*s)\b",
        "canonical_abbr": "RBS",
        "expansion": "Random Blood Sugar",
        "category": "Diagnostic Investigation / Measurement Shorthand",
        "rule_id": "IND_ABBR_RBS",
        "clinical_role": "glycemic_investigation"
    },
    {
        "pattern": r"\b(?:c\s*[\/\.]?\s*b\s*[\/\.]?\s*c)\b",
        "canonical_abbr": "CBC",
        "expansion": "Complete Blood Count",
        "category": "Diagnostic Investigation Shorthand",
        "rule_id": "IND_ABBR_CBC",
        "clinical_role": "hematology_investigation"
    },
    {
        "pattern": r"\b(?:u\s*[\/\.]?\s*s\s*[\/\.]?\s*g)\b",
        "canonical_abbr": "USG",
        "expansion": "Ultrasonography (Ultrasound)",
        "category": "Diagnostic Investigation Shorthand",
        "rule_id": "IND_ABBR_USG",
        "clinical_role": "radiology_investigation"
    },
    {
        "pattern": r"\b(?:c\s*[\/\.]?\s*t)\b(?!\s*head\b)",
        "canonical_abbr": "CT",
        "expansion": "Computed Tomography",
        "category": "Diagnostic Investigation Shorthand",
        "rule_id": "IND_ABBR_CT",
        "clinical_role": "radiology_investigation"
    },
    {
        "pattern": r"\b(?:m\s*[\/\.]?\s*r\s*[\/\.]?\s*i)\b",
        "canonical_abbr": "MRI",
        "expansion": "Magnetic Resonance Imaging",
        "category": "Diagnostic Investigation Shorthand",
        "rule_id": "IND_ABBR_MRI",
        "clinical_role": "radiology_investigation"
    },
    {
        "pattern": r"\b(?:e\s*[\/\.]?\s*c\s*[\/\.]?\s*g|e\s*[\/\.]?\s*k\s*[\/\.]?\s*g)\b",
        "canonical_abbr": "ECG",
        "expansion": "Electrocardiogram",
        "category": "Diagnostic Investigation Shorthand",
        "rule_id": "IND_ABBR_ECG",
        "clinical_role": "cardiac_investigation"
    },
    {
        "pattern": r"\b(?:o\s*[\/\.]?\s*p\s*[\/\.]?\s*d)\b",
        "canonical_abbr": "OPD",
        "expansion": "Outpatient Department",
        "category": "Clinical Location / Referral Shorthand",
        "rule_id": "IND_ABBR_OPD",
        "clinical_role": "location_referral"
    },
    {
        "pattern": r"\b(?:o\s*[\/\.]?\s*h\s*[\/\.]?\s*a[s]?)\b",
        "canonical_abbr": "OHA",
        "expansion": "Oral Hypoglycemic Agent",
        "category": "Medication Class Shorthand",
        "rule_id": "IND_ABBR_OHA",
        "clinical_role": "medication_class"
    },

    # -------------------------------------------------------------------------
    # B. Standard Vital & Clinical Acronyms (Preserving Existing PULSE Mappings)
    # -------------------------------------------------------------------------
    {"pattern": r"\bBP\b", "canonical_abbr": "BP", "expansion": "Blood Pressure", "category": "Vitals", "rule_id": "STD_ABBR_BP"},
    {"pattern": r"\bGCS\b", "canonical_abbr": "GCS", "expansion": "Glasgow Coma Scale", "category": "Neurological", "rule_id": "STD_ABBR_GCS"},
    {"pattern": r"\bBGLS?\b", "canonical_abbr": "BGL", "expansion": "Blood Glucose Level", "category": "Glycemic", "rule_id": "STD_ABBR_BGL"},
    {"pattern": r"\bBSL\b", "canonical_abbr": "BSL", "expansion": "Blood Sugar Level", "category": "Glycemic", "rule_id": "STD_ABBR_BSL"},
    {"pattern": r"\bIV\b", "canonical_abbr": "IV", "expansion": "Intravenous", "category": "Route", "rule_id": "STD_ABBR_IV"},
    {"pattern": r"\bPRN\b", "canonical_abbr": "PRN", "expansion": "Pro Re Nata (As Needed)", "category": "Frequency", "rule_id": "STD_ABBR_PRN"},
    {"pattern": r"\bQID\b", "canonical_abbr": "QID", "expansion": "Quater In Die (Four Times Daily)", "category": "Frequency", "rule_id": "STD_ABBR_QID"},
    {"pattern": r"\bBD\b", "canonical_abbr": "BD", "expansion": "Bis In Die (Twice Daily)", "category": "Frequency", "rule_id": "STD_ABBR_BD"},
    {"pattern": r"\bTDS\b", "canonical_abbr": "TDS", "expansion": "Ter Die Sumendum (Three Times Daily)", "category": "Frequency", "rule_id": "STD_ABBR_TDS"},
    {"pattern": r"\bAF\b", "canonical_abbr": "AF", "expansion": "Atrial Fibrillation", "category": "Condition", "rule_id": "STD_ABBR_AF"},
    {"pattern": r"\bCOPD\b", "canonical_abbr": "COPD", "expansion": "Chronic Obstructive Pulmonary Disease", "category": "Condition", "rule_id": "STD_ABBR_COPD"},
    {"pattern": r"\bDM\b", "canonical_abbr": "DM", "expansion": "Diabetes Mellitus", "category": "Condition", "rule_id": "STD_ABBR_DM"},
    {"pattern": r"\bHPN\b", "canonical_abbr": "HPN", "expansion": "Hypertension", "category": "Condition", "rule_id": "STD_ABBR_HPN"},
    {"pattern": r"\bHTN\b", "canonical_abbr": "HTN", "expansion": "Hypertension", "category": "Condition", "rule_id": "STD_ABBR_HTN"},
    {"pattern": r"\bUTI\b", "canonical_abbr": "UTI", "expansion": "Urinary Tract Infection", "category": "Condition", "rule_id": "STD_ABBR_UTI"},
    {"pattern": r"\bMRSA\b", "canonical_abbr": "MRSA", "expansion": "Methicillin-Resistant Staphylococcus Aureus", "category": "Infection", "rule_id": "STD_ABBR_MRSA"},
    {"pattern": r"\bOBS\b", "canonical_abbr": "OBS", "expansion": "Observations / Vital Signs", "category": "Vitals", "rule_id": "STD_ABBR_OBS"},
    {"pattern": r"\bCXR\b", "canonical_abbr": "CXR", "expansion": "Chest X-Ray", "category": "Investigation", "rule_id": "STD_ABBR_CXR"},
    {"pattern": r"\bFBC\b", "canonical_abbr": "FBC", "expansion": "Full Blood Count", "category": "Investigation", "rule_id": "STD_ABBR_FBC"},
    {"pattern": r"\bIDC\b", "canonical_abbr": "IDC", "expansion": "Indwelling Catheter", "category": "Treatment", "rule_id": "STD_ABBR_IDC"},
    {"pattern": r"\bADL\b", "canonical_abbr": "ADL", "expansion": "Activities of Daily Living", "category": "Care", "rule_id": "STD_ABBR_ADL"},
    {"pattern": r"\bSOB\b", "canonical_abbr": "SOB", "expansion": "Shortness of Breath", "category": "Symptom", "rule_id": "STD_ABBR_SOB"},
    {"pattern": r"\bPO\b", "canonical_abbr": "PO", "expansion": "Per Os (Orally)", "category": "Route", "rule_id": "STD_ABBR_PO"},
    {"pattern": r"\bNOF\b", "canonical_abbr": "NOF", "expansion": "Neck of Femur", "category": "Anatomy", "rule_id": "STD_ABBR_NOF"},
    {"pattern": r"\bNBM\b", "canonical_abbr": "NBM", "expansion": "Nil By Mouth", "category": "Care", "rule_id": "STD_ABBR_NBM"},
    {"pattern": r"\bCCF\b", "canonical_abbr": "CCF", "expansion": "Congestive Cardiac Failure", "category": "Condition", "rule_id": "STD_ABBR_CCF"},
    {"pattern": r"\bAMI\b", "canonical_abbr": "AMI", "expansion": "Acute Myocardial Infarction", "category": "Condition", "rule_id": "STD_ABBR_AMI"},
    {"pattern": r"\bTIA\b", "canonical_abbr": "TIA", "expansion": "Transient Ischaemic Attack", "category": "Condition", "rule_id": "STD_ABBR_TIA"},
    {"pattern": r"\bCVA\b", "canonical_abbr": "CVA", "expansion": "Cerebrovascular Accident (Stroke)", "category": "Condition", "rule_id": "STD_ABBR_CVA"},
    {"pattern": r"\bDVT\b", "canonical_abbr": "DVT", "expansion": "Deep Vein Thrombosis", "category": "Condition", "rule_id": "STD_ABBR_DVT"},
    {"pattern": r"\bPE\b", "canonical_abbr": "PE", "expansion": "Pulmonary Embolism", "category": "Condition", "rule_id": "STD_ABBR_PE"},
    {"pattern": r"\bOA\b", "canonical_abbr": "OA", "expansion": "Osteoarthritis", "category": "Condition", "rule_id": "STD_ABBR_OA"},
    {"pattern": r"\bRA\b", "canonical_abbr": "RA", "expansion": "Rheumatoid Arthritis", "category": "Condition", "rule_id": "STD_ABBR_RA"},
    {"pattern": r"\bTKR\b", "canonical_abbr": "TKR", "expansion": "Total Knee Replacement", "category": "Procedure", "rule_id": "STD_ABBR_TKR"},
    {"pattern": r"\bTHR\b", "canonical_abbr": "THR", "expansion": "Total Hip Replacement", "category": "Procedure", "rule_id": "STD_ABBR_THR"},
    {"pattern": r"\bMET\b", "canonical_abbr": "MET", "expansion": "Medical Emergency Team", "category": "Emergency", "rule_id": "STD_ABBR_MET"}
]


# ==============================================================================
# Clinical Shorthand Normalizer Class
# ==============================================================================

class ClinicalShorthandNormalizer:
    """
    Normalizes Indian and Commonwealth clinical shorthand with rigorous context-checking,
    GCS component integrity, and audit traceability.
    """

    def __init__(self):
        # Compiled patterns for general abbreviations
        self.abbreviation_rules = []
        for item in COMMON_CLINICAL_SHORTHANDS:
            self.abbreviation_rules.append({
                "compiled_re": re.compile(item["pattern"], re.IGNORECASE),
                "canonical_abbr": item["canonical_abbr"],
                "expansion": item["expansion"],
                "category": item["category"],
                "rule_id": item["rule_id"],
                "clinical_role": item.get("clinical_role", "general_abbreviation")
            })

        # Context cues for OD disambiguation
        self.ophthalmic_cues = re.compile(
            r"\b(?:eyes?|pupils?|vision|cornea|corneal|cataract|oculus|retina|fundus|visual\s*acuity|iop|drops?\s+in|drops?\s+into|re\s*\(right\s*eye\)|le\s*\(left\s*eye\)|os|ou|sluggish|reactive)\b",
            re.IGNORECASE
        )
        self.overdose_cues = re.compile(
            r"\b(?:overdose|overdosed|suicid(?:e|al)|poisoning|toxicity|ingested|consumption\s+of|excess\s+intake)\b|(?:\b(?:drug|paracetamol|pcm|tablet|pill)s?\s+od\b)",
            re.IGNORECASE
        )
        self.medication_cues = re.compile(
            r"(?:\b(?:tab|tablet|inj|injection|syrup|cap|capsule|drops|infusion|dose|dosage)\b|(?:\d+(?:\.\d+)?\s*(?:mg|g|mcg|ml|units?|iu|puffs?))|\b(?:started\s+on|prescribed|administered|given|on\s+tab|on\s+inj|daily|mane|nocte)\b)",
            re.IGNORECASE
        )

        # Medication frequency mapping dictionary
        self.frequency_expansions = {
            "OD": {"canonical": "OD", "expansion": "Once Daily (Omni Die)", "rule_id": "MED_FREQ_OD"},
            "BD": {"canonical": "BD", "expansion": "Twice Daily (Bis In Die)", "rule_id": "MED_FREQ_BD"},
            "BID": {"canonical": "BD", "expansion": "Twice Daily (Bis In Die)", "rule_id": "MED_FREQ_BD"},
            "TDS": {"canonical": "TDS", "expansion": "Three Times Daily (Ter Die Sumendum)", "rule_id": "MED_FREQ_TDS"},
            "TID": {"canonical": "TDS", "expansion": "Three Times Daily (Ter Die Sumendum)", "rule_id": "MED_FREQ_TDS"},
            "QID": {"canonical": "QID", "expansion": "Four Times Daily (Quater In Die)", "rule_id": "MED_FREQ_QID"},
            "SOS": {"canonical": "SOS", "expansion": "As Needed (Si Opus Sit)", "rule_id": "MED_FREQ_SOS"},
            "PRN": {"canonical": "PRN", "expansion": "As Needed (Pro Re Nata)", "rule_id": "MED_FREQ_PRN"},
            "HS": {"canonical": "HS", "expansion": "At Bedtime (Hora Somni)", "rule_id": "MED_FREQ_HS"},
            "STAT": {"canonical": "STAT", "expansion": "Immediately / Single Dose (Statim)", "rule_id": "MED_FREQ_STAT"},
            "MANE": {"canonical": "MANE", "expansion": "Morning (Mane)", "rule_id": "MED_FREQ_MANE"}
        }

    # --------------------------------------------------------------------------
    # 1. Context-Sensitive 'OD' Disambiguation
    # --------------------------------------------------------------------------

    def disambiguate_od(self, start: int, end: int, text: str, local_clause: str) -> Dict[str, Any]:
        """
        Disambiguates 'OD' into:
        1. Medication frequency: Once Daily (Omni Die)
        2. Ophthalmic context: Oculus Dexter (Right Eye)
        3. Toxicology context: Overdose
        4. Ambiguous context: Flagged for review
        """
        # Look around the match within a +/- 60 character local scope
        context_window = text[max(0, start - 60):min(len(text), end + 60)]

        # Check Ophthalmic context first
        if self.ophthalmic_cues.search(context_window) or self.ophthalmic_cues.search(local_clause):
            return {
                "interpretation": "ophthalmic",
                "is_medication_frequency": False,
                "canonical": "OD (Oculus Dexter)",
                "expansion": "Oculus Dexter (Right Eye)",
                "category": "Ophthalmic Examination Shorthand",
                "rule_id": "OPHTHALMIC_OD",
                "review_status": "confirmed"
            }

        # Check Overdose / Toxicology context
        if self.overdose_cues.search(context_window) or self.overdose_cues.search(local_clause):
            return {
                "interpretation": "toxicology",
                "is_medication_frequency": False,
                "canonical": "OD (Overdose)",
                "expansion": "Drug Overdose / Toxicity",
                "category": "Clinical Toxicology Shorthand",
                "rule_id": "TOX_OD",
                "review_status": "confirmed"
            }

        # Check Medication prescription context
        has_med_cue = bool(self.medication_cues.search(local_clause) or self.medication_cues.search(context_window))
        if has_med_cue:
            return {
                "interpretation": "medication_frequency",
                "is_medication_frequency": True,
                "canonical": "OD",
                "expansion": "Once Daily (Omni Die)",
                "category": "Medication Frequency Shorthand",
                "rule_id": "MED_FREQ_OD",
                "review_status": "confirmed"
            }

        # Standalone / Ambiguous OD
        return {
            "interpretation": "ambiguous",
            "is_medication_frequency": False,
            "canonical": "OD",
            "expansion": "OD (Ambiguous Context: Once Daily / Right Eye / Overdose)",
            "category": "Ambiguous Clinical Shorthand",
            "rule_id": "AMBIGUOUS_OD",
            "review_status": "flagged_for_review"
        }

    # --------------------------------------------------------------------------
    # 2. Medication Frequency Extraction & Normalization
    # --------------------------------------------------------------------------

    def extract_medication_frequency(self, local_scope: str, full_text: str, med_start: int, med_end: int) -> Optional[Dict[str, Any]]:
        """
        Extracts and normalizes medication frequency from a local clause scope,
        respecting context sensitivity for OD and supporting Indian prescription shorthand (BD, TDS, SOS, HS, etc.).
        """
        # Find frequency tokens
        # Check standard non-OD frequencies first
        std_pattern = re.compile(
            r"\b(qid|bd|bid|tds|tid|prn|sos|hs|stat|daily|mane|nocte|hourly)\b",
            re.IGNORECASE
        )
        std_match = std_pattern.search(local_scope)
        if std_match:
            raw_token = std_match.group(0).upper()
            mapping = self.frequency_expansions.get(raw_token, {
                "canonical": raw_token,
                "expansion": raw_token,
                "rule_id": f"MED_FREQ_{raw_token}"
            })
            return {
                "matched_text": std_match.group(0),
                "canonical_token": mapping["canonical"],
                "expansion": mapping["expansion"],
                "rule_id": mapping["rule_id"],
                "start": std_match.start(),
                "end": std_match.end()
            }

        # Check OD with context sensitivity
        od_match = re.search(r"\b(o\s*[\/\.]?\s*d)\b", local_scope, re.IGNORECASE)
        if od_match:
            abs_start = med_start + od_match.start()
            abs_end = med_start + od_match.end()
            od_info = self.disambiguate_od(abs_start, abs_end, full_text, local_scope)
            if od_info["is_medication_frequency"]:
                return {
                    "matched_text": od_match.group(0),
                    "canonical_token": "OD",
                    "expansion": od_info["expansion"],
                    "rule_id": od_info["rule_id"],
                    "start": od_match.start(),
                    "end": od_match.end()
                }

        return None

    # --------------------------------------------------------------------------
    # 3. Structured Glasgow Coma Scale (GCS) Parser
    # --------------------------------------------------------------------------

    def parse_gcs(self, text: str, sentence_spans: List[Tuple[str, int, int]]) -> List[Dict[str, Any]]:
        """
        Parses GCS notations without inventing component scores from total scores.
        Formats:
        1. Explicit Component Score: GCS E4 V5 M6 or E3V4M5 -> records eye, verbal, motor, and derived total.
        2. Ratio / Slash Score: GCS 15/15 or GCS 14/15 -> total score 15 or 14; components strictly None.
        3. Integer Score: GCS 15 or GCS: 14 -> total score 15 or 14; components strictly None.
        4. Header notation: GCS E/V/M -> recorded as unscored observation, marked for review.
        """
        results: List[Dict[str, Any]] = []
        seen_spans: Set[Tuple[int, int]] = set()

        def _find_sent(start_char: int) -> str:
            for s_text, s_start, s_end in sentence_spans:
                if s_start <= start_char <= s_end:
                    return s_text
            return ""

        # Pattern 1: Explicit Components (e.g. "GCS E4 V5 M6", "E3 V4 M5", "GCS: E4, V5, M6")
        comp_pattern = re.compile(
            r"\b(?:gcs(?:\s*(?:is|was|of|score\s*is|recorded\s*as)?)?\s*[:=]?\s*)?e\s*([1-4])\s*[\/,; ]\s*v\s*([1-5]|t|intubated)\s*[\/,; ]\s*m\s*([1-6])\b",
            re.IGNORECASE
        )
        for m in comp_pattern.finditer(text):
            span = (m.start(), m.end())
            seen_spans.add(span)
            e_score = int(m.group(1))
            v_raw = m.group(2).strip()
            v_score = int(v_raw) if v_raw.isdigit() else v_raw.upper()
            m_score = int(m.group(3))
            total = (e_score + v_score + m_score) if isinstance(v_score, int) else f"{e_score + m_score}+T"

            matched_text = m.group(0).strip()
            source_sent = _find_sent(m.start())
            results.append({
                "category": "Measurement",
                "type": "Glasgow Coma Scale (GCS)",
                "text": matched_text,
                "normalized": f"Glasgow Coma Scale: {total} (E{e_score} V{v_score} M{m_score})",
                "source_sentence": source_sent,
                "start_char": m.start(),
                "end_char": m.end(),
                "total_score": total,
                "eye_score": e_score,
                "verbal_score": v_score,
                "motor_score": m_score,
                "components_present": True,
                "rule_id": "GCS_COMPONENT_SCORE",
                "review_status": "confirmed",
                "confidence": None,
                "confidence_type": "deterministic_rule",
                "raw_model_probability": None,
                "calibrated": False,
                "rule_source": "Indian Clinical Shorthand Normalizer (GCS)",
                "matching_method": "GCS Component Regex Parser"
            })

        # Pattern 2: Slash / Ratio Score (e.g. "GCS 15/15", "GCS: 14/15")
        ratio_pattern = re.compile(
            r"\b(?:gcs|glasgow\s*coma\s*scale)(?:\s*(?:is|was|of|score\s*(?:is|of)?)?\s*[:=]?\s*)(\d{1,2})\s*\/\s*15\b",
            re.IGNORECASE
        )
        for m in ratio_pattern.finditer(text):
            span = (m.start(), m.end())
            if any(s[0] <= span[0] and span[1] <= s[1] for s in seen_spans):
                continue
            seen_spans.add(span)
            score_val = int(m.group(1))
            matched_text = m.group(0).strip()
            source_sent = _find_sent(m.start())
            results.append({
                "category": "Measurement",
                "type": "Glasgow Coma Scale (GCS)",
                "text": matched_text,
                "normalized": f"Glasgow Coma Scale: {score_val}/15",
                "source_sentence": source_sent,
                "start_char": m.start(),
                "end_char": m.end(),
                "total_score": score_val,
                "eye_score": None,      # Strictly NOT hallucinated
                "verbal_score": None,   # Strictly NOT hallucinated
                "motor_score": None,    # Strictly NOT hallucinated
                "components_present": False,
                "rule_id": "GCS_RATIO_SCORE",
                "review_status": "confirmed",
                "confidence": None,
                "confidence_type": "deterministic_rule",
                "raw_model_probability": None,
                "calibrated": False,
                "rule_source": "Indian Clinical Shorthand Normalizer (GCS)",
                "matching_method": "GCS Ratio Score Regex Parser"
            })

        # Pattern 3: Simple Score (e.g. "GCS 15", "GCS was 14", "GCS: 12")
        simple_pattern = re.compile(
            r"\b(?:gcs|glasgow\s*coma\s*scale)(?:\s*(?:is|was|of|score\s*(?:is|of)?)?\s*[:=]?\s*)(\d{1,2})\b(?!\s*\/)",
            re.IGNORECASE
        )
        for m in simple_pattern.finditer(text):
            span = (m.start(), m.end())
            if any(s[0] <= span[0] and span[1] <= s[1] for s in seen_spans):
                continue
            seen_spans.add(span)
            score_val = int(m.group(1))
            if not (3 <= score_val <= 15):
                continue  # Out-of-range clinical guard
            matched_text = m.group(0).strip()
            source_sent = _find_sent(m.start())
            results.append({
                "category": "Measurement",
                "type": "Glasgow Coma Scale (GCS)",
                "text": matched_text,
                "normalized": f"Glasgow Coma Scale: {score_val}",
                "source_sentence": source_sent,
                "start_char": m.start(),
                "end_char": m.end(),
                "total_score": score_val,
                "eye_score": None,      # Strictly NOT hallucinated
                "verbal_score": None,   # Strictly NOT hallucinated
                "motor_score": None,    # Strictly NOT hallucinated
                "components_present": False,
                "rule_id": "GCS_TOTAL_SCORE",
                "review_status": "confirmed",
                "confidence": None,
                "confidence_type": "deterministic_rule",
                "raw_model_probability": None,
                "calibrated": False,
                "rule_source": "Indian Clinical Shorthand Normalizer (GCS)",
                "matching_method": "GCS Integer Score Regex Parser"
            })

        # Pattern 4: Unscored Notation (e.g. "GCS E/V/M")
        unscored_pattern = re.compile(r"\bgcs\s*e\s*[\/]\s*v\s*[\/]\s*m\b", re.IGNORECASE)
        for m in unscored_pattern.finditer(text):
            span = (m.start(), m.end())
            if any(s[0] <= span[0] and span[1] <= s[1] for s in seen_spans):
                continue
            seen_spans.add(span)
            matched_text = m.group(0).strip()
            source_sent = _find_sent(m.start())
            results.append({
                "category": "Measurement",
                "type": "Glasgow Coma Scale (GCS)",
                "text": matched_text,
                "normalized": "Glasgow Coma Scale: Unquantified (E/V/M Protocol)",
                "source_sentence": source_sent,
                "start_char": m.start(),
                "end_char": m.end(),
                "total_score": None,
                "eye_score": None,
                "verbal_score": None,
                "motor_score": None,
                "components_present": False,
                "rule_id": "GCS_UNSCORED_HEADER",
                "review_status": "flagged_for_review",
                "confidence": None,
                "confidence_type": "deterministic_rule",
                "raw_model_probability": None,
                "calibrated": False,
                "rule_source": "Indian Clinical Shorthand Normalizer (GCS)",
                "matching_method": "GCS Unquantified Header Pattern"
            })

        return results

    # --------------------------------------------------------------------------
    # 4. Master Normalization Pipeline for Clinical Abbreviations
    # --------------------------------------------------------------------------

    def normalize_abbreviations(self, text: str, sentence_spans: List[Tuple[str, int, int]]) -> List[Dict[str, Any]]:
        """
        Scans text for clinical shorthand abbreviations, applies disambiguation,
        preserves exact source spans and character offsets, and returns auditable dictionary records.
        """
        output_list: List[Dict[str, Any]] = []
        seen_matches: Set[Tuple[int, int]] = set()

        def _find_sent(start_char: int) -> str:
            for s_text, s_start, s_end in sentence_spans:
                if s_start <= start_char <= s_end:
                    return s_text
            return ""

        # 1. Match known clinical abbreviation rules
        for rule in self.abbreviation_rules:
            for m in rule["compiled_re"].finditer(text):
                start, end = m.start(), m.end()
                span = (start, end)
                if span in seen_matches:
                    continue

                matched_text = m.group(0).strip()
                source_sent = _find_sent(start)

                # Special handling for NAD: check if in distress context
                if rule["canonical_abbr"] == "NAD":
                    s_lower = source_sent.lower()
                    if any(c in s_lower for c in ["distress", "sitting comfortably", "lying comfortably", "patient in nad", "looks comfortable"]):
                        expansion = "No Apparent Distress"
                    else:
                        expansion = "No Abnormality Detected"
                else:
                    expansion = rule["expansion"]

                seen_matches.add(span)
                record = {
                    "abbreviation": matched_text,
                    "expansion": expansion,
                    "normalized": expansion,
                    "canonical_abbr": rule["canonical_abbr"],
                    "category": rule["category"],
                    "rule_id": rule["rule_id"],
                    "clinical_role": rule["clinical_role"],
                    "review_status": "confirmed",
                    "source_sentence": source_sent,
                    "start_char": start,
                    "end_char": end,

                    # Standard ClinicalEntity Contract fields
                    "entity_type": "Clinical_Abbreviation",
                    "source_text": matched_text,
                    "normalized_value": expansion,
                    "source_start": start,
                    "source_end": end,
                    "attributes": {
                        "canonical_abbr": rule["canonical_abbr"],
                        "expansion": expansion,
                        "rule_id": rule["rule_id"],
                        "category": rule["category"],
                        "clinical_role": rule["clinical_role"]
                    },
                    "evidence_text": source_sent,
                    "extraction_method": "indian_clinical_shorthand_normalizer",
                    "confidence_score": 1.0
                }
                output_list.append(record)

        # 2. Match standalone 'OD' occurrences and disambiguate
        od_re = re.compile(r"\b(o\s*[\/\.]?\s*d)\b", re.IGNORECASE)
        for m in od_re.finditer(text):
            start, end = m.start(), m.end()
            span = (start, end)
            if span in seen_matches:
                continue

            matched_text = m.group(0).strip()
            source_sent = _find_sent(start)
            od_res = self.disambiguate_od(start, end, text, source_sent)

            seen_matches.add(span)
            record = {
                "abbreviation": matched_text,
                "expansion": od_res["expansion"],
                "normalized": od_res["expansion"],
                "canonical_abbr": od_res["canonical"],
                "category": od_res["category"],
                "rule_id": od_res["rule_id"],
                "clinical_role": od_res["interpretation"],
                "review_status": od_res["review_status"],
                "source_sentence": source_sent,
                "start_char": start,
                "end_char": end,

                # Standard ClinicalEntity Contract fields
                "entity_type": "Clinical_Abbreviation",
                "source_text": matched_text,
                "normalized_value": od_res["expansion"],
                "source_start": start,
                "source_end": end,
                "attributes": {
                    "canonical_abbr": od_res["canonical"],
                    "expansion": od_res["expansion"],
                    "rule_id": od_res["rule_id"],
                    "category": od_res["category"],
                    "clinical_role": od_res["interpretation"]
                },
                "evidence_text": source_sent,
                "extraction_method": "indian_clinical_shorthand_normalizer",
                "confidence_score": 1.0 if od_res["review_status"] == "confirmed" else 0.5
            }
            output_list.append(record)

        # 3. Detect and preserve unknown abbreviation candidates (e.g., 2-5 uppercase chars not in dictionary)
        unknown_re = re.compile(r"\b([A-Z]{2,6})\b")
        known_canonicals = {r["canonical_abbr"] for r in self.abbreviation_rules}
        known_canonicals.update({"OD", "IV", "PO", "PRN", "SOS", "BD", "TDS", "QID", "HS", "STAT", "BP", "GCS"})
        disallowed_capitals = {"THE", "AND", "FOR", "WITH", "WAS", "HAD", "HAS", "NOT", "YES", "HER", "HIS", "HIM", "SHE", "AGE", "BED", "DR", "MR", "MS", "MRS"}

        for m in unknown_re.finditer(text):
            start, end = m.start(), m.end()
            span = (start, end)
            if span in seen_matches:
                continue

            token = m.group(1)
            if token in known_canonicals or token in disallowed_capitals:
                continue

            matched_text = m.group(0).strip()
            source_sent = _find_sent(start)
            seen_matches.add(span)

            record = {
                "abbreviation": matched_text,
                "expansion": f"Unknown Shorthand ({matched_text})",
                "normalized": f"Unknown Shorthand ({matched_text})",
                "canonical_abbr": matched_text,
                "category": "Unknown Clinical Shorthand Candidate",
                "rule_id": "UNKNOWN_SHORTHAND_CANDIDATE",
                "clinical_role": "unknown_candidate",
                "review_status": "flagged_for_review",
                "source_sentence": source_sent,
                "start_char": start,
                "end_char": end,

                # Standard ClinicalEntity Contract fields
                "entity_type": "Clinical_Abbreviation",
                "source_text": matched_text,
                "normalized_value": None,  # Strictly NO hallucinated identity
                "source_start": start,
                "source_end": end,
                "attributes": {
                    "canonical_abbr": matched_text,
                    "rule_id": "UNKNOWN_SHORTHAND_CANDIDATE",
                    "category": "Unknown Clinical Shorthand Candidate"
                },
                "evidence_text": source_sent,
                "extraction_method": "unknown_shorthand_detector",
                "confidence_score": 0.5
            }
            output_list.append(record)

        # Sort by start_char
        output_list.sort(key=lambda x: x["start_char"])
        return output_list


# Singleton instance
clinical_shorthand_normalizer = ClinicalShorthandNormalizer()
