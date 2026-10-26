# PULSE Model Training & Evaluation Readiness Report
**Document Path**: [docs/benchmark/model_training_readiness.md](file:///c:/Users/akg50/Desktop/prototype/docs/benchmark/model_training_readiness.md)  
**Date**: October 2026  
**System**: PULSE (Patient Update & Log Structuring Engine)  
**Status**: Formal Audit & Readiness Determination  

---

## 1. Executive Summary & Audit Overview

As PULSE transitions toward supervised model training, hyperparameter optimization, and rigorous statistical model comparison, an exhaustive audit was performed on the existing repository. The audit evaluated data assets, training pipelines, feature extraction pipelines, data-split hygiene, transformer fine-tuning feasibility, and computational resource constraints.

### Core Audit Findings
1. **Existing Model Architectures**:
   - **Statistical Classifier**: Documented and verified as an L2-regularized Logistic Regression sequence/token tagger using 14 lexical, morphological, and orthographic features combined with a $\pm 2$ window context and `DictVectorizer(sparse=True)`.
   - **Bio_ClinicalBERT Checkpoint**: Present locally in [backend/models/clinical_bert/](file:///c:/Users/akg50/Desktop/prototype/backend/models/clinical_bert/) (`model.safetensors`, 430 MB, 110M parameters) with a `BertTokenizerFast` tokenizer.
   - **Hybrid Pipeline**: Context-aware rule-based entity recognizer with regex patterns, Indian clinical shorthand normalizer, Roman-Hindi/Hinglish mapping, heuristic attribute binding, and assertion/temporality classifiers.
2. **Data Suitability**:
   - **Historical 101-Note Corpus** ([data/gold_standard/gold_standard_corpus.json](file:///c:/Users/akg50/Desktop/prototype/data/gold_standard/gold_standard_corpus.json)): Contains 101 synthetic nursing handover documents (8,487 tokens, 2,103 annotated spans across 11 macro categories). It **can** train token-level sequence classifiers for entity span extraction. It **cannot** train assertion/temporality classifiers (0 assertion tags) or medication attribute relation linkers (0 relation tags). This dataset was used during iterative development and is **not an independent held-out benchmark**.
   - **Schema Fixtures** ([data/gold_standard/benchmark_schema_fixture.json](file:///c:/Users/akg50/Desktop/prototype/data/gold_standard/benchmark_schema_fixture.json)): Exactly 7 synthetic clinical fixture notes designed for schema validation, attribute binding tests, and unit verification. These are **not valid training or independent evaluation data**.
   - **Planned 250-Note Benchmark**: Designed in Step 4.2 (100 train / 50 val / 100 test), but **not yet collected or annotated**.
3. **Data Leakage & Split Audit**:
   - Document-level split integrity in [data/gold_standard/train_test_splits.json](file:///c:/Users/akg50/Desktop/prototype/data/gold_standard/train_test_splits.json) was audited across all 5 folds: zero document ID overlap across train, validation, and test partitions ($100\%$ disjoint).
   - Zero duplicate notes and zero near-duplicate notes (all pairwise token Jaccard similarities $< 0.35$).
   - Vectorizers are fitted strictly on the training fold (`fit_transform` on train, `transform` on val/test), preventing vocabulary and distribution leakage.
4. **Reproducible Baseline Experiment**:
   - Implemented [scripts/train_statistical_classifier.py](file:///c:/Users/akg50/Desktop/prototype/scripts/train_statistical_classifier.py) executing a leak-free 5-fold cross-validation with inner validation tuning over $C \in \{0.01, 0.1, 1.0, 10.0\}$ and `class_weight` $\in \{\text{None}, \text{'balanced'}\}$.
   - Optimal validation configuration across all 5 folds: $C=1.0, \text{class\_weight}=\text{None}$.
   - Evaluation on held-out test folds: **Strict Span F1 = 51.69% ± 4.62%**, **Lenient Span F1 = 73.49% ± 3.96%**, **Token Accuracy = 78.52% ± 3.17%**.
   - Preserved all historical baseline results and recorded full tuning metrics to [data/gold_standard/statistical_classifier_tuning_results.json](file:///c:/Users/akg50/Desktop/prototype/data/gold_standard/statistical_classifier_tuning_results.json).
5. **Readiness Verdict**:
   - **`READY FOR BASELINE TRAINING`** for the statistical sequence classifier on entity extraction.
   - **`NOT READY — ANNOTATION GAP`** for supervised assertion, temporality, and relation-binding models.

---

## 2. Pipeline Audit & Technical Inventory (Task 1)

### 2.1 File Paths and Modules

| Component | Repository Path | Key Functions / Classes | Role |
|---|---|---|---|
| **Gold Standard Corpus** | [data/gold_standard/gold_standard_corpus.json](file:///c:/Users/akg50/Desktop/prototype/data/gold_standard/gold_standard_corpus.json) | JSON document store (101 notes) | Ground truth entity span annotations |
| **Data Splits** | [data/gold_standard/train_test_splits.json](file:///c:/Users/akg50/Desktop/prototype/data/gold_standard/train_test_splits.json) | 5-fold CV split dictionary | Pre-computed document-level split partitions |
| **Statistical Baseline** | [scripts/evaluate_statistical_baseline.py](file:///c:/Users/akg50/Desktop/prototype/scripts/evaluate_statistical_baseline.py) | `extract_features`, `evaluate_fold` | Historical baseline evaluator |
| **Tuned Training Script** | [scripts/train_statistical_classifier.py](file:///c:/Users/akg50/Desktop/prototype/scripts/train_statistical_classifier.py) | `train_and_tune_statistical_classifier` | Grid search, inner validation, model serialization |
| **ClinicalBERT Pipeline** | [scripts/train_and_evaluate_clinicalbert.py](file:///c:/Users/akg50/Desktop/prototype/scripts/train_and_evaluate_clinicalbert.py) | `ClinicalDataset`, `train_epoch`, `evaluate_model` | Transformer fine-tuning script |
| **Local Checkpoint** | [backend/models/clinical_bert/](file:///c:/Users/akg50/Desktop/prototype/backend/models/clinical_bert/) | `model.safetensors`, `config.json` | Local Bio_ClinicalBERT weights |
| **Benchmark Runner** | [backend/evaluation/benchmark_runner.py](file:///c:/Users/akg50/Desktop/prototype/backend/evaluation/benchmark_runner.py) | `BenchmarkRunner`, `evaluate_all_models` | Multi-model evaluation harness |
| **Unit Verification** | [tests/test_statistical_model_training.py](file:///c:/Users/akg50/Desktop/prototype/tests/test_statistical_model_training.py) | `TestStatisticalModelTraining` | Split integrity, leak-free vectorizer, metric tests |

### 2.2 Feature Extraction and Vectorization

The statistical model uses a token-level contextual feature extractor (`extract_features(tokens, index)`):
1. **Target Token Features**:
   - `token.lower()` (case normalization)
   - Suffixes: `token[-3:]`, `token[-2:]`
   - Prefixes: `token[:3]`, `token[:2]`
   - Orthographic flags: `isupper()`, `istitle()`, `isdigit()`, `has_hyphen`
   - Shape pattern (e.g., `Xxxx`, `dd`, `xxxx`)
   - Clinical pattern flags: `is_measurement` (regex matching numbers with units like `mg`, `bpm`, `mmHg`), `is_vital_keyword` (bp, pulse, temp, spo2, hr, rr, gcs), `is_med_keyword` (iv, po, tds, bd, od, prn, stat)
2. **Contextual Window Features**:
   - Preceding tokens ($i-1, i-2$): lower, title, upper, is_vital, is_med
   - Succeeding tokens ($i+1, i+2$): lower, title, upper, is_vital, is_med
   - Boundary flags: `BOS` (beginning of sentence/note), `EOS` (end of sentence/note)
3. **Vectorization**:
   - Implemented via `sklearn.feature_extraction.DictVectorizer(sparse=True)`.
   - **Crucial Hygiene**: The vectorizer is instantiated per fold and fitted strictly on `train_features` via `.fit_transform()`. The validation and test features are transformed using `.transform()`. Unseen feature keys during validation/testing map to zero columns without error or leakage.

### 2.3 Model Architecture & Classification Scheme

- **Algorithm**: Multi-class L2-penalized Logistic Regression (`sklearn.linear_model.LogisticRegression`).
- **Optimization**: `solver='lbfgs'`, `max_iter=200`, `random_state=42`.
- **Target Schema**: 12 discrete token-level classes:
  - 1 negative class: `"O"` (outside any entity)
  - 11 macro entity classes: `Clinical_Condition`, `Clinical_Observation`, `Medication`, `Investigation_Procedure`, `Care_Activity`, `Plan_Goal`, `Demographics_Name`, `Demographics_Age`, `Demographics_Gender`, `Demographics_Bed`, `Demographics_Doctor`.
- **Span Reconstruction**: Adjacent tokens sharing the same non-`"O"` entity label are merged into span candidates with character start/end offsets determined by whitespace token boundaries.

### 2.4 Dependency Versions and Available Hardware

Environment configuration verified via runtime inspection:
- **Operating System**: Windows 11 AMD64
- **Python**: 3.13.1 (64-bit)
- **PyTorch**: `2.8.0+cpu` (**CPU only**; `torch.cuda.is_available() == False`)
- **Scikit-Learn**: `1.7.1`
- **Transformers**: `4.56.1`
- **Safetensors**: `0.5.3`
- **Hardware Resources**: 12 logical CPU cores, ~15.7 GB physical RAM, 0 available GPUs.

---

## 3. Data Suitability & Annotation Audit (Task 2)

### 3.1 Corpus Inventory & Class Distribution

The repository contains three distinct dataset categories:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            DATASET INVENTORY                                 │
├─────────────────────────────────────────────────────────┬──────────┬─────────┤
│ Dataset Identifier                                      │ Documents│ Status  │
├─────────────────────────────────────────────────────────┼──────────┼─────────┤
│ Historical Gold Standard (gold_standard_corpus.json)    │ 101      │ Active  │
│ Schema Fixtures (benchmark_schema_fixture.json)         │ 7        │ Testing │
│ Planned Independent Benchmark (Design Step 4.2)         │ 250      │ Pending │
└─────────────────────────────────────────────────────────┴──────────┴─────────┘
```

#### Detailed Breakdown of the Historical 101-Note Corpus:
- **Total Documents**: 101
- **Total Word Tokens**: 8,487
- **Total Annotated Spans**: 2,103
- **Annotated Entities Breakdown**:

| Macro Category | Mapped Source Categories (NICTA) | Annotated Spans | Share of Entities |
|---|---|---:|---:|
| `Demographics_Gender` | `gender` | 489 | 23.25% |
| `Clinical_Observation` | `sign_or_symptom`, `test_finding` | 354 | 16.83% |
| `Clinical_Condition` | `medical_condition`, `diagnosis` | 228 | 10.84% |
| `Demographics_Name` | `patient_name` | 200 | 9.51% |
| `Plan_Goal` | `care_plan`, `discharge_plan` | 156 | 7.42% |
| `Investigation_Procedure` | `investigation`, `procedure` | 143 | 6.80% |
| `Medication` | `medication`, `dose`, `route`, `frequency` | 134 | 6.37% |
| `Demographics_Bed` | `bed_number` | 127 | 6.04% |
| `Demographics_Doctor` | `doctor_name` | 104 | 4.95% |
| `Demographics_Age` | `age` | 101 | 4.80% |
| `Care_Activity` | `nursing_activity` | 67 | 3.19% |
| **Total** | 35 NICTA sub-types $\to$ 11 macro classes | **2,103** | **100.0%** |

### 3.2 Annotation Format & Structural Compatibility

1. **Format**: JSON list of documents containing `id`, `text`, and an `entities` list with `text`, `label`, `start_offset`, and `end_offset`.
2. **Granularity**: Character-offset entity spans. Converted at training time into token labels via exact whitespace tokenization.
3. **Model Compatibility**:
   - **Compatible**: Entity span extraction (token classification) using both Logistic Regression and Bio_ClinicalBERT.
   - **Incompatible (Missing Annotations)**:
     - **Assertion Status**: 0 gold assertion annotations (`Positive`, `Negated`, `Possible`, `Conditional`). Cannot train supervised assertion classifiers without annotating assertion attributes.
     - **Temporality**: 0 gold temporality annotations (`Current`, `Historical`, `Planned`). Cannot train temporality classifiers without explicit temporal tags.
     - **Medication Attribute Binding**: 0 relation annotations linking drug names to dosages, frequencies, and routes.
4. **Influence on Historical Development**:
   - The 101 notes were used repeatedly during Phase 1–5 development, heuristic tuning, and baseline audits. **It cannot serve as an independent held-out evaluation set for publication claims.**
5. **Domain & Linguistic Limitations**:
   - All 101 notes are synthetic nursing handover narratives.
   - High prevalence of English shorthand; minimal representation of Hinglish expressions (Hinglish expressions were introduced in fixtures during Phase 5, Step 3).

---

## 4. Data Leakage & Cross-Validation Split Audit (Task 3)

### 4.1 Split Disjointness Verification

The pre-computed splits in [data/gold_standard/train_test_splits.json](file:///c:/Users/akg50/Desktop/prototype/data/gold_standard/train_test_splits.json) were verified using set-theoretic intersection checks across all 5 folds:

```
Fold 0: Train: 60 docs, Val: 21 docs, Test: 20 docs | Intersect(Train, Val, Test) = ∅
Fold 1: Train: 60 docs, Val: 21 docs, Test: 20 docs | Intersect(Train, Val, Test) = ∅
Fold 2: Train: 61 docs, Val: 20 docs, Test: 20 docs | Intersect(Train, Val, Test) = ∅
Fold 3: Train: 61 docs, Val: 20 docs, Test: 20 docs | Intersect(Train, Val, Test) = ∅
Fold 4: Train: 61 docs, Val: 20 docs, Test: 20 docs | Intersect(Train, Val, Test) = ∅
```
Every fold partitions the 101 notes into strictly disjoint subsets with zero document overlap.

### 4.2 Near-Duplicate Document Audit

An all-pairs document similarity matrix was computed using token-level Jaccard similarity:
- **Maximum Pairwise Jaccard**: $0.3421$ (between `doc_043` and `doc_088`).
- **Mean Pairwise Jaccard**: $0.1873$.
- **Exact Duplicates**: 0 documents.
- **Near-Duplicates (Jaccard > 0.8)**: 0 documents.
There is no risk of synthetic note templates leaking verbatim between training and validation partitions.

### 4.3 Feature and Preprocessing Hygiene

1. **Vectorizer Fitting**: In both historical baseline scripts and our newly implemented training script, `DictVectorizer` is fitted exclusively on the `train` fold.
2. **Label Isolation**: Token features depend solely on input character strings, suffixes, shapes, and neighboring token characters. No gold entity labels or downstream pipeline metadata are accessible during feature generation.
3. **Metric Calculation**: Strict and lenient F1 scores are computed strictly from model predictions (`reconstructed_pred_spans`) against gold spans (`gold_spans`).

---

## 5. First Reproducible Training Experiment (Task 4)

### 5.1 Training Protocol & Hyperparameter Search

We developed and executed [scripts/train_statistical_classifier.py](file:///c:/Users/akg50/Desktop/prototype/scripts/train_statistical_classifier.py). The training protocol enforces:
- **5-Fold Nested Cross-Validation**: For each fold, candidate hyperparameters are trained on `train_split` (~60 notes) and scored against `val_split` (~20 notes).
- **Primary Optimization Metric**: **Strict Span F1** (exact match of span start, span end, and macro entity label).
- **Candidate Grid**:
  - Regularization strength $C \in \{0.01, 0.1, 1.0, 10.0\}$
  - Class weighting $\in \{\text{None}, \text{'balanced'}\}$
  - Total combinations per fold: 8 configurations (40 training runs overall).
- **Test Set Quarantine**: The held-out `test_split` (~20 notes) is never touched during hyperparameter tuning; it is evaluated exactly once using the optimal hyperparameter configuration chosen on the validation fold.

### 5.2 Inner Validation Selection Results

| Fold | Best Hyperparameters Selected on Validation | Validation Token Acc | Validation Strict F1 | Validation Lenient F1 |
|:---:|---|:---:|:---:|:---:|
| **0** | $C=1.0, \text{class\_weight}=\text{None}$ | 76.54% | 47.74% | 67.97% |
| **1** | $C=1.0, \text{class\_weight}=\text{None}$ | 79.25% | 46.79% | 72.33% |
| **2** | $C=1.0, \text{class\_weight}=\text{None}$ | 79.52% | 50.80% | 72.96% |
| **3** | $C=1.0, \text{class\_weight}=\text{None}$ | 82.35% | 60.12% | 83.39% |
| **4** | $C=1.0, \text{class\_weight}=\text{None}$ | 78.43% | 49.31% | 69.80% |

All five folds uniformly converged on $C=1.0, \text{class\_weight}=\text{None}$. Setting `class_weight='balanced'` degraded strict F1 by inflating false-positive span boundaries across minority classes.

### 5.3 Held-Out Test Evaluation Results

The selected models evaluated against the quarantined test folds achieved the following performance:

| Fold | Test Token Acc | Test Strict Prec | Test Strict Rec | Test Strict F1 | Test Lenient F1 |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **Fold 0** | 77.16% | 47.16% | 61.27% | 53.30% | 75.31% |
| **Fold 1** | 74.32% | 40.54% | 54.05% | 46.33% | 70.82% |
| **Fold 2** | 82.26% | 52.88% | 59.86% | 56.14% | 74.94% |
| **Fold 3** | 80.82% | 49.79% | 60.30% | 54.55% | 78.64% |
| **Fold 4** | 78.03% | 44.75% | 52.05% | 48.13% | 67.74% |
| **Mean ± SD** | **78.52% ± 3.17%** | **47.02% ± 4.67%** | **57.52% ± 4.22%** | **51.69% ± 4.62%** | **73.49% ± 3.96%** |

*Execution Time*: 73.14 seconds for complete 5-fold grid search and evaluation.  
*Saved Artifact*: [data/gold_standard/statistical_classifier_tuning_results.json](file:///c:/Users/akg50/Desktop/prototype/data/gold_standard/statistical_classifier_tuning_results.json).

### 5.4 Per-Class Performance Analysis

```
┌───────────────────────────┬──────────────┬──────────────┬──────────────┐
│ Entity Class              │ Precision    │ Recall       │ Strict F1    │
├───────────────────────────┼──────────────┼──────────────┼──────────────┤
│ Demographics_Age          │ 92.4%        │ 88.1%        │ 90.2%        │
│ Demographics_Gender       │ 84.7%        │ 91.2%        │ 87.8%        │
│ Demographics_Bed          │ 81.3%        │ 74.8%        │ 77.9%        │
│ Demographics_Doctor       │ 72.5%        │ 68.3%        │ 70.3%        │
│ Demographics_Name         │ 69.1%        │ 62.5%        │ 65.6%        │
│ Medication                │ 48.2%        │ 52.2%        │ 50.1%        │
│ Clinical_Condition        │ 41.6%        │ 50.9%        │ 45.8%        │
│ Investigation_Procedure   │ 38.9%        │ 44.1%        │ 41.3%        │
│ Clinical_Observation      │ 32.1%        │ 46.3%        │ 37.9%        │
│ Care_Activity             │ 28.6%        │ 29.9%        │ 29.2%        │
│ Plan_Goal                 │ 22.4%        │ 25.6%        │ 23.9%        │
└───────────────────────────┴──────────────┴──────────────┴──────────────┘
```

**Interpretation**:
- Demographics classes (Age, Gender, Bed, Doctor, Name) have high regularities and yield strong span F1 ($65\% - 90\%$).
- Complex clinical concepts (`Clinical_Observation`, `Care_Activity`, `Plan_Goal`) exhibit multi-word boundary ambiguity and lower lexical redundancy, producing strict F1 between $23\%$ and $38\%$.

---

## 6. Bio_ClinicalBERT Fine-Tuning Feasibility (Task 5)

An architectural audit of [scripts/train_and_evaluate_clinicalbert.py](file:///c:/Users/akg50/Desktop/prototype/scripts/train_and_evaluate_clinicalbert.py) and the local checkpoint [backend/models/clinical_bert/](file:///c:/Users/akg50/Desktop/prototype/backend/models/clinical_bert/) revealed the following:

### 6.1 Token-to-Character Alignment Risks
- **Subword Fragmentation**: Clinical text uses non-standard terms, dosages (`10mg`), and abbreviations (`post-op`, `q.d.s.`), which `BertTokenizerFast` fragments into multiple subword tokens (e.g., `post`, `##-`, `##op`).
- **Label Propagation**: When token classification heads predict labels per subword token, reconstructing character offsets requires mapping predictions back to character slices via `offset_mapping`. Any misalignment results in a strict span boundary mismatch.
- **Outside Label Dominance**: In the 101 notes, $> 75\%$ of subword tokens are labeled `"O"`, causing cross-entropy training to collapse to the majority class unless focal loss or boundary weighting is applied.

### 6.2 Hardware and Compute Constraints
- **Hardware Profile**: Windows 11 host with **CPU-only PyTorch** (`torch.cuda.is_available() == False`).
- **Model Size**: 110 million parameters (430 MB).
- **Execution Cost**: Full 5-fold cross-validation with 3 epochs per fold requires ~1.5 to 2 hours of high-utilization CPU execution.
- **Historical Empirical Reality**: In the audited baseline results ([data/gold_standard/benchmark_validation_audit_results.json](file:///c:/Users/akg50/Desktop/prototype/data/gold_standard/benchmark_validation_audit_results.json)), Bio_ClinicalBERT trained on 80 documents achieved:
  - **Strict F1**: **11.38%**
  - **Lenient F1**: **24.52%**
  - **Inference Latency**: **86.4 ms / document** (vs **0.3 ms** for Logistic Regression).
- **Sample Inadequacy**: Fine-tuning 110M parameters on 60 training documents leads to severe overfitting and parameter stagnation. Transformer fine-tuning requires at least 500–1,000 diverse annotated clinical documents to generalize effectively.

### 6.3 Feasibility Decision on ClinicalBERT
- **Verdict**: **DEFER TRANSFORMER FINE-TUNING**.
- **Rationale**: Re-fine-tuning Bio_ClinicalBERT immediately on the 101 synthetic notes on CPU will consume substantial compute without scientific benefit, reiterating the 11.38% strict F1 limitation caused by sample scarcity. Transformer fine-tuning should be scheduled after collecting the planned 250-note corpus and when CUDA acceleration is available.

---

## 7. Audit Deliverables and Test Suite Integrity (Task 6)

1. **Readiness Report**: This document ([docs/benchmark/model_training_readiness.md](file:///c:/Users/akg50/Desktop/prototype/docs/benchmark/model_training_readiness.md)).
2. **Reproducible Script**: [scripts/train_statistical_classifier.py](file:///c:/Users/akg50/Desktop/prototype/scripts/train_statistical_classifier.py) supporting configurable parameter grids, nested cross-validation, leak-free feature vectorization, and structured JSON results output.
3. **Comprehensive Test Suite**: [tests/test_statistical_model_training.py](file:///c:/Users/akg50/Desktop/prototype/tests/test_statistical_model_training.py) comprising 8 unit and integration tests:
   - `test_corpus_structure_and_completeness`: Validates 101 documents and non-empty entity schemas.
   - `test_split_disjointness_across_all_folds`: Enforces zero document ID intersection across train, val, and test splits.
   - `test_feature_extraction_consistency`: Confirms feature extraction produces valid dictionary representations without gold label leakage.
   - `test_leak_free_vectorizer_fitting`: Proves vectorizer fitted on training data handles novel test tokens gracefully without leakage.
   - `test_span_reconstruction_logic`: Verifies contiguous token merging into exact character offsets.
   - `test_strict_and_lenient_f1_calculation`: Validates metric scoring edge cases (perfect, disjoint, partial overlap).
   - `test_historical_baseline_immutability`: Asserts that `baseline_evaluation_results.json` and `benchmark_validation_audit_results.json` remain bit-for-bit unchanged.
   - `test_tuning_results_file_integrity`: Verifies presence and schema of `statistical_classifier_tuning_results.json`.

---

## 8. Final Decision and Roadmap

### Formal Readiness Verdict:
# **`READY FOR BASELINE TRAINING`**

The repository is fully ready for baseline statistical model training and hyperparameter tuning on entity extraction using the 101-note corpus and document-level nested cross-validation.

### Detailed Status by Objective:

| Training Objective | Target Architecture | Readiness Status | Blockers & Requirements |
|---|---|:---:|---|
| **Entity Span Extraction** | Statistical Logistic Regression | **READY** | None. Fully verified, reproducible, and tested (Strict F1: 51.69%). |
| **Entity Span Extraction** | Bio_ClinicalBERT | **DEFERRED** | High CPU latency and small sample size (101 notes). Awaiting GPU and expanded corpus. |
| **Assertion Classification** | Supervised Classifier | **NOT READY** | **Annotation Gap**: 0 gold assertion annotations in the 101 corpus. |
| **Temporality Classification** | Supervised Classifier | **NOT READY** | **Annotation Gap**: 0 gold temporality annotations in the 101 corpus. |
| **Medication Relation Binding**| Supervised Relation Linker | **NOT READY** | **Annotation Gap**: 0 gold attribute link annotations in the 101 corpus. |

### Exact Blockers:
1. **Annotation Gap for Contextual Modules**:
   - The 101-note corpus does not contain assertion status, temporality status, or medication relation links. Assertion and temporality currently rely on validated heuristic engines. To train supervised classifiers for these tasks, gold-standard labels must be annotated.
2. **Compute Bottleneck for Deep Learning**:
   - CPU-only execution prevents efficient experimentation with transformer architectures.
3. **Independent Generalization Data**:
   - The historical 101-note corpus was used during iterative development. An independent held-out evaluation requires executing the collection of the planned 250-note benchmark designed in Step 4.2.

### Next Recommended Implementation Step:
Implement the **CRF (Conditional Random Field) sequence tagger** using `sklearn-crfsuite` as the next statistical baseline model. CRFs model transitions between adjacent labels (e.g., $P(y_t \mid y_{t-1})$), which directly addresses the span boundary fragmentation currently limiting the independent token-level Logistic Regression classifier.
