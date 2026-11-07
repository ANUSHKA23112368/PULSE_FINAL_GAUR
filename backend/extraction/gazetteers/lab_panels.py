LAB_PANELS = [
    "Full Blood Count", "FBC", "CBC", "Electrolytes", "U&Es",
    "Liver Function Tests", "LFTs", "Coagulation Profile", "INR",
    "Arterial Blood Gas", "ABG", "Troponin", "Lactate"
]
def is_lab_panel(term: str) -> bool:
    return term.strip().lower() in [l.lower() for l in LAB_PANELS]
