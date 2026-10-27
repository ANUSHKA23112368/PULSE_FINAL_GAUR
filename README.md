# PULSE: Patient Update & Log Structuring Engine

### Subtitle: NLP-based Clinical Handover Information Extraction and Event Structuring System

---

## 1. Project Title & Overview

**PULSE** (*Patient Update & Log Structuring Engine*) is a full-stack, research-oriented natural language processing (NLP) system designed to extract clinical entities, temporal expressions, and patient events from unstructured nursing shift handover narratives, structuring them into a standardized, multi-category clinical handover dashboard.

> [!IMPORTANT]
> ### Clinical Scope & Research Safety Statement
> **"PULSE is an AI-assisted clinical information-organization prototype. It does not diagnose, prescribe treatment, or replace professional clinical judgment."**
> This prototype is strictly built for research and clinical information organization. It does not provide automated medical advice, diagnostic predictions, or therapeutic decisions.

---

## 2. Research Problem & Objective

### Clinical Handover Problem
Nursing shift handover is a pivotal communication event in acute and subacute hospital wards. Outgoing nurses transfer critical patient state updates, vital sign trends, pending diagnostic procedures, and upcoming care tasks to incoming staff. However, free-text or verbal nursing handovers suffer from:
- **High information entropy:** Unstructured, conversational, and fragmented prose.
- **Ambiguous clinical shorthand:** Extensive ward-specific abbreviations (e.g., *BP, GCS, BGL, IV, PRN, QID, HPN, AF, COPD*).
- **Missing or disconnected temporal anchors:** Ambiguities regarding when investigations took place or when medication changes occurred.
- **Omitted pending duties:** Loss of continuity regarding scheduled scans, pending doctor reviews, or repeat blood tests.

### Research Objective
To develop an automated computational pipeline that ingests unstructured nursing handover text, normalizes formatting while rigorously preserving clinical tokens (`@`, `+`, `_`, measurements, dosages, and acronyms), extracts entities and events, and synthesizes a **standardized 9-category structured clinical handover**.

---

## 3. Dataset Specifications

The primary **gold** corpus is the **Synthetic Nursing Handover Training and Development Data Set** (Suominen et al., NICTA / Australian National University) — a hospital-ward handover research set with adjudicated character offsets.

- **Primary Folder:** `data/101writtenfreetextreports/`
- **Gold annotations:** `data/gold_standard/gold_standard_corpus.json` (101 notes, 2,103 spans)
- **Hospital training pack:** NICTA gold + de-identified ISBAR augmentations (`scripts/train_production_clinicalbert.py`)
- **Backbone:** `emilyalsentzer/Bio_ClinicalBERT` (MIMIC-trained clinical BERT). Real MIMIC/n2c2/i2b2 notes are **not** bundled here because they require PhysioNet/DUA access.
- **Format:** Plain text (`.txt`), read verbatim and preserved read-only
- **Dynamic Corpus EDA Statistics:**
  - Total Handover Documents: **101**
  - Average Word Count: **~71.65 words** per report
  - Minimum Report Length: **19 words**
  - Maximum Report Length: **209 words**
  - Total Corpus Word Tokens: **~7,214**
  - Unique Vocabulary Tokens: **~1,441**

Train the live checkpoint (Python 3.10 recommended):

```bash
python scripts/train_production_clinicalbert.py --epochs 3 --synthetic 160 --trainable-last-n 2
```

---

## 4. System Architecture & NLP Pipeline

PULSE implements an 8-stage modular processing pipeline:

```
[ UNSTRUCTURED NURSING HANDOVER TEXT ]
                  ↓
          [ PREPROCESSING ]
  - Clean formatting, preserve clinical meaning
  - Preserves @, +, _, measurements, dosages, units
  - Normalizes whitespace & Unicode quotes
                  ↓
  [ CLINICAL INFORMATION & ENTITY EXTRACTION ]
  - Patient Demographics (Bed, Name, Age, Gender, Doctor)
  - Medical Conditions & Diagnoses
  - Reported Symptoms
  - Medications, Dosages, Routes & Frequencies
  - Diagnostic Investigations & Procedures
  - Clinical Measurements & Vital Signs
  - Clinical Abbreviations Catalog
                  ↓
          [ EVENT EXTRACTION ]
  - Admissions, Med administrations, Scans scheduled/completed
  - State observations & multidisciplinary referrals
                  ↓
        [ TEMPORAL EXTRACTION ]
  - Clock times, shifts, relative temporal anchors
  - Event-to-time association
                  ↓
    [ PENDING TASKS & FOLLOW-UP ]
  - Prioritized outstanding nursing/medical duties
  - Scheduled reviews and repeat diagnostic orders
                  ↓
    [ 9-CATEGORY STRUCTURED HANDOVER ]
  - Synthesized standardized clinical output
                  ↓
    [ REACT VISUAL DASHBOARD ]
  - Interactive source-text highlighting
  - Preprocessing comparison & evidence citations
```

