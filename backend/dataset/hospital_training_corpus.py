"""
Hospital-style training corpus for PULSE Bio_ClinicalBERT.

Primary gold source
-------------------
Suominen et al. Synthetic Nursing Handover Training Data (NICTA / ANU):
101 de-identified ward handover narratives already adjudicated in
data/gold_standard/gold_standard_corpus.json.

Why not MIMIC / n2c2 / i2b2 here
--------------------------------
Those official EHR corpora require PhysioNet or DUA credentials and contain
real protected health information. This builder never downloads them.

Augmentation
------------
De-identified ISBAR ward notes with exact character offsets, using public
clinical vocabulary (diagnoses, meds, investigations, vitals) typical of
acute hospital handovers. Spans are known by construction — no PHI.
"""

from __future__ import annotations

import json
import os
import random
from typing import Any, Dict, List, Optional, Tuple

from backend.extraction.label_schema import MACRO_CATEGORIES, map_raw_label

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "gold_standard_corpus.json")
SPLITS_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "train_test_splits.json")
EXPORT_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "hospital_training_corpus.json")


class NoteBuilder:
    def __init__(self) -> None:
        self.parts: List[str] = []
        self.spans: List[Dict[str, Any]] = []

    def add(self, text: str, category: Optional[str] = None) -> "NoteBuilder":
        start = sum(len(p) for p in self.parts)
        self.parts.append(text)
        if category and text.strip():
            stripped = text
            lead = len(stripped) - len(stripped.lstrip())
            trail = len(stripped.rstrip())
            span_start = start + lead
            span_end = start + trail
            if span_end > span_start:
                self.spans.append({
                    "label": category,
                    "start_char": span_start,
                    "end_char": span_end,
                    "text": "".join(self.parts)[span_start:span_end],
                    "category": category,
                })
        return self

    def build(self) -> Tuple[str, List[Dict[str, Any]]]:
        return "".join(self.parts), self.spans


BEDS = ["4", "8", "12", "15", "21", "Bed 3", "Bed 7", "Bay 2", "Room 9"]
GIVEN = ["Priya", "Rahul", "Anita", "James", "Maria", "Omar", "Leila", "Chen", "Sofia", "Arjun"]
FAMILY = ["Sharma", "Patel", "Nguyen", "Okeke", "Garcia", "Khan", "Singh", "Walsh", "Costa", "Mehta"]
AGES = ["42 years", "55 yo", "68 year old", "74 years", "29 yo", "81 years", "36 year old"]
GENDERS = ["male", "female"]
DOCTORS = ["Hanlen", "Mehta", "Okoye", "Brennan", "Kapoor", "Santos"]
CONDITIONS = [
    "COPD exacerbation", "community acquired pneumonia", "acute ischaemic stroke",
    "NSTEMI", "diabetic ketoacidosis", "acute kidney injury", "heart failure",
    "cellulitis", "post-op laparoscopic cholecystectomy", "asthma exacerbation",
    "sepsis of urinary origin", "upper GI bleed", "type 2 diabetes", "hypertension",
    "atrial fibrillation", "chronic kidney disease",
]
HISTORY = [
    "type 2 diabetes", "hypertension", "COPD", "ischaemic heart disease",
    "CKD stage 3", "prior stroke", "asthma", "atrial fibrillation",
]
OBS = [
    "OBS are stable", "saturations 94 percent on 2 litres", "febrile overnight",
    "BP 148/86", "tachycardic at 112", "afebrile and comfortable",
    "GCS 15 pupils equal and reactive", "pain 3/10", "nil chest pain",
    "short of breath on exertion", "nausea settled",
]
MEDS = [
    ("IV Lasix", "40 mg", "BD"),
    ("oral metformin", "500 mg", "BD"),
    ("IV Augmentin", "1.2 g", "TDS"),
    ("salbutamol nebuliser", "5 mg", "PRN"),
    ("apixaban", "5 mg", "BD"),
    ("insulin Actrapid", "sliding scale", "QID"),
    ("GTN spray", "400 mcg", "PRN"),
    ("IV fluids Normal Saline", "1 litre", "8 hourly"),
    ("paracetamol", "1 g", "QID"),
    ("aspirin", "100 mg", "daily"),
]
INVESTIGATIONS = [
    "chest X-ray", "ECG", "troponin", "CT brain", "FBC", "UEC",
    "arterial blood gas", "echo", "carotid doppler", "blood cultures",
    "urine MCS", "MRI brain", "BGL",
]
PLANS = [
    "repeat electrolytes in the morning", "medical review overnight if saturations drop",
    "repeat troponin at 6 hours", "physio for mobilisation",
    "diabetes educator review", "hold metformin if eGFR falls",
    "for discharge tomorrow if afebrile", "needs carotid doppler appointment",
]
CARE = [
    "ambulant and self-caring", "needs two-assist for transfers",
    "strict fluid balance", "pressure area care two-hourly",
    "nil by mouth from midnight", "insulin sliding scale charted",
]


