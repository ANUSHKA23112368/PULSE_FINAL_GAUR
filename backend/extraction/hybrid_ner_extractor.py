"""Runtime CRF + lexicon span extractor for PULSE.

Loads the artifacts written by `scripts/train_hybrid_ner.py`:

    backend/models/hybrid_ner/crf_model.pkl
    backend/models/hybrid_ner/gazetteer.json

The model generalises over token shape/word/character features, so unlike a
pure lexicon it can tag entities it never saw in training. It is intended as
the span layer of the hybrid pipeline (CRF spans + ConText + deterministic
vitals parsing).
"""

from __future__ import annotations

import json
import os
import pickle
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from backend.extraction.context_extractor import clinical_context_extractor
from backend.extraction.hybrid_ner_features import (
    clean_spans,
    tags_to_spans,
    token_features,
    tokenize,
)

MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "hybrid_ner"))

DEMOGRAPHIC_FIELDS = {
    "Demographics_Bed": "Bed / Room",
    "Demographics_Name": "Patient Name",
    "Demographics_Age": "Age",
    "Demographics_Gender": "Gender / Sex",
    "Demographics_Doctor": "Consulting Doctor",
}

BUCKETS = {
    "Clinical_Condition": "conditions",
    "Clinical_Observation": "symptoms",
    "Medication": "medications",
    "Investigation_Procedure": "investigations",
    "Plan_Goal": "treatments",
    "Care_Activity": "treatments",
}

_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]?")
_DOSE_RE = re.compile(r"\b(\d+\s*(?:mg|mcg|ml|units?|puffs?|dosage|doses?)|variable\s*dose|sliding\s*scale|\d+\s+nitros?)\b", re.IGNORECASE)
_FREQ_RE = re.compile(r"\b(qid|bd|tds|prn|daily|mane|nocte|hourly)\b", re.IGNORECASE)
_ROUTE_RE = re.compile(r"\b(iv|oral|po|subcut|sc|topical|sublingual|inhal(?:er|ation))\b", re.IGNORECASE)

ENTITY_BUCKET_LABELS = {
    "conditions": "Condition",
    "symptoms": "Symptom",
    "medications": "Medication",
    "investigations": "Investigation",
    "treatments": "Treatment",
}
_ENTITY_BUCKETS = tuple(ENTITY_BUCKET_LABELS)


class HybridNERExtractor:
    def __init__(self, model_dir: Optional[str] = None):
        self.model_dir = model_dir or MODEL_DIR
        self.model = None
        self.gazetteer: Dict[str, Counter] = {}
        self.last_inference_ms = None
        self._load()

    def _load(self) -> None:
        model_path = os.path.join(self.model_dir, "crf_model.pkl")
        gaz_path = os.path.join(self.model_dir, "gazetteer.json")
        if not (os.path.exists(model_path) and os.path.exists(gaz_path)):
            return
        try:
            with open(model_path, "rb") as fh:
                self.model = pickle.load(fh)
            with open(gaz_path, encoding="utf-8") as fh:
                raw = json.load(fh)
            self.gazetteer = {key: Counter(value.get("counts", {})) for key, value in raw.items()}
        except Exception as exc:  # pragma: no cover - defensive load
            print(f"Notice: hybrid NER artifacts could not be loaded: {exc}")
            self.model = None

    def is_available(self) -> bool:
        return self.model is not None

    def predict_spans(self, text: str) -> List[Dict[str, Any]]:
        if not self.model or not text.strip():
            return []
        tokens = tokenize(text)
        if not tokens:
            return []
        feats = [token_features(tokens, i, self.gazetteer) for i in range(len(tokens))]
        raw_spans = tags_to_spans(tokens, self.model.predict([feats])[0], text)
        # Same cleanup the fold evaluation applies, so runtime output matches metrics.
        return clean_spans(raw_spans, text)

    def _sentence_at(self, text: str, position: int) -> str:
        for match in _SENTENCE_RE.finditer(text):
            if match.start() <= position <= match.end():
                return match.group(0).strip()
        return ""

    def extract(self, text: str) -> Dict[str, Any]:
        entities: Dict[str, Any] = {
            "patient_information": [],
            "conditions": [],
            "symptoms": [],
            "medications": [],
            "investigations": [],
            "treatments": [],
            "measurements": [],
            "abbreviations": [],
            "clinical_risks": [],
        }
        # Deduplicated span buckets keyed like the Bio_ClinicalBERT extractor so that
        # downstream event/ConText/structured-generation stages receive the same contract.
        buckets: Dict[str, Dict[tuple, Dict[str, Any]]] = {name: {} for name in _ENTITY_BUCKETS}
        for span in self.predict_spans(text):
            category = span["category"]
            sentence = self._sentence_at(text, span["start_char"])
            span_text = span["text"]
            if category in DEMOGRAPHIC_FIELDS:
                entities["patient_information"].append(
                    {
                        "category": "Patient Information",
                        "field": DEMOGRAPHIC_FIELDS[category],
                        "value": span["text"],
                        "detail": span["text"],
                        "confidence": None,
                        "confidence_type": "uncalibrated",
                        "extraction_method": "CRF + lexicon hybrid tagger",
                        "source_sentence": sentence,
                        "start_char": span["start_char"],
                        "end_char": span["end_char"],
                    }
                )
                continue
            bucket = BUCKETS.get(category)
            if not bucket:
                continue
            ctx = clinical_context_extractor.analyze_assertion(
                span_text, span["start_char"], span["end_char"], text
            )
            key = (span_text.lower(), ctx["assertion"], ctx["temporality"])
            existing = buckets[bucket].get(key)
            if existing is not None:
                existing["occurrences"] += 1
                existing["all_spans"].append((span["start_char"], span["end_char"]))
                continue
            item: Dict[str, Any] = {
                "category": ENTITY_BUCKET_LABELS[bucket],
                "text": span_text,
                "normalized": span_text.title(),
                "assertion": ctx["assertion"],
                "temporality": ctx["temporality"],
                "is_negated": ctx["is_negated"],
                "is_uncertain": ctx["is_uncertain"],
                "is_historical": ctx["is_historical"],
                "is_planned": ctx["is_planned"],
                "context_cue": ctx["cue"],
                "confidence": None,
                "confidence_type": "uncalibrated",
                "extraction_method": "CRF + lexicon hybrid tagger",
                "source_sentence": sentence,
                "start_char": span["start_char"],
                "end_char": span["end_char"],
                "all_spans": [(span["start_char"], span["end_char"])],
                "occurrences": 1,
            }
            if bucket == "medications":
                dose_m = _DOSE_RE.search(sentence)
                freq_m = _FREQ_RE.search(sentence)
                route_m = _ROUTE_RE.search(sentence)
                item["dosage"] = dose_m.group(0) if dose_m else "Unspecified dose in text"
                item["frequency"] = freq_m.group(0).upper() if freq_m else "Unspecified frequency"
                item["route"] = route_m.group(0).upper() if route_m else "Unspecified route"
            buckets[bucket][key] = item
        for bucket_name, items in buckets.items():
            entities[bucket_name] = list(items.values())
        return entities


hybrid_ner_extractor = HybridNERExtractor()
