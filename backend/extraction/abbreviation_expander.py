"""
Clinical Abbreviation Normalization and Lookup Engine.
Expands ward-specific clinical shorthand into standardized clinical terms.
"""

from typing import Dict, Optional

CLINICAL_ABBREVIATIONS: Dict[str, str] = {
    "AF": "Atrial Fibrillation",
    "BGL": "Blood Glucose Level",
    "BP": "Blood Pressure",
    "COPD": "Chronic Obstructive Pulmonary Disease",
    "CXR": "Chest X-Ray",
    "ECG": "Electrocardiogram",
    "GCS": "Glasgow Coma Scale",
    "HPN": "Hypertension",
    "IV": "Intravenous",
    "MDT": "Multidisciplinary Team",
    "PACU": "Post-Anesthesia Care Unit",
    "PO": "Per Os (By Mouth)",
    "PRN": "Pro Re Nata (As Needed)",
    "QID": "Quarter In Die (Four Times Daily)",
    "SOB": "Shortness of Breath",
    "UTI": "Urinary Tract Infection"
}

def expand_abbreviation(token: str) -> Optional[str]:
    """Returns canonical clinical definition for known abbreviations."""
    clean = token.strip().upper()
    return CLINICAL_ABBREVIATIONS.get(clean)
