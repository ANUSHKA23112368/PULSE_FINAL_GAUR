# PULSE System Architecture

## Overview

PULSE implements an 8-stage modular clinical NLP pipeline that transforms unstructured nursing shift handover narratives into standardized 9-category structured handovers.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                  UNSTRUCTURED NURSING HANDOVER TEXT              │
│         (Free-text, abbreviations, clinical shorthand)           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  STAGE 1        │
                    │  PREPROCESSING  │
                    │  ─────────────  │
                    │  • Unicode norm │
                    │  • Preserve @   │
                    │  • Preserve +_  │
                    │  • Measurement  │
                    │    preservation │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  STAGE 2        │
                    │  BIO CLINICAL   │
                    │  BERT NER       │
                    │  ─────────────  │
                    │  • Token classif│
                    │  • B-/I- tagging│
                    │  • Char offsets │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  STAGE 3        │
                    │  ENTITY EXTRACT │
                    │  ─────────────  │
                    │  • Demographics │
                    │  • Conditions   │
                    │  • Medications  │
                    │  • Vitals       │
                    │  • Abbrev. dict │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  STAGE 4        │
                    │  EVENT EXTRACT  │
                    │  ─────────────  │
                    │  • Admissions   │
                    │  • Procedures   │
                    │  • MDT referrals│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  STAGE 5        │
                    │  TEMPORAL NLP   │
                    │  ─────────────  │
                    │  • Clock times  │
                    │  • Shift anchors│
                    │  • Relative time│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  STAGE 6        │
                    │  PENDING TASKS  │
                    │  ─────────────  │
                    │  • Outstanding  │
                    │    nursing duties│
                    │  • Priority rank│
                    └────────┬────────┘
                             │
                    ┌────────▼────────────────────────────────┐
                    │  STAGE 7 — 9-CATEGORY STRUCTURED OUTPUT  │
                    │  ──────────────────────────────────────  │
                    │  1. Patient Information                   │
                    │  2. Current Condition                     │
                    │  3. Medical History                       │
                    │  4. Medications / Treatment               │
                    │  5. Investigations                        │
                    │  6. Clinical Events                       │
                    │  7. Temporal Information                  │
                    │  8. Pending Tasks                         │
                    │  9. Follow-up                             │
                    └────────┬────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  STAGE 8        │
                    │  REACT DASHBOARD│
                    │  ─────────────  │
                    │  • Source text  │
                    │    highlighting │
                    │  • Evidence     │
                    │    citations    │
                    │  • Export       │
                    └─────────────────┘
```

---

## Component Breakdown

### Backend (`backend/`)
| Module | Responsibility |
|---|---|
| `main.py` | FastAPI application, route definitions, startup events |
| `models/clinical_bert/` | Fine-tuned Bio_ClinicalBERT checkpoint |
| `dataset/external_loader.py` | n2c2/i2b2 external corpus ingestion |
| `pulse_prototype.db` | SQLite cache for analysis run history |

### Frontend (`frontend/src/`)
| Component | Responsibility |
|---|---|
| `App.jsx` | Root application router and global state |
| `pages/DashboardPage.jsx` | Main landing page with EDA stats and pipeline overview |
| `pages/AnalyzePage.jsx` | Interactive handover analysis with report selector |
| `pages/DatasetPage.jsx` | Dataset browser with corpus catalog |
| `pages/ResearchEvaluationPage.jsx` | Empirical benchmark results and model comparison |
| `pages/ModelTrainingDashboardPage.jsx` | Live fine-tuning telemetry via SSE |
| `pages/AboutPage.jsx` | Technical specifications and research background |
| `services/api.js` | Axios-based API client |

### Scripts (`scripts/`)
| Script | Responsibility |
|---|---|
| `train_production_clinicalbert.py` | Full Bio_ClinicalBERT fine-tuning pipeline |

### Configuration (`configs/`)
| File | Responsibility |
|---|---|
| `label_map.yaml` | Maps external dataset labels to PULSE categories |

---

## Data Flow

```
Request: POST /api/analyze { text, report_id }
    ↓
FastAPI Router → NLP Pipeline Manager
    ↓
Stage 1: Preprocessor.clean(text)
    ↓
Stage 2: ClinicalBERTExtractor.predict_spans(tokens)
    ↓
Stage 3: EntityExtractor.extract_all(spans, text)
    ↓
Stage 4: EventExtractor.extract_events(text, entities)
    ↓
Stage 5: TemporalExtractor.extract_times(text)
    ↓
Stage 6: PendingTaskExtractor.extract_pending(text)
    ↓
Stage 7: StructuredHandoverBuilder.build_9cat(all_extractions)
    ↓
Stage 8: Response → Frontend React Dashboard
```

---

## Deployment Architecture

```
┌──────────────────┐     HTTP/REST      ┌──────────────────┐
│  React Frontend  │ ◄────────────────► │  FastAPI Backend  │
│  Vite Dev Server │                    │  Uvicorn ASGI    │
│  localhost:5173  │                    │  127.0.0.1:8000  │
└──────────────────┘                    └────────┬─────────┘
                                                 │
                                    ┌────────────┼────────────┐
                                    │            │            │
                              ┌─────▼────┐ ┌────▼─────┐ ┌───▼─────┐
                              │ SQLite   │ │ BERT     │ │ Data    │
                              │ Cache DB │ │ Model    │ │ Files   │
                              │ .db      │ │ /models/ │ │ /data/  │
                              └──────────┘ └──────────┘ └─────────┘
```
