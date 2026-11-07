ICU_MEDICATIONS = [
    "Noradrenaline", "Vasopressin", "Propofol", "Fentanyl",
    "Midazolam", "Dexmedetomidine", "Amiodarone", "Insulin Infusion"
]
def is_icu_drug(term: str) -> bool:
    return term.strip().lower() in [m.lower() for m in ICU_MEDICATIONS]
