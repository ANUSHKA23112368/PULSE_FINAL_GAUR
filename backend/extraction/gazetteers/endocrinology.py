ENDOCRINOLOGY_CONDITIONS = [
    "Type 2 Diabetes Mellitus", "T2DM", "Diabetic Ketoacidosis", "DKA",
    "Hypoglycemia", "Hyperthyroidism", "Hypothyroidism", "Addisonian Crisis"
]
def is_endocrinology_term(term: str) -> bool:
    return term.strip().lower() in [c.lower() for c in ENDOCRINOLOGY_CONDITIONS]
