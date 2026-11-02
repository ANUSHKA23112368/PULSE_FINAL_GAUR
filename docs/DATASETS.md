# PULSE Dataset Registry

This document catalogues every dataset integrated or supported by PULSE, including access instructions, citation requirements, and label mapping details.

---

## 1. NICTA Synthetic Nursing Handover Dataset (Primary Gold Corpus)

| Field | Detail |
|---|---|
| **Source** | Suominen et al., NICTA / Australian National University |
| **Year** | 2015 |
| **Domain** | Acute / sub-acute nursing shift handovers |
| **Documents** | 101 free-text nursing shift reports |
| **Gold Spans** | 2,103 clinically adjudicated entity spans |
| **Schema** | 9 standardized clinical categories |
| **Annotation** | Manual, with inter-annotator agreement (IAA) reported |
| **Access** | Bundled in `data/101writtenfreetextreports/` (read-only) |
| **Format** | Plain `.txt`, verbatim, UTF-8 |

### Corpus Statistics
- Average report length: **71.65 words**
- Minimum report length: **19 words**
- Maximum report length: **209 words**
- Total corpus tokens: **~7,214**
- Unique vocabulary tokens: **~1,441**

### Citation
```
Suominen H. et al. (2015). Benchmarking clinical NLP algorithms on nursing shift handover data.
NICTA Technical Report. Canberra: Australian National University.
```

---

## 2. Hospital Training Pack — ISBAR Augmentation Corpus

| Field | Detail |
|---|---|
| **Type** | Synthetic augmentation (de-identified) |
| **Documents** | 160 multi-shift ISBAR handover notes |
| **Combined with NICTA** | 261 total training documents |
| **Token Spans** | ~9,500+ labelled entity spans |
| **Generation** | Rule-seeded clinical pattern generation with random sampling |
| **Clinical Coverage** | ICU, PACU, Med-Surg, Telemetry, Subacute wards |
| **File** | `data/gold_standard/hospital_training_corpus.json` |

### Clinical Entity Categories Covered
- IV line titration rates and infusion targets
- NEWS2 early warning deterioration scores (0–20 scale)
- PRN (as-needed) analgesia with dose ranges
- Fluid balance: intake vs. output across 24-hour periods
- Ventilator settings: PEEP, FiO₂, tidal volume
- Vasopressor weaning protocols (noradrenaline, vasopressin)

---

## 3. n2c2 2018 Track 2 — Adverse Drug Events & Medication Extraction

| Field | Detail |
|---|---|
| **Organizer** | Harvard n2c2 Shared Task Committee |
| **Year** | 2018 |
| **Domain** | Medication extraction from clinical discharge summaries |
| **Annotation Types** | Drug, Dosage, Route, Frequency, Reason, ADE |
| **Access** | Requires n2c2 Data Use Agreement (DUA) — NOT bundled |
| **Ingestion** | Via `backend/dataset/external_loader.py` |
| **Label Mapping** | `configs/label_map.yaml` → `n2c2_2018_to_pulse` section |

### Label Mapping (n2c2 → PULSE)
| n2c2 Label | PULSE Category |
|---|---|
| Drug | Medication |
| Dosage | Medication |
| Route | Medication |
| Frequency | Medication |
| Reason | Clinical_Condition |
| ADE | Clinical_Observation |

### Usage
```bash
export PULSE_EXTERNAL_DATA_DIR=/path/to/n2c2_2018/train
python -c "from backend.dataset.external_loader import ExternalDatasetLoader; loader = ExternalDatasetLoader(); docs = loader.load_directory(); print(len(docs))"
```

---

## 4. i2b2 2010 Clinical Relations & Entity Challenge

| Field | Detail |
|---|---|
| **Organizer** | i2b2 NLP Research Center |
| **Year** | 2010 |
| **Domain** | Hospital discharge summaries and clinical progress notes |
| **Annotation Types** | Problem, Treatment, Test |
| **Access** | Requires PhysioNet / i2b2 Data Use Agreement — NOT bundled |
| **Ingestion** | Via `backend/dataset/external_loader.py` |
| **Label Mapping** | `configs/label_map.yaml` → `i2b2_2010_to_pulse` section |

### Label Mapping (i2b2 → PULSE)
| i2b2 Label | PULSE Category |
|---|---|
| problem | Clinical_Condition |
| treatment | Medication |
| test | Investigation_Procedure |

---

## 5. MIMIC-III Critical Care Database (Pretraining Backbone)

| Field | Detail |
|---|---|
| **Source** | Beth Israel Deaconess Medical Center (BIDMC) |
| **Year** | 2016+ (ongoing updates) |
| **Domain** | ICU critical care — clinical notes, discharge summaries, nursing notes |
| **Scale** | 2+ million de-identified clinical notes |
| **Access** | Requires PhysioNet credentialed access + DUA — NOT bundled |
| **Role in PULSE** | Pretraining foundation for `emilyalsentzer/Bio_ClinicalBERT` |
| **Model** | `backend/models/clinical_bert/` (fine-tuned checkpoint) |

### Citation
```
Johnson AEW et al. MIMIC-III, a freely accessible critical care database.
Scientific Data, 2016. DOI: 10.1038/sdata.2016.35
```

---

## External Dataset Ingestion Guide

Point `PULSE_EXTERNAL_DATA_DIR` to a directory containing paired `.txt` + `.ann` files:

```
external_data/
├── note_001.txt
├── note_001.ann
├── note_002.txt
├── note_002.ann
└── ...
```

Run ingestion:
```python
from backend.dataset.external_loader import ExternalDatasetLoader
loader = ExternalDatasetLoader(data_dir="/path/to/external_data")
documents = loader.load_directory()
print(f"Loaded {len(documents)} documents | Stats: {loader.stats}")
```
