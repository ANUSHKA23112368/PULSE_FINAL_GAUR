CARDIOLOGY_CONDITIONS = [
    "Atrial Fibrillation", "AF", "Acute Coronary Syndrome", "ACS",
    "Heart Failure", "CHF", "STEMI", "NSTEMI", "Angina",
    "Cardiogenic Shock", "Pericarditis", "Aortic Stenosis"
]
def is_cardiology_term(term: str) -> bool:
    return term.strip().lower() in [c.lower() for c in CARDIOLOGY_CONDITIONS]
