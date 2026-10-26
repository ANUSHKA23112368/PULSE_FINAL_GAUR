"""
PULSE Common Extraction Contract & Base Extractor Interface
Phase 5 — Step 1: Generalized Clinical Extraction Architecture

Defines the standard internal representation for clinical entities across all extractors:
- Rule-based lexicon extractors
- Neural / Token classification extractors (e.g. Bio_ClinicalBERT)
- Statistical sequence extractors
- Open-vocabulary candidate extractors
- Future instruction-following / SLM extractors

Adheres to:
1. Unified Extraction Contract:
   - entity_type: str
   - source_text: str
   - normalized_value: Optional[str] (None when adequately supported mapping is unavailable)
   - source_start: Optional[int]
   - source_end: Optional[int]
   - attributes: Dict[str, Any] (dose, route, frequency, status, timing, negation, uncertainty, etc.)
   - evidence_text: str
   - extraction_method: str
   - review_status: str ("unreviewed", "flagged_for_review", "confirmed")
   - confidence_score: Optional[float]
2. Strict Backward Compatibility:
   Every entity dictionary exported via to_dict() preserves existing PULSE keys:
   category, text, normalized, start_char, end_char, source_sentence, assertion,
   temporality, is_negated, is_uncertain, is_historical, is_planned, dosage,
   frequency, route, status, all_spans, occurrences.
3. Open-Vocabulary Architecture:
   Terms are not required to appear in a hardcoded dictionary before representation.
   Unknown clinical phrases are preserved without inventing identities or diagnoses.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class ClinicalEntity:
    """
    Standardized internal clinical entity representation for PULSE.
    """
    entity_type: str
    source_text: str
    evidence_text: str
    normalized_value: Optional[str] = None
    source_start: Optional[int] = None
    source_end: Optional[int] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    extraction_method: str = "deterministic_rule"
    review_status: str = "unreviewed"  # "unreviewed", "flagged_for_review", "confirmed"
    confidence_score: Optional[float] = None
    all_spans: List[Tuple[int, int]] = field(default_factory=list)
    occurrences: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes entity to a dictionary containing BOTH:
        1. Unified extraction contract fields (entity_type, source_text, normalized_value,
           source_start, source_end, attributes, evidence_text, extraction_method, review_status).
        2. Legacy backward-compatible fields (category, text, normalized, start_char, end_char,
           source_sentence, dosage, frequency, route, status, assertion, temporality,
           is_negated, is_uncertain, is_historical, is_planned).
        """
        # Legacy primary attributes
        dose_val = self.attributes.get("dosage") or self.attributes.get("dose")
        if dose_val is None and self.entity_type == "Medication":
            dose_val = "Unspecified dose in text"

        freq_val = self.attributes.get("frequency")
        if freq_val is None and self.entity_type == "Medication":
            freq_val = "Unspecified frequency"

        route_val = self.attributes.get("route")
        if route_val is None and self.entity_type == "Medication":
            route_val = "Unspecified route"

        status_val = self.attributes.get("status")
        if status_val is None and self.entity_type == "Investigation":
            status_val = "Unspecified"

        assertion = self.attributes.get("assertion", "Affirmative")
        temporality = self.attributes.get("temporality", "Current")
        is_negated = bool(self.attributes.get("is_negated", assertion == "Negated"))
        is_uncertain = bool(self.attributes.get("is_uncertain", assertion in ["Possible", "Uncertain"]))
        is_historical = bool(self.attributes.get("is_historical", temporality == "Historical"))
        is_planned = bool(self.attributes.get("is_planned", temporality == "Planned"))

        # Normalized string fallback for legacy UI components
        legacy_norm = self.normalized_value if self.normalized_value is not None else self.source_text

        spans = self.all_spans
        if not spans and self.source_start is not None and self.source_end is not None:
            spans = [(self.source_start, self.source_end)]

        res = {
            # Standard Contract Keys
            "entity_type": self.entity_type,
            "source_text": self.source_text,
            "normalized_value": self.normalized_value,
            "source_start": self.source_start,
            "source_end": self.source_end,
            "attributes": dict(self.attributes),
            "evidence_text": self.evidence_text,
            "extraction_method": self.extraction_method,
            "review_status": self.review_status,
            "confidence_score": self.confidence_score,

            # Legacy Backward-Compatible Keys
            "category": self.entity_type,
            "text": self.source_text,
            "normalized": legacy_norm,
            "source_sentence": self.evidence_text,
            "start_char": self.source_start if self.source_start is not None else 0,
            "end_char": self.source_end if self.source_end is not None else len(self.source_text),
            "assertion": assertion,
            "temporality": temporality,
            "is_negated": is_negated,
            "is_uncertain": is_uncertain,
            "is_historical": is_historical,
            "is_planned": is_planned,
            "all_spans": spans,
            "occurrences": self.occurrences
        }

        # Legacy category-specific attributes
        if self.entity_type == "Medication":
            res["dosage"] = dose_val
            res["frequency"] = freq_val
            res["route"] = route_val
        if status_val is not None or self.entity_type == "Investigation":
            res["status"] = status_val

        # Propagate custom fields from attributes for complete parity
        for k, v in self.attributes.items():
            if k not in res:
                res[k] = v

        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any], default_method: str = "deterministic_rule") -> "ClinicalEntity":
        """Reconstructs ClinicalEntity from a legacy or contract dictionary."""
        entity_type = data.get("entity_type") or data.get("category", "General")
        source_text = data.get("source_text") or data.get("text") or data.get("value") or ""
        if "normalized_value" in data:
            norm_val = data["normalized_value"]
        elif "normalized" in data:
            norm_val = data["normalized"]
        else:
            norm_val = None

        source_start = data.get("source_start")
        if source_start is None:
            source_start = data.get("start_char")

        source_end = data.get("source_end")
        if source_end is None:
            source_end = data.get("end_char")

        evidence_text = data.get("evidence_text") or data.get("source_sentence", "")
        method = data.get("extraction_method") or data.get("matching_method") or data.get("rule_source") or default_method
        review_status = data.get("review_status", "unreviewed")

        # Gather attributes dynamically
        attributes = dict(data.get("attributes", {}))
        standard_keys = {
            "entity_type", "category", "source_text", "text", "normalized_value", "normalized",
            "source_start", "start_char", "source_end", "end_char", "evidence_text",
            "source_sentence", "extraction_method", "review_status", "confidence_score",
            "all_spans", "occurrences", "attributes"
        }
        for k, v in data.items():
            if k not in standard_keys and k not in attributes:
                attributes[k] = v

        return cls(
            entity_type=entity_type,
            source_text=source_text,
            normalized_value=norm_val,
            source_start=source_start,
            source_end=source_end,
            attributes=attributes,
            evidence_text=evidence_text,
            extraction_method=method,
            review_status=review_status,
            confidence_score=data.get("confidence_score") or data.get("raw_model_probability"),
            all_spans=data.get("all_spans", []),
            occurrences=data.get("occurrences", 1)
        )