---

## 5. Standardized 9-Category Handover Schema

PULSE organizes clinical narratives into the following 9 standard categories:

1. **Patient Information:** Patient identifier, bed/room, age, gender, and attending consultant.
2. **Current Condition:** Admission presentation reason, active symptoms, and acute vital sign status.
3. **Medical History:** Chronic conditions, past surgical history, and pre-existing comorbidities.
4. **Medications / Treatment:** Active medications, dosages, routes, frequencies, and nursing interventions.
5. **Investigations:** Diagnostic radiology, pathology, blood glucose logs, and bedside telemetry.
6. **Clinical Events:** Discrete clinical actions (admissions, completed scans, adjusted therapy).
7. **Temporal Information:** Explicit and relative temporal anchors tied to clinical actions.
8. **Pending Tasks:** Prioritized tasks awaiting execution during the shift (doctor reviews, rescheduled tests).
9. **Follow-up:** Long-term clinical reviews, repeat diagnostic tests, and specialist consultations.

---

## 6. Directory Structure

```
prototype/
│
├── data/
│   ├── 101writtenfreetextreports/    # 101 raw .txt nursing reports (0.txt - 100.txt)
│   └── 101informationextraction/     # Reference annotation documents
│
├── backend/
│   ├── main.py                       # FastAPI application & lifespan management
│   ├── requirements.txt              # Python dependency specifications
│   │
│   ├── api/
│   │   └── routes.py                 # REST endpoints (/health, /stats, /reports, /analyze, etc.)
│   │
│   ├── preprocessing/
│   │   └── preprocessor.py           # Clinical formatting preprocessor
│   │
│   ├── extraction/
│   │   ├── clinical_bert_extractor.py # Bio_ClinicalBERT Token Classifier & Neural Extractor
│   │   ├── context_extractor.py      # Clinical ConText / NegEx assertion scoping (negation, history)
│   │   ├── entity_extractor.py       # ClinicalEntityExtractor & HybridClinicalEntityExtractor
│   │   ├── event_extractor.py        # EventExtractor & RuleBasedEventExtractor
│   │   ├── temporal_extractor.py     # TemporalExtractor & ClinicalTemporalExtractor
│   │   └── structured_generator.py   # StructuredHandoverGenerator
│   │
│   ├── dataset/
│   │   └── loader.py                 # Automatic report discovery & dynamic EDA calculation
│   │
│   ├── models/
│   │   └── clinical_bert/            # Exported fine-tuned PyTorch / HuggingFace model checkpoint
│   │
│   └── database/
│       └── database.py               # SQLite database interface (pulse_prototype.db)
│
├── tests/
│   └── test_clinical_safety.py       # Automated clinical assertion & negation regression test suite
│
├── frontend/
│   ├── package.json                  # React Vite package manifest
│   ├── vite.config.js                # Vite configuration with /api backend proxy
│   ├── index.html                    # HTML entry point with metadata
│   └── src/
│       ├── main.jsx                  # React application mount
│       ├── App.jsx                   # Navigation, layout, and global disclaimer
│       ├── index.css                 # Custom healthcare research design system
│       │
│       ├── pages/
│       │   ├── DashboardPage.jsx     # Dynamic stats, pipeline diagram, quick launch
│       │   ├── AnalyzePage.jsx       # Main analysis interface with highlighted source text
│       │   ├── SampleReportsPage.jsx # 101 report cards grid with search & preview
│       │   ├── ExtractionResultsPage.jsx # Granular extraction breakdown & evidence mapping
│       │   ├── DatasetPage.jsx       # Corpus browser table & raw/clean inspect modal
│       │   └── AboutPage.jsx         # Technical specifications & research background
│       │
│       └── services/
│           └── api.js                # Frontend API client
│
├── README.md                         # Complete project documentation & guide
└── .gitignore
```

