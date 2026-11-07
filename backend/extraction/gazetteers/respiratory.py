RESPIRATORY_CONDITIONS = [
    "COPD", "Asthma", "Pneumonia", "Pulmonary Embolism", "PE",
    "Pleural Effusion", "Pneumothorax", "ARDS", "Bronchiectasis"
]
def is_respiratory_term(term: str) -> bool:
    return term.strip().lower() in [c.lower() for c in RESPIRATORY_CONDITIONS]
