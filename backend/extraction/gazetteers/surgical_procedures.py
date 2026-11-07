SURGICAL_PROCEDURES = [
    "Laparotomy", "Appendectomy", "Cholecystectomy", "CABG",
    "Total Hip Replacement", "THR", "Total Knee Replacement", "TKR",
    "Craniotomy", "Colectomy", "Stoma Formation"
]
def is_surgical_procedure(term: str) -> bool:
    return term.strip().lower() in [s.lower() for s in SURGICAL_PROCEDURES]
