"""
PULSE Temporal Information Extractor
Extracts temporal expressions (times, dates, durations, shifts, relative markers)
and associates them with corresponding clinical events and statements.
Adheres strictly to verbatim content without fabricating calendar dates.
"""

import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple

class TemporalExtractor(ABC):
    @abstractmethod
    def extract(self, text: str, events: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        pass


class ClinicalTemporalExtractor(TemporalExtractor):
    def __init__(self):
        self.temporal_patterns = [
            # Explicit clock times (e.g., 950, 1050, 1030, 10 AM, 14:00)
            (r"\b(?:at\s+)?(\d{1,2}(?::\d{2})?\s*(?:am|pm))\b", "Clock Time"),
            (r"\b(?:at|to)\s+(\d{3,4})\b", "Military / Clinical Clock Time"),
            # Relative day markers
            (r"\b(today|tonight|this\s+morning|this\s+afternoon|this\s+evening)\b", "Immediate Shift / Current Day"),
            (r"\b(tomorrow(?:\s+morning|\s+afternoon)?|yesterday|next\s+shift|later|soon)\b", "Relative Temporal Anchor"),
            # Shift / Frequency intervals
            (r"\b(during\s+the\s+am|during\s+the\s+pm|in\s+the\s+morning|at\s+night)\b", "Shift Period"),
            # Durations & Historical spans
            (r"\b(for\s+the\s+last\s+(?:\d+|three|four|five|several|few)\s+(?:years|months|weeks|days|hours))\b", "Duration"),
            (r"\b(since\s+(?:childhood|yesterday|admission|this\s+morning))\b", "Onset Anchor"),
            (r"\b(\d+\s+(?:days?|weeks?|months?|years?)\s+ago)\b", "Historical Distance"),
            # Follow-up intervals & future delays
            (r"\b(?:after|in)\s+(\d+\s*(?:days?|weeks?|months?|hours?))\b", "Future Temporal Interval / Follow-Up Timing")
        ]

    def _split_into_sentences(self, text: str) -> List[Tuple[str, int, int]]:
        from backend.extraction.context_extractor import clinical_context_extractor
        return clinical_context_extractor.split_sentences_protected(text)

    def _find_source_sentence(self, match_start: int, sentence_spans: List[Tuple[str, int, int]]) -> str:
        for sent_text, s_start, s_end in sentence_spans:
            if s_start <= match_start <= s_end:
                return sent_text
        return sentence_spans[0][0] if sentence_spans else ""

    def _associate_event(self, source_sentence: str, events: Optional[List[Dict[str, Any]]]) -> str:
        if not events:
            return "General clinical timeline"
        for ev in events:
            if ev.get("source_sentence") == source_sentence or ev.get("source_sentence") in source_sentence:
                return ev.get("event", "Clinical event")
        return "Clinical context within sentence"

    def extract(self, text: str, events: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        if not text:
            return []

        sentence_spans = self._split_into_sentences(text)
        temporal_items = []
        seen_spans = set()

        for pattern, temp_type in self.temporal_patterns:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                span = (m.start(), m.end())
                if span not in seen_spans:
                    seen_spans.add(span)
                    matched_expr = m.group(0).strip()
                    source_sentence = self._find_source_sentence(m.start(), sentence_spans)
                    associated_event = self._associate_event(source_sentence, events)

                    temporal_items.append({
                        "expression": matched_expr,
                        "type": temp_type,
                        "associated_event": associated_event,
                        "source_sentence": source_sentence,
                        "start_char": m.start(),
                        "end_char": m.end()
                    })

        return temporal_items

# Global singleton instance
clinical_temporal_extractor = ClinicalTemporalExtractor()
