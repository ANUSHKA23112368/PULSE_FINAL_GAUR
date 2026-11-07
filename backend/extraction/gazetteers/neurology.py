NEUROLOGY_CONDITIONS = [
    "Stroke", "CVA", "TIA", "Subarachnoid Hemorrhage", "SAH",
    "Seizure", "Epilepsy", "Encephalopathy", "Parkinson", "Delirium"
]
def is_neurology_term(term: str) -> bool:
    return term.strip().lower() in [c.lower() for c in NEUROLOGY_CONDITIONS]
