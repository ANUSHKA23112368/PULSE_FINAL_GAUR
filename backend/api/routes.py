"""
PULSE REST API Endpoints
Provides endpoints for:
- Health & System status
- Corpus statistics (dynamic EDA)
- Report discovery & retrieval (0 to 100)
- Preprocessing comparison
- Clinical extraction & event structuring
- Full end-to-end analysis pipeline
- SQLite execution history
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

from backend.dataset.loader import dataset_loader
from backend.preprocessing.preprocessor import clinical_preprocessor
from backend.extraction.entity_extractor import clinical_entity_extractor
from backend.extraction.clinical_bert_extractor import clinical_bert_extractor
from backend.extraction.event_extractor import clinical_event_extractor
from backend.extraction.temporal_extractor import clinical_temporal_extractor
from backend.extraction.structured_generator import structured_handover_generator
from backend.database.database import db

router = APIRouter(prefix="/api")

# Pydantic Schemas
class PreprocessRequest(BaseModel):
    raw_text: str = Field(..., description="Raw unstructured nursing handover text")

class AnalyzeRequest(BaseModel):
    report_id: Optional[str] = Field(None, description="Optional ID of dataset report (0-100)")
    raw_text: Optional[str] = Field(None, description="Raw handover text if custom or overriding")
    engine: Optional[str] = Field("hybrid", description="Extraction engine: 'hybrid', 'clinical_bert', or 'rule'")

class ExtractRequest(BaseModel):
    text: str = Field(..., description="Handover text to extract from")
    engine: Optional[str] = Field("hybrid", description="Extraction engine: 'hybrid', 'clinical_bert', or 'rule'")

class PatientCreate(BaseModel):
    display_id: Optional[str] = Field(None, description="Optional unique synthetic demonstration patient ID (e.g. PULSE-DEMO-011). Auto-generated if omitted.")
    name: str = Field(..., min_length=1, description="Synthetic demonstration patient name")
    age: Optional[str] = Field(None, description="Patient age")
    gender: Optional[str] = Field(None, description="Patient gender")
    ward: Optional[str] = Field(None, description="Assigned ward")
    bed_number: Optional[str] = Field(None, description="Assigned bed number")
    consultant: Optional[str] = Field(None, description="Attending consultant")
    admitting_diagnosis: Optional[str] = Field(None, description="Synthetic admitting diagnosis")

class NoteCreate(BaseModel):
    raw_text: str = Field(..., min_length=1, description="Clinical handover note text")
    author_identifier: Optional[str] = Field("Staff Clinician (Demo)", description="Author identification")

class NoteReviewRequest(BaseModel):
    reviewed_data: Dict[str, Any] = Field(..., description="Complete corrected structured extraction data")
    reviewer_identifier: Optional[str] = Field("Dr. Hanlen, MD (Attending Consultant)", description="Reviewer identification")
    review_notes: Optional[str] = Field(None, description="Optional clinician review audit notes")


@router.get("/health")
async def health_check():
    """
    Returns system health status and component availability.
    """
    stats = dataset_loader.calculate_statistics()
    bert_available = clinical_bert_extractor.is_available()
    return {
        "status": "healthy",
        "system": "PULSE (Patient Update & Log Structuring Engine)",
        "version": "1.0.0-prototype",
        "dataset_loaded": stats["loaded_successfully"] > 0,
        "total_reports": stats["total_reports"],
        "total_patients": len(db.list_patients()),
        "model_status": {
            "current_engine": "Bio_ClinicalBERT Neural Extraction Pipeline" if bert_available else "Hybrid Clinical Rule Engine",
            "clinical_bert_loaded": bert_available,
            "clinical_bert_model": "emilyalsentzer/Bio_ClinicalBERT",
            "clinical_bert_path": clinical_bert_extractor.model_path,
            "status_detail": "Fine-tuned model checkpoint active" if bert_available else "Rule engine fallback active (checkpoint loading pending or in progress)"
        },
        "disclaimer": "PULSE is an AI-assisted clinical information-organization prototype. It does not diagnose, prescribe treatment, or replace professional clinical judgment."
    }


@router.get("/stats")
async def get_stats():
    """
    Calculates and returns live EDA statistics directly from the 101 text files.
    """
    try:
        stats = dataset_loader.calculate_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate dataset statistics: {str(e)}")


@router.get("/reports")
async def get_reports():
    """
    Returns index of all discovered nursing handover reports.
    """
    try:
        reports = dataset_loader.get_all_reports()
        # Return summary listing
        summary = []
        for r in reports:
            summary.append({
                "report_id": r["report_id"],
                "filename": r["filename"],
                "word_count": r["word_count"],
                "char_count": r["char_count"],
                "preview": r["raw_text"][:140] + "..." if len(r["raw_text"]) > 140 else r["raw_text"],
                "status": r["status"]
            })
        return {
            "total_count": len(summary),
            "reports": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve reports: {str(e)}")


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    """
    Returns verbatim raw text and preprocessed text for a specific report.
    """
    report = dataset_loader.get_report_by_id(report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report ID '{report_id}' not found in dataset.")

    preprocessed_res = clinical_preprocessor.preprocess(report["raw_text"])

    return {
        "report_id": report["report_id"],
        "filename": report["filename"],
        "word_count": report["word_count"],
        "char_count": report["char_count"],
        "raw_text": report["raw_text"],
        "preprocessed_text": preprocessed_res["preprocessed_text"],
        "changes_made": preprocessed_res["changes_made"],
        "preserved_clinical_elements": preprocessed_res.get("preserved_clinical_elements", []),
        "sentences": preprocessed_res.get("sentences", []),
        "token_count": preprocessed_res.get("token_count", 0),
        "philosophy_note": preprocessed_res.get("philosophy_note", "")
    }


@router.post("/preprocess")
async def preprocess_text(payload: PreprocessRequest):
    """
    Performs standalone clinical formatting normalization.
    """
    if not payload.raw_text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    result = clinical_preprocessor.preprocess(payload.raw_text)
    return result


@router.post("/extract")
async def extract_clinical_info(payload: ExtractRequest):
    """
    Executes clinical entity extraction on the provided text.
    Supports engine selection: 'clinical_bert', 'rule', or 'hybrid'.
    """
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    engine = (payload.engine or "hybrid").lower()
    if engine in ["clinical_bert", "hybrid"] and clinical_bert_extractor.is_available():
        entities = clinical_bert_extractor.extract(payload.text)
    else:
        entities = clinical_entity_extractor.extract(payload.text)
    return entities


@router.post("/analyze")
async def analyze_handover(payload: AnalyzeRequest):
    """
    The PRIMARY End-to-End Pipeline Execution Endpoint:
    STEP 1: Receive raw handover text (or fetch by report_id)
    STEP 2: Preprocess the text (clean formatting, preserve clinical meaning)
    STEP 3: Perform clinical information & entity extraction (Neural or Hybrid Rule)
    STEP 4: Perform event extraction
    STEP 5: Perform temporal extraction
    STEP 6: Extract pending tasks & follow-up actions
    STEP 7: Synthesize 9-category structured clinical handover
    STEP 8: Store in SQLite history and return comprehensive JSON
    """
    raw_text = payload.raw_text or ""
    report_id = payload.report_id
    engine = (payload.engine or "hybrid").lower()

    # If report_id is given and raw_text is omitted or blank, load from dataset
    if report_id and not raw_text.strip():
        report_data = dataset_loader.get_report_by_id(report_id)
        if not report_data:
            raise HTTPException(status_code=404, detail=f"Report ID '{report_id}' not found in dataset.")
        raw_text = report_data["raw_text"]

    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="No clinical handover text provided for analysis.")

    # STEP 2: Preprocessing
    prep_res = clinical_preprocessor.preprocess(raw_text)
    preprocessed_text = prep_res["preprocessed_text"]
    changes_made = prep_res["changes_made"]

    # STEP 3: Entity Extraction (Route to Bio_ClinicalBERT or Rule engine)
    if engine in ["clinical_bert", "hybrid"] and clinical_bert_extractor.is_available():
        entities = clinical_bert_extractor.extract(preprocessed_text)
    else:
        entities = clinical_entity_extractor.extract(preprocessed_text)

    # STEP 4: Event Extraction
    events = clinical_event_extractor.extract(preprocessed_text, entities=entities)

    # STEP 5: Temporal Extraction
    temporal_info = clinical_temporal_extractor.extract(preprocessed_text, events=events)

    # STEP 6: Pending Tasks & Follow-Up
    pending_tasks = structured_handover_generator.extract_pending_tasks(preprocessed_text, events=events)
    follow_up = structured_handover_generator.extract_follow_up(preprocessed_text, pending_tasks=pending_tasks)

    # STEP 7: Final 9-Category Structured Handover Output
    structured_handover = structured_handover_generator.generate_structured_handover(
        text=preprocessed_text,
        entities=entities,
        events=events,
        temporal_info=temporal_info,
        pending_tasks=pending_tasks,
        follow_up=follow_up
    )

    # Compile Evidence Map (linking extracted items to source sentences)
    evidence_items = []
    # Patient Info evidence
    for p in entities.get("patient_information", []):
        evidence_items.append({
            "category": "Patient Info",
            "entity": f"{p.get('field')}: {p.get('value')}",
            "source_sentence": p.get("source_sentence", "")
        })
    # Conditions evidence
    for c in entities.get("conditions", []):
        evidence_items.append({
            "category": "Condition",
            "entity": c.get("text"),
            "source_sentence": c.get("source_sentence", "")
        })
    # Symptoms evidence
    for s in entities.get("symptoms", []):
        evidence_items.append({
            "category": "Symptom",
            "entity": s.get("text"),
            "source_sentence": s.get("source_sentence", "")
        })
    # Medications evidence
    for m in entities.get("medications", []):
        evidence_items.append({
            "category": "Medication",
            "entity": m.get("text"),
            "source_sentence": m.get("source_sentence", "")
        })
    # Investigations evidence
    for inv in entities.get("investigations", []):
        evidence_items.append({
            "category": "Investigation",
            "entity": inv.get("text"),
            "source_sentence": inv.get("source_sentence", "")
        })
    # Treatments evidence
    for trt in entities.get("treatments", []):
        evidence_items.append({
            "category": "Treatment",
            "entity": trt.get("text"),
            "source_sentence": trt.get("source_sentence", "")
        })
    # Measurements evidence
    for ms in entities.get("measurements", []):
        evidence_items.append({
            "category": "Measurement",
            "entity": ms.get("text"),
            "source_sentence": ms.get("source_sentence", "")
        })
    # Events evidence
    for ev in events:
        evidence_items.append({
            "category": "Clinical Event",
            "entity": ev.get("event"),
            "source_sentence": ev.get("source_sentence", "")
        })
    # Pending tasks evidence
    for pt in pending_tasks:
        evidence_items.append({
            "category": "Pending Task",
            "entity": pt.get("task"),
            "source_sentence": pt.get("source_sentence", "")
        })

    # Prepare complete response payload
    response_data = {
        "report_id": report_id or "Custom",
        "raw_text": raw_text,
        "preprocessed_text": preprocessed_text,
        "changes_made": changes_made,
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
        "model_metadata": {
            "pipeline": "PULSE Bio_ClinicalBERT Extraction Pipeline" if (engine in ["clinical_bert", "hybrid"] and clinical_bert_extractor.is_available()) else "PULSE Deterministic Rule & ConText Pipeline",
            "nlp_paradigm": "Fine-Tuned Bio_ClinicalBERT Token Classification with Contextual Assertion Scoping" if (engine in ["clinical_bert", "hybrid"] and clinical_bert_extractor.is_available()) else "Dictionary, Pattern, and Contextual Rule Engine",
            "candidate_backbone": "Bio_ClinicalBERT (emilyalsentzer/Bio_ClinicalBERT)",
            "model_active": clinical_bert_extractor.is_available(),
            "selected_engine": engine,
            "evaluation_reference": "Synthetic Nursing Handover Reference Corpus (101 Documents)"
        }
    }

    # STEP 8: Store in SQLite history
    try:
        db.save_analysis(
            report_id=report_id,
            raw_text=raw_text,
            preprocessed_text=preprocessed_text,
            structured_data=response_data
        )
    except Exception as db_err:
        print(f"Warning: could not persist to SQLite history: {db_err}")

    return response_data


@router.get("/history")
async def get_history(limit: int = 20):
    """
    Returns recent analysis runs from SQLite.
    """
    try:
        records = db.get_recent_analyses(limit=limit)
        return {"history": records}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")


# ==============================================================================
# Patient Database & Demonstration Endpoints (Phase 2A-2B)
# ==============================================================================

@router.get("/patients")
async def list_patients(search: Optional[str] = None):
    """
    Returns index of synthetic demo patient records.
    Supports optional search filtering across name, display_id, ward, or consultant.
    """
    try:
        patients = db.list_patients(search=search)
        return {
            "total_count": len(patients),
            "total_patients": len(patients),
            "search_query": search,
            "patients": patients
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve patients: {str(e)}")


@router.get("/patients/{patient_id}")
async def get_patient_profile(patient_id: str):
    """
    Retrieves a single patient profile by primary key id or display_id.
    Includes latest simulated vitals if present.
    Returns 404 for unknown patient identifiers.
    """
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")
    return patient


@router.post("/patients", status_code=201)
async def create_patient_record(payload: PatientCreate):
    """
    Registers a new synthetic demonstration patient record.
    Rejects duplicate display_id with an appropriate 400 response.
    Auto-generates unique display_id if omitted.
    """
    if not payload.name or not payload.name.strip():
        raise HTTPException(status_code=400, detail="Patient 'name' cannot be empty or whitespace only.")

    try:
        data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        new_patient = db.create_patient(data)
        return new_patient
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create patient: {str(e)}")


# ==============================================================================
# Patient Note Lifecycle Endpoints (Phase 2C)
# ==============================================================================

@router.post("/patients/{patient_id}/notes", status_code=201)
async def create_patient_note(patient_id: str, payload: NoteCreate):
    """
    Creates a new clinical note for a specific patient in 'Draft' status.
    Preserves raw text verbatim without running NLP models.
    """
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")

    if not payload.raw_text.strip():
        raise HTTPException(status_code=400, detail="Clinical note text cannot be empty or whitespace only.")

    try:
        note = db.create_patient_note(
            patient_id=patient["id"],
            raw_text=payload.raw_text,
            author_identifier=payload.author_identifier
        )
        return note
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create patient note: {str(e)}")


@router.get("/patients/{patient_id}/notes")
async def list_patient_notes(patient_id: str):
    """
    Retrieves all chronological clinical notes belonging to a specific patient.
    Prevents cross-patient note access.
    """
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")

    try:
        notes = db.get_patient_notes(patient["id"])
        return {
            "patient_id": patient["id"],
            "display_id": patient["display_id"],
            "total_notes": len(notes),
            "notes": notes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve patient notes: {str(e)}")


@router.post("/patients/{patient_id}/notes/{note_id}/process")
async def process_patient_note(patient_id: str, note_id: int):
    """
    Processes an existing saved note using the PULSE NLP pipeline.
    Persists structured extraction output to note_extractions table.
    Updates note status from 'Draft' to 'Processed'.
    Explicitly tags extracted output with an unreviewed status.
    """
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")

    note = db.get_patient_note(patient["id"], int(note_id))
    if not note:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found for patient '{patient_id}'.")

    raw_text = note["raw_text"]
    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="Cannot process an empty note.")

    # 1. Preprocess note text
    prep_res = clinical_preprocessor.preprocess(raw_text)
    preprocessed_text = prep_res["preprocessed_text"]

    # 2. Extract clinical entities
    engine_name = "Bio_ClinicalBERT" if clinical_bert_extractor.is_available() else "Hybrid Rule Engine"
    if clinical_bert_extractor.is_available():
        entities = clinical_bert_extractor.extract(preprocessed_text)
    else:
        entities = clinical_entity_extractor.extract(preprocessed_text)

    # 3. Extract events
    events = clinical_event_extractor.extract(preprocessed_text, entities=entities)

    # 4. Extract temporal relationships
    temporal_info = clinical_temporal_extractor.extract(preprocessed_text, events=events)

    # 5. Extract pending tasks and follow up
    pending_tasks = structured_handover_generator.extract_pending_tasks(preprocessed_text, events=events)
    follow_up = structured_handover_generator.extract_follow_up(preprocessed_text, pending_tasks=pending_tasks)

    # 6. Generate structured clinical handover
    structured = structured_handover_generator.generate_structured_handover(
        text=preprocessed_text,
        entities=entities,
        events=events,
        temporal_info=temporal_info,
        pending_tasks=pending_tasks,
        follow_up=follow_up
    )

    # Explicit unreviewed clinical assertion metadata
    extraction_payload = {
        "review_status": "ai_generated_unreviewed",
        "status_label": "AI-generated — not yet reviewed",
        "is_human_reviewed": False,
        "preprocessed_text": preprocessed_text,
        "entities": entities,
        "events": events,
        "temporal_information": temporal_info,
        "pending_tasks": pending_tasks,
        "follow_up": follow_up,
        "structured_handover": structured,
        "executive_summary": structured.get("executive_summary", ""),
        "isbar": structured.get("isbar", {}),
        "clinical_risks": entities.get("clinical_risks", []),
        "disclaimer": "This information was automatically structured by AI and is not verified by a clinician. Do not use for clinical diagnosis or treatment."
    }

    try:
        updated_note = db.process_patient_note(
            patient_id=patient["id"],
            note_id=int(note_id),
            extraction_data=extraction_payload,
            engine_used=engine_name
        )
        return updated_note
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process and persist note: {str(e)}")


@router.get("/patients/{patient_id}/notes/{note_id}")
async def get_patient_note(patient_id: str, note_id: int):
    """
    Retrieves a single clinical note by patient_id and note_id.
    Includes original note text, original AI extraction, latest human review,
    note lifecycle status, reviewer identifier, and review timestamp.
    """
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")

    note = db.get_patient_note(patient["id"], int(note_id))
    if not note:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found for patient '{patient_id}'.")

    return note


@router.post("/patients/{patient_id}/notes/{note_id}/review")
async def review_patient_note(patient_id: str, note_id: int, payload: NoteReviewRequest):
    """
    Saves a clinician review of a processed clinical note.
    - Validates patient and note existence and cross-patient isolation.
    - Permits review only for notes that have been successfully processed (status != 'Draft').
    - Uses an atomic database transaction to persist review in note_reviews and update status to 'Reviewed'.
    - Returns saved review, note status, review timestamp, and reviewer identifier.
    - Preserves original note text and original AI extraction completely untouched.
    """
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found.")

    note = db.get_patient_note(patient["id"], int(note_id))
    if not note:
        raise HTTPException(status_code=404, detail=f"Note {note_id} not found for patient '{patient_id}'.")

    if not payload.reviewed_data or not isinstance(payload.reviewed_data, dict):
        raise HTTPException(status_code=400, detail="reviewed_data must be a non-empty structured dictionary.")

    try:
        result = db.review_patient_note(
            patient_id=patient["id"],
            note_id=int(note_id),
            reviewed_data=payload.reviewed_data,
            reviewer_identifier=payload.reviewer_identifier,
            review_notes=payload.review_notes
        )
        return result
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to persist clinician review: {str(e)}")