def _gold_documents() -> List[Dict[str, Any]]:
    with open(GOLD_PATH, "r", encoding="utf-8") as handle:
        corpus = json.load(handle)
    docs: List[Dict[str, Any]] = []
    for report in corpus.get("reports", []):
        spans = []
        for sp in report.get("entity_spans", []):
            category = map_raw_label(sp.get("label", ""))
            if category in MACRO_CATEGORIES and sp.get("start_char", 0) < sp.get("end_char", 0):
                spans.append({
                    "label": category,
                    "category": category,
                    "start_char": int(sp["start_char"]),
                    "end_char": int(sp["end_char"]),
                    "text": sp.get("text") or report["raw_text"][sp["start_char"]:sp["end_char"]],
                })
        docs.append({
            "report_id": str(report["report_id"]),
            "source": "nicta_suominen_nursing_handover",
            "raw_text": report["raw_text"],
            "entity_spans": spans,
        })
    return docs


def _synthetic_isbar_note(rng: random.Random, index: int) -> Dict[str, Any]:
    bed = rng.choice(BEDS)
    given = rng.choice(GIVEN)
    family = rng.choice(FAMILY)
    name = f"{given} {family}"
    age = rng.choice(AGES)
    gender = rng.choice(GENDERS)
    doctor = rng.choice(DOCTORS)
    dx = rng.choice(CONDITIONS)
    hx = rng.choice(HISTORY)
    while hx.lower() in dx.lower():
        hx = rng.choice(HISTORY)
    obs_a = rng.choice(OBS)
    obs_b = rng.choice(OBS)
    while obs_b == obs_a:
        obs_b = rng.choice(OBS)
    med_name, dose, freq = rng.choice(MEDS)
    inv = rng.choice(INVESTIGATIONS)
    inv2 = rng.choice(INVESTIGATIONS)
    plan = rng.choice(PLANS)
    care = rng.choice(CARE)

    b = NoteBuilder()
    b.add("Bed ").add(bed, "Demographics_Bed").add(", ")
    b.add(name, "Demographics_Name").add(". ")
    b.add(age, "Demographics_Age").add(" ")
    b.add(gender, "Demographics_Gender").add(" under Dr ")
    b.add(doctor, "Demographics_Doctor").add(". Admitted with ")
    b.add(dx, "Clinical_Condition").add(". History of ")
    b.add(hx, "Clinical_Condition").add(". ")
    b.add(obs_a, "Clinical_Observation").add(". ")
    b.add(obs_b, "Clinical_Observation").add(". Currently ")
    b.add(care, "Care_Activity").add(". On ")
    b.add(med_name, "Medication").add(" ")
    b.add(dose, "Medication").add(" ")
    b.add(freq, "Medication").add(". For ")
    b.add(inv, "Investigation_Procedure").add(" this shift, pending ")
    b.add(inv2, "Investigation_Procedure").add(". Plan: ")
    b.add(plan, "Plan_Goal").add(".")

    text, spans = b.build()
    return {
        "report_id": f"isbar_{index:03d}",
        "source": "synthetic_hospital_isbar",
        "raw_text": text,
        "entity_spans": spans,
    }


def build_hospital_training_corpus(n_synthetic: int = 160, seed: int = 42) -> Dict[str, Any]:
    rng = random.Random(seed)
    gold = _gold_documents()
    synthetic = [_synthetic_isbar_note(rng, i) for i in range(n_synthetic)]
    documents = gold + synthetic
    n_spans = sum(len(d["entity_spans"]) for d in documents)
    return {
        "metadata": {
            "dataset_name": "PULSE Hospital Bio_ClinicalBERT Training Corpus",
            "primary_gold": "NICTA/ANU Synthetic Nursing Handover (Suominen et al.) — 101 adjudicated ward notes",
            "augmentation": "De-identified ISBAR hospital handover templates with exact character offsets",
            "excluded_sources": "MIMIC, n2c2, and i2b2 are excluded because they require DUA/PhysioNet access and contain real PHI",
            "total_documents": len(documents),
            "gold_documents": len(gold),
            "synthetic_hospital_documents": len(synthetic),
            "total_entity_spans": n_spans,
            "seed": seed,
        },
        "documents": documents,
    }


def load_hospital_training_documents(
    include_synthetic: bool = True,
    n_synthetic: int = 160,
    seed: int = 42,
) -> List[Dict[str, Any]]:
    corpus = build_hospital_training_corpus(n_synthetic=n_synthetic, seed=seed)
    docs = corpus["documents"]
    if not include_synthetic:
        docs = [d for d in docs if d["source"] == "nicta_suominen_nursing_handover"]
    return docs


def load_fold_ids(fold_name: str = "fold_0") -> Dict[str, List[str]]:
    with open(SPLITS_PATH, "r", encoding="utf-8") as handle:
        splits = json.load(handle)
    return splits[fold_name]


def export_hospital_training_corpus(path: Optional[str] = None, n_synthetic: int = 160) -> str:
    dest = path or EXPORT_PATH
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    corpus = build_hospital_training_corpus(n_synthetic=n_synthetic)
    with open(dest, "w", encoding="utf-8") as handle:
        json.dump(corpus, handle, indent=2)
    return dest


if __name__ == "__main__":
    out = export_hospital_training_corpus()
    print(f"Wrote hospital training corpus to {out}")
