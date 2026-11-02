"""
Temporal Anchor Resolver.
Parses shift markers, absolute clock hours, and relative offsets in clinical narratives.
"""

import re
from typing import List, Dict, Any

SHIFT_MAPPINGS = {
    "morning": {"start": "07:00", "end": "15:30"},
    "day": {"start": "07:00", "end": "15:30"},
    "afternoon": {"start": "13:30", "end": "22:00"},
    "evening": {"start": "13:30", "end": "22:00"},
    "night": {"start": "21:30", "end": "07:30"},
}

def extract_clock_times(text: str) -> List[Dict[str, Any]]:
    pattern = r"\b(?:(?:[01]?\d|2[0-3]):[0-5]\d|(?:1[0-2]|0?[1-9])\s*(?:am|pm))\b"
    found = []
    for m in re.finditer(pattern, text, re.IGNORECASE):
        found.append({
            "expression": m.group(0),
            "start_char": m.start(),
            "end_char": m.end()
        })
    return found