class BaseClinicalExtractor(ABC):
    """
    Abstract Base Class for all PULSE Clinical Extractors.
    Allows rule-based, statistical, neural, and open-vocabulary extractors
    to be evaluated behind a common unified contract.
    """
    def __init__(self, name: str, version: str = "1.0.0", supports_open_vocabulary: bool = False):
        self.name = name
        self.version = version
        self.supports_open_vocabulary = supports_open_vocabulary

    @abstractmethod
    def extract(self, text: str) -> Dict[str, Any]:
        """
        Executes clinical extraction on raw or preprocessed text.
        Returns a dictionary containing categorized lists of entities,
        including 'all_entities' and 'unclassified_candidates'.
        """
        pass

    def extract_entities(self, text: str) -> List[ClinicalEntity]:
        """
        Returns a flat list of ClinicalEntity contract objects.
        """
        raw_res = self.extract(text)
        entities: List[ClinicalEntity] = []
        if "all_entities" in raw_res:
            for item in raw_res["all_entities"]:
                if isinstance(item, ClinicalEntity):
                    entities.append(item)
                elif isinstance(item, dict):
                    entities.append(ClinicalEntity.from_dict(item, default_method=self.name))
        else:
            for cat_key in [
                "patient_information", "conditions", "symptoms", "medications",
                "investigations", "treatments", "measurements", "unclassified_candidates"
            ]:
                for item in raw_res.get(cat_key, []):
                    if isinstance(item, dict):
                        entities.append(ClinicalEntity.from_dict(item, default_method=self.name))
        return entities


class ExtractorRegistry:
    """
    Registry for evaluating multiple clinical extraction engines
    (rule-based, statistical, neural, open-vocabulary) behind the common contract.
    """
    _registry: Dict[str, BaseClinicalExtractor] = {}

    @classmethod
    def register(cls, name: str, extractor: BaseClinicalExtractor):
        cls._registry[name.lower()] = extractor

    @classmethod
    def get(cls, name: str) -> Optional[BaseClinicalExtractor]:
        return cls._registry.get(name.lower())

    @classmethod
    def list_available(cls) -> List[str]:
        return list(cls._registry.keys())
