NEPHROLOGY_CONDITIONS = [
    "Acute Kidney Injury", "AKI", "Chronic Kidney Disease", "CKD",
    "End Stage Renal Disease", "ESRD", "Glomerulonephritis", "Nephrotic Syndrome"
]
def is_nephrology_term(term: str) -> bool:
    return term.strip().lower() in [c.lower() for c in NEPHROLOGY_CONDITIONS]
