# PULSE API Reference

Base URL: `http://127.0.0.1:8000`

---

## Core Endpoints

### GET `/`
Returns system metadata and available endpoint map.

**Response:**
```json
{
  "name": "PULSE API",
  "description": "Patient Update & Log Structuring Engine",
  "subtitle": "NLP-based Clinical Handover Information Extraction and Event Structuring System",
  "docs_url": "/docs",
  "health_check": "/api/health",
  "disclaimer": "..."
}
```

---

### GET `/api/health`
Returns system health, dataset load status, and model status.

**Response:**
```json
{
  "status": "healthy",
  "system": "PULSE (Patient Update & Log Structuring Engine)",
  "version": "1.0.0-prototype",
  "dataset_loaded": true,
  "total_reports": 101,
  "total_patients": 10,
  "model_status": {
    "current_engine": "Bio_ClinicalBERT Real-Time Extraction Pipeline",
    "clinical_bert_loaded": true,
    "clinical_bert_model": "emilyalsentzer/Bio_ClinicalBERT"
  }
}
```

---

### GET `/api/dataset/stats`
Returns dynamic EDA statistics computed from disk files.

**Response:**
```json
{
  "total_reports": 101,
  "avg_word_count": 71.65,
  "min_word_count": 19,
  "max_word_count": 209,
  "total_tokens": 7214,
  "unique_vocabulary": 1441
}
```

---

### GET `/api/reports`
Returns a list of all available report IDs and metadata.

---

### GET `/api/reports/{report_id}`
Returns the raw verbatim text of a specific nursing handover report.

**Path Parameters:**
| Parameter | Type | Description |
|---|---|---|
| `report_id` | `int` | Report index (0–100) |

---

### POST `/api/analyze`
Analyzes a nursing handover text through the full 8-stage NLP pipeline.

**Request Body:**
```json
{
  "text": "Patient John Smith, 72M, Bed 4A. Admitted with SOB and chest pain...",
  "report_id": "0"
}
```

**Response:**
```json
{
  "structured_handover": {
    "patient_info": {...},
    "current_condition": [...],
    "medications": [...],
    "investigations": [...],
    "pending_tasks": [...],
    ...
  },
  "highlighted_spans": [...],
  "preprocessing_diff": {...},
  "pipeline_stages": [...]
}
```

---

### GET `/api/evaluation/research`
Returns empirical benchmark evaluation results against the gold standard corpus.

---

### GET `/api/patients`
Returns all registered demo patient profiles.

---

### POST `/api/training/start`
Initiates a Bio_ClinicalBERT fine-tuning run with SSE progress streaming.

**Request Body:**
```json
{
  "epochs": 3,
  "synthetic_count": 160,
  "trainable_last_n": 2,
  "learning_rate": 3e-5
}
```

---

## Interactive Docs
Full Swagger UI available at: `http://127.0.0.1:8000/docs`
ReDoc available at: `http://127.0.0.1:8000/redoc`
