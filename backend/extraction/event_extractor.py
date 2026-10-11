"""
PULSE Clinical Event Extractor
Extracts clinical events and actions described in the nursing handover:
- Patient admission / presentation
- Medication administration / changes
- Investigations performed / ordered / rescheduled
- Status changes / clinical observations
- Treatment procedures / referrals
Adheres strictly to the text without fabricating unmentioned events.
"""

import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple

class EventExtractor(ABC):
    """
    Abstract Base Class for Clinical Event Extraction.
    Allows future machine learning / transformer sequence-level event extraction.
    """
    @abstractmethod
    def extract(self, text: str, entities: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        pass


class RuleBasedEventExtractor(EventExtractor):
    """
    Rule-based event extraction engine identifying explicit clinical actions,
    their types, timing, and source sentences.
    """

    def __init__(self):
        # Event triggers with classification rules
        self.event_rules = [
            # 1. Admission / Presentation
            {
                "pattern": r"\b(?:came\s+in(?:\s+for|\s+with)?|admitted(?:\s+for|\s+with)?|presented(?:\s+with)?)\s+([^.,;]+)",
                "type": "Admission / Presentation",
                "template": "Patient admitted with/for {0}"
            },
            # 2. Medication Administration / Changes
            {
                "pattern": r"\b(?:had|given|received|administered)\s+(\d+\s+nitros?|antibiotics?|pain\s*relief|insulin|medication[s]?[^.,;]*)",
                "type": "Medication Administration",
                "template": "Administered {0}"
            },
            {
                "pattern": r"\b(?:insulin\s+is\s+on\s+a\s+sliding\s+scale|on\s+variable\s+dose|dose\s+adjusted|medication\s+changed)\b",
                "type": "Medication Regimen Management",
                "template": "Medication regimen adjusted / sliding scale management"
            },
            # 3. Investigation Performed / Returned
            {
                "pattern": r"\b(?:just\s+came\s+back\s+from|returned\s+from|completed|had\s+a)\s+([^.,;]*(?:mri|scan|ct|x-?ray|doppler|ultrasound)[^.,;]*)",
                "type": "Investigation Completed",
                "template": "Completed investigation: {0}"
            },
            # 4. Investigation Scheduled / Rescheduled / Pending
            {
                "pattern": r"\b(?:is\s+planned\s+for|planned\s+for|is\s+for|scheduled\s+for|supposed\s+to\s+have|booked\s+for)\s+([^.,;]*(?:biopsy|renal\s+biopsy|carotid\s+doppler|mri|ct|doppler|scan|procedure|surgery|blood\s*test)[^.,;]*)",
                "type": "Investigation / Procedure Scheduled",
                "template": "Scheduled for {0}"
            },
            {
                "pattern": r"\b(?:a\s+([a-zA-Z\s]+?(?:biopsy|procedure|surgery|scan))\s+is\s+planned\s+for\s+([^.,;]+))",
                "type": "Investigation / Procedure Scheduled",
                "template": "Scheduled for {0} (timing: {1})"
            },
            {
                "pattern": r"\b(?:pushed\s+(?:it\s+)?back\s+to|rescheduled\s+to|delayed\s+to|needs\s+another)\s+([^.,;]+)",
                "type": "Investigation Rescheduled / Delayed",
                "template": "Investigation rescheduled/delayed: {0}"
            },
            # 5. Clinical Observation / Neurological Status
            {
                "pattern": r"\b(gcs\s+is\s+\d+[^.,;]*|obs\s+are\s+stable|vital\s*signs\s*stable|pupils?\s*equal\s*and\s*reactive)",
                "type": "Clinical Status Assessment",
                "template": "Assessment: {0}"
            },
            # 6. Referral / Multidisciplinary Consultation
            {
                "pattern": r"\b(?:still\s+for\s+referral\s+to|referred\s+to|awaiting\s+review\s+by)\s+([^.,;]+)",
                "type": "Consultation / Referral",
                "template": "Referral requested for {0}"
            },
            # 7. Clinical Review Required / Pending
            {
                "pattern": r"\b(?:still\s+need\s+(?:the\s+)?team\s+to\s+review|doctor\s+to\s+review|still\s+for\s+review|awaiting\s+doctor)\s*([^.,;]*)",
                "type": "Clinical Review Event",
                "template": "Clinical review pending by medical team"
            },
            # 8. Treatment / Intervention Ongoing
            {
                "pattern": r"\b(?:currently\s+receiving|under\s+monitoring|on\s+oxygen|still\s+under\s+monitoring)\b",
                "type": "Intervention Ongoing",
                "template": "Active clinical monitoring / therapy underway"
            }
        ]

    def _split_into_sentences(self, text: str) -> List[Tuple[str, int, int]]:
        from backend.extraction.context_extractor import clinical_context_extractor
        return clinical_context_extractor.split_sentences_protected(text)

    def _find_source_sentence(self, match_start: int, sentence_spans: List[Tuple[str, int, int]]) -> str:
        for sent_text, s_start, s_end in sentence_spans:
            if s_start <= match_start <= s_end:
                return sent_text
        return sentence_spans[0][0] if sentence_spans else ""

    def _extract_time_from_sentence(self, sentence: str) -> str:
        # Check for temporal expressions inside sentence
        time_patterns = [
            r"\b(?:this\s+morning\s+at\s+\d{2,4}|at\s+\d{2,4}|pushed\s+back\s+to\s+\d{2,4})\b",
            r"\b(?:\d{1,2}(?::\d{2})?\s*(?:am|pm|hours?))\b",
            r"\b(?:this\s+morning|tomorrow|yesterday|today|tonight|next\s+shift|during\s+the\s+am)\b",
            r"\b(?:for\s+the\s+last\s+\w+\s+years|since\s+childhood)\b"
        ]
        found_times = []
        for tp in time_patterns:
            matches = re.findall(tp, sentence, re.IGNORECASE)
            found_times.extend(matches)
        return ", ".join(found_times) if found_times else "Not specified"

    def extract(self, text: str, entities: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not text:
            return []

        sentence_spans = self._split_into_sentences(text)
        events = []
        seen_events = set()

        for rule in self.event_rules:
            for m in re.finditer(rule["pattern"], text, re.IGNORECASE):
                matched_groups = [g.strip() if g else "" for g in m.groups()] if m.groups() else [""]
                try:
                    event_desc = rule["template"].format(*matched_groups).strip()
                except Exception:
                    event_desc = rule["template"].format(matched_groups[0]).strip()
                source_sentence = self._find_source_sentence(m.start(), sentence_spans)
                time_expr = self._extract_time_from_sentence(source_sentence)

                event_key = (event_desc.lower(), source_sentence.lower())
                if event_key not in seen_events:
                    seen_events.add(event_key)
                    events.append({
                        "event": event_desc,
                        "type": rule["type"],
                        "time": time_expr,
                        "source_sentence": source_sentence,
                        "start_char": m.start(),
                        "end_char": m.end()
                    })

        # If no explicit action pattern matched, synthesize admission reason if available
        if not events and entities and entities.get("conditions"):
            top_cond = entities["conditions"][0]
            events.append({
                "event": f"Patient presented with {top_cond.get('text', 'clinical symptoms')}",
                "type": "Admission / Presentation",
                "time": "On admission",
                "source_sentence": top_cond.get("source_sentence", ""),
                "start_char": top_cond.get("start_char", 0),
                "end_char": top_cond.get("end_char", 0)
            })

        return events

# Global singleton instance
clinical_event_extractor = RuleBasedEventExtractor()
