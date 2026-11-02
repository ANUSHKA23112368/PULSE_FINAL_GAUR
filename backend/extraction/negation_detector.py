"""
Clinical Negation and Uncertainty Detector (ConText-inspired heuristic rules).
"""

import re
from typing import Tuple

PRE_NEGATION_TRIGGERS = [
    r"\bno\b", r"\bdenies\b", r"\bdenied\b", r"\bnegative for\b",
    r"\bwithout\b", r"\bfree of\b", r"\brule out\b", r"\bno signs of\b"
]

UNCERTAINTY_TRIGGERS = [
    r"\bpossible\b", r"\bpossibly\b", r"\bprobable\b", r"\bsuspected\b",
    r"\bquery\b", r"\b\?\b"
]

def check_assertion(sentence: str, entity: str) -> Tuple[bool, bool]:
    s_lower = sentence.lower()
    e_lower = entity.lower()
    
    if e_lower not in s_lower:
        return False, False
        
    e_pos = s_lower.find(e_lower)
    pre_window = s_lower[max(0, e_pos - 40):e_pos]
    
    is_neg = any(re.search(pat, pre_window) for pat in PRE_NEGATION_TRIGGERS)
    is_unc = any(re.search(pat, pre_window) for pat in UNCERTAINTY_TRIGGERS)
    
    return is_neg, is_unc