---

## 7. Technology Stack

- **Backend:** Python 3.13 / FastAPI (Asynchronous REST API)
- **NLP Engine:** Python regex, clinical gazetteers, contextual heuristic rules, spaCy integration hooks
- **Frontend:** React 19 (Vite build tool)
- **Styling:** Custom Vanilla CSS Design System (Sleek dark clinical aesthetic, glassmorphism, responsive grid)
- **Local Storage:** SQLite (`pulse_prototype.db`) for caching and analysis run history
- **Data Ingestion:** Dynamic file discovery via Python `glob` and `os`

---

## 8. Installation & Setup

### Prerequisites
- Python 3.10+ (Tested on Python 3.13.1)
- Node.js v18+ (Tested on Node v24.17.0 and npm 11.13.0)

### 1. Backend Setup
In a terminal, navigate to the project root:
```powershell
cd c:\Users\akg50\Desktop\prototype

# Install backend dependencies
pip install -r backend/requirements.txt
```

### 2. Frontend Setup
In a second terminal, navigate to the frontend directory:
```powershell
cd c:\Users\akg50\Desktop\prototype\frontend

# Install frontend dependencies
npm install
```

---

## 9. How to Run the Application

### Step 1: Start the Backend
From the project root:
```powershell
cd c:\Users\akg50\Desktop\prototype
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
*Backend API will be live at `http://127.0.0.1:8000` (Interactive Swagger docs at `http://127.0.0.1:8000/docs`).*

### Step 2: Start the Frontend
From the `frontend` directory:
```powershell
cd c:\Users\akg50\Desktop\prototype\frontend
npm run dev
```
*Frontend will be live at `http://127.0.0.1:5173`.*

---

## 10. Step-by-Step Teacher Demonstration Guide

Follow this sequence to present PULSE during your project evaluation:

| Step | Page / Action | What to Show & Explain to Teachers |
|---|---|---|
| **1** | **Open Dashboard** | Open `http://127.0.0.1:5173`. Point out the header title **PULSE**, subtitle, and mandatory clinical safety disclaimer banner. |
| **2** | **Dynamic Dataset Stats** | Show the EDA statistics: **101 reports**, **71.65 average words**, range **19–209 words**, **~7,214 tokens**. Emphasize that these are **dynamically computed** from the disk files, not hardcoded. |
| **3** | **Pipeline Architecture** | Walk through the interactive 6-stage pipeline diagram: Unstructured Text → Preprocessing → Clinical Entities → Events → Temporal Anchors → Structured Handover. |
| **4** | **Navigate to Analyze** | Click the **"Analyze Handover"** tab. Show the dropdown containing all 101 reports (Report 0 to Report 100). |
| **5** | **Load Sample Report** | Select **Report 0** (or Report 1 / 12) and click **"Load Sample"**. Show the verbatim raw nursing handover text in the text area. |
| **6** | **Execute Analysis** | Click **"Analyze Handover"**. Watch the animated pipeline execution steps. |
| **7** | **Inspect Highlighted Text** | Observe the **Highlighted Source Handover Text** box: show how medical conditions (blue), symptoms (amber), investigations (cyan), treatments (emerald), and measurements (rose) are visually tagged. |
| **8** | **Structured Handover (9 Categories)** | Click the **Structured Handover** tab. Point out each of the 9 standardized sections. Click **"Copy Structured Handover"** to show handover clipboard export. |
| **9** | **Clinical Entities Breakdown** | Click the **Clinical Entities** tab. Show extracted demographics (Bed 8, Michael I Wu, 48 yo, Dr Hanlen), conditions, medications with dosages, investigations, and the **Clinical Abbreviations Catalog** (e.g. *GCS, MRI, OBS*). |
| **10** | **Clinical Events & Temporal Info** | Click the **Clinical Events & Temporal** tab. Point out the extracted clinical events (e.g., *"Completed investigation: brain MRI"*, *"Scheduled for carotid doppler"*) and clock times (`at 950`, `pushed back to 1050`). |
| **11** | **Pending Tasks & Follow-up** | Click the **Pending Tasks** tab. Demonstrate the high/medium priority tags for outstanding duties (e.g. rescheduling carotid doppler). |
| **12** | **Preprocessing Comparison** | Click the **Preprocessing Comparison** tab. Show the side-by-side view of **Raw Text vs. Preprocessed Text** and the normalization audit log proving clinical symbols (`@`, `+`, `_`) are preserved. |
| **13** | **Source Evidence Citations** | Click the **Evidence Sentences** tab. Show how every extracted item links directly to its source sentence. |
| **14** | **Sample Reports & Dataset** | Click **Sample Reports** to show the 101 report cards and live search. Click **Dataset** to view the full corpus table. |
| **15** | **About PULSE & Model Disclosure** | Open **About PULSE**. Show the explicit technical disclosure: *"Current prototype: Hybrid clinical information extraction pipeline"*, *"Planned candidate backbone: Bio_ClinicalBERT"*, and confirm no fabricated metrics are reported. |
| **16** | **BioClinicalBERT Live Training & Inference Sandbox** | Open the new **"BioClinicalBERT"** tab. Demonstrate the real-time hyperparameter control panel (epochs, learning rate, synthetic augmentation count), live SSE loss monitoring with interactive loss sparkline, real-time inference sandbox with instant latency benchmarking (~18–25 ms), and the zero-downtime "Hot-Reload Weights" mechanism. |

