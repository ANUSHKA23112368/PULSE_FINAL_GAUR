"""
Shared real-time handover analysis pipeline with step timings.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from backend.extraction.clinical_bert_extractor import clinical_bert_extractor
from backend.extraction.entity_extractor import clinical_entity_extractor
from backend.extraction.event_extractor import clinical_event_extractor
from backend.extraction.structured_generator import structured_handover_generator
from backend.extraction.temporal_extractor import clinical_temporal_extractor
from backend.preprocessing.preprocessor import clinical_preprocessor


def _now() -> float:
    return time.perf_counter()


def run_realtime_analysis(
    raw_text: str,
    engine: str = "hybrid",
    on_step: Optional[Callable[[str, Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    engine = (engine or "hybrid").lower()
    timings: Dict[str, float] = {}
    bert_ready = clinical_bert_extractor.is_available()
    use_bert = engine in ["clinical_bert", "hybrid"] and bert_ready

    def emit(step: str, payload: Optional[Dict[str, Any]] = None):
        if on_step:
            on_step(step, payload or {})

    emit("preprocess")
    t0 = _now()
    prep_res = clinical_preprocessor.preprocess(raw_text)
    preprocessed_text = prep_res["preprocessed_text"]
    timings["preprocess_ms"] = round((_now() - t0) * 1000, 2)

    emit("extract")
    t1 = _now()
    if use_bert:
        entities = clinical_bert_extractor.extract(preprocessed_text)
        engine_used = "Bio_ClinicalBERT" if engine == "clinical_bert" else "Hybrid Bio_ClinicalBERT + ConText"
    else:
        entities = clinical_entity_extractor.extract(preprocessed_text)
        engine_used = "Hybrid Rule Engine"
    timings["extract_ms"] = round((_now() - t1) * 1000, 2)
    timings["neural_span_ms"] = clinical_bert_extractor.last_inference_ms if use_bert else None

    emit("events")
    t2 = _now()
    events = clinical_event_extractor.extract(preprocessed_text, entities=entities)
    timings["events_ms"] = round((_now() - t2) * 1000, 2)

    emit("temporal")
    t3 = _now()
    temporal_info = clinical_temporal_extractor.extract(preprocessed_text, events=events)
    timings["temporal_ms"] = round((_now() - t3) * 1000, 2)

    emit("tasks")
    t4 = _now()
    pending_tasks = structured_handover_generator.extract_pending_tasks(preprocessed_text, events=events)
    follow_up = structured_handover_generator.extract_follow_up(preprocessed_text, pending_tasks=pending_tasks)
    timings["tasks_ms"] = round((_now() - t4) * 1000, 2)

    emit("structure")
    t5 = _now()
    structured_handover = structured_handover_generator.generate_structured_handover(
        text=preprocessed_text,
        entities=entities,
        events=events,
        temporal_info=temporal_info,
        pending_tasks=pending_tasks,
        follow_up=follow_up,
    )
    timings["structure_ms"] = round((_now() - t5) * 1000, 2)
    timings["total_ms"] = round(sum(v for v in timings.values() if isinstance(v, (int, float))), 2)

    evidence_items: List[Dict[str, Any]] = []
    mapping = [
        ("Patient Info", "patient_information", lambda p: f"{p.get('field')}: {p.get('value')}"),
        ("Condition", "conditions", lambda c: c.get("text")),
        ("Symptom", "symptoms", lambda s: s.get("text")),
        ("Medication", "medications", lambda m: m.get("text")),
        ("Investigation", "investigations", lambda inv: inv.get("text")),
        ("Treatment", "treatments", lambda trt: trt.get("text")),
        ("Measurement", "measurements", lambda ms: ms.get("text")),
    ]
    for category, key, fmt in mapping:
        for item in entities.get(key, []):
            evidence_items.append({
                "category": category,
                "entity": fmt(item),
                "source_sentence": item.get("source_sentence", ""),
            })
    for ev in events:
        evidence_items.append({
            "category": "Clinical Event",
            "entity": ev.get("event"),
            "source_sentence": ev.get("source_sentence", ""),
        })
    for pt in pending_tasks:
        evidence_items.append({
            "category": "Pending Task",
            "entity": pt.get("task"),
            "source_sentence": pt.get("source_sentence", ""),
        })

    emit("complete", {"total_ms": timings["total_ms"]})
    return {
        "raw_text": raw_text,
        "preprocessed_text": preprocessed_text,
        "changes_made": prep_res["changes_made"],
        "word_count": len(preprocessed_text.split()),
        "char_count": len(preprocessed_text),
        "entities": entities,
        "events": events,
        "temporal_information": temporal_info,
        "pending_tasks": pending_tasks,
        "follow_up": follow_up,
        "structured_handover": structured_handover,
        "executive_summary": structured_handover.get("executive_summary", ""),
        "isbar": structured_handover.get("isbar", {}),
        "clinical_risks": entities.get("clinical_risks", []),
        "evidence": evidence_items,
        "engine_used": engine_used,
        "model_metadata": {
            "pipeline": "PULSE Bio_ClinicalBERT Extraction Pipeline" if use_bert else "PULSE Deterministic Rule & ConText Pipeline",
            "nlp_paradigm": (
                "Fine-tuned Bio_ClinicalBERT token classification with live sliding-window inference and ConText assertion scoping"
                if use_bert
                else "Dictionary, Pattern, and Contextual Rule Engine"
            ),
            "candidate_backbone": "Bio_ClinicalBERT (emilyalsentzer/Bio_ClinicalBERT)",
            "model_active": bert_ready,
            "selected_engine": engine,
            "evaluation_reference": "NICTA/ANU Synthetic Nursing Handover (101 documents) + de-identified ISBAR hospital augmentations",
            "realtime": True,
            "pipeline_timings_ms": timings,
            "neural_span_ms": timings.get("neural_span_ms"),
            "total_inference_ms": timings.get("total_ms"),
        },
    }
