"""
Vital Sign Unit Normalizer and Physiological Bounds Validator.
"""

import re
from typing import Dict, Any, Optional

def parse_vital_measurement(text: str) -> Optional[Dict[str, Any]]:
    hr_match = re.search(r"\b(?:HR|pulse)\s*[:=]?\s*(\d{2,3})\s*(?:bpm)?\b", text, re.IGNORECASE)
    if hr_match:
        val = int(hr_match.group(1))
        return {"metric": "heart_rate", "value": val, "unit": "bpm", "abnormal": val < 50 or val > 100}
    
    bp_match = re.search(r"\bBP\s*[:=]?\s*(\d{2,3})\s*/\s*(\d{2,3})\b", text, re.IGNORECASE)
    if bp_match:
        sys = int(bp_match.group(1))
        dia = int(bp_match.group(2))
        return {"metric": "blood_pressure", "systolic": sys, "diastolic": dia, "unit": "mmHg", "abnormal": sys > 140 or dia > 90}
    
    spo2_match = re.search(r"\bSpO2\s*[:=]?\s*(\d{2,3})\s*%?\b", text, re.IGNORECASE)
    if spo2_match:
        val = int(spo2_match.group(1))
        return {"metric": "spo2", "value": val, "unit": "%", "abnormal": val < 95}
        
    return None