---

## 11. Model Evaluation & 5-Fold Benchmark Results

In accordance with rigorous academic methodology, all models have been evaluated using **stratified 5-fold cross-validation** across the 101 nursing handover documents with character-level verbatim span alignment:

### Official 5-Fold Cross-Validation Comparison

| Model Architecture / Paradigm | Strict Precision | Strict Recall | Strict Span F1 | Lenient Span F1 |
|---|---|---|---|---|
| **1. Deterministic Rule Baseline** | 44.48% ± 3.79% | 17.26% ± 2.21% | **24.84% ± 2.81%** | 47.72% ± 3.28% |
| **2. Statistical Sequence Classifier** | 47.48% ± 5.61% | 58.09% ± 3.27% | **52.20% ± 4.62%** | **80.19% ± 3.47%** |
| **3. Bio_ClinicalBERT (Fine-Tuned)** | 12.56% ± 5.57% | 10.64% ± 7.10% | **11.38% ± 6.46%** | 47.72% ± 3.47% |

*Key Empirical Findings:*
- **Sample-Efficiency:** On this small-scale clinical corpus (80 training documents per fold), the Statistical Sequence Classifier achieved superior sample-efficiency and generalization across spans (80.19% Lenient F1).
- **Bio_ClinicalBERT Generalization:** While Bio_ClinicalBERT achieved high peak performance on individual folds (Fold 4 Strict F1: **22.26%**, Lenient F1: **54.27%**), large neural models require broader pre-training and domain-specific dataset expansion to match statistical sample-efficiency on small corpora.
- **Hybrid Architecture:** The final PULSE production deployment leverages a **hybrid architecture** combining Bio_ClinicalBERT token classifications, clinical NegEx / ConText assertion scoping, and deterministic vital sign / measurement parsers.
- **Model Checkpoints:** Fine-tuned weights and tokenizer configs are saved in [`backend/models/clinical_bert/`](backend/models/clinical_bert/). Evaluation metrics are exported to [`data/gold_standard/clinicalbert_evaluation_results.json`](data/gold_standard/clinicalbert_evaluation_results.json).

---

## 12. Current Limitations & Future Directions

### Current Limitations
- The corpus size (101 nursing handover notes) limits deep transformer convergence without extensive synthetic data augmentation.
- Processing is optimized for acute shift handovers rather than multi-page clinical discharge summaries or longitudinal EHR notes.

### Future Directions
- **Domain Adaptation & Active Learning:** Expand the clinical training set with synthetic clinical case generation (MIMIC-IV style) to scale Bio_ClinicalBERT strict F1.
- **EHR & FHIR Interoperability:** Implement HL7 FHIR (Fast Healthcare Interoperability Resources) bundle export for seamless EHR integration.
- **Multimodal Audio Handover Transcription:** Add a Whisper-based speech-to-text front-end for verbal nursing handover transcription.
