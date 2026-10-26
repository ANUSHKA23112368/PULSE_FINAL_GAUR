# PULSE — Clinical Attribute Accuracy & Structured Handover Evaluation Report
**Document Path**: [docs/benchmark/clinical_attribute_evaluation.md](file:///c:/Users/akg50/Desktop/prototype/docs/benchmark/clinical_attribute_evaluation.md)  
**Date**: October 2026  
**System**: PULSE (Patient Update & Log Structuring Engine)  
**Status**: Step 5.7 Attribute Accuracy & Structured Handover Evaluation  

---

## 1. Executive Summary

PULSE Step 5.7 evaluated the correctness of structured clinical information extraction, attribute binding, assertion classification, investigation status semantics, and conditional instruction parsing.

The audit strictly separated:
1. **Genuinely Evaluable Historical Features**: Entity mentions and character offset validity measured on the 101-note historical corpus.
2. **Features Marked `NOT EVALUABLE`**: Relational links (medication-to-dose/route/frequency), PRN indications, investigation statuses, assertion, and temporality, which lack gold link annotations in the historical 101-note NICTA corpus.
3. **Deterministic Schema Regression Testing**: Controlled unit and schema fixture tests (7 synthetic notes) verifying attribute binding algorithms and edge-case safety without presenting them as clinical generalization evidence.

### Key Audit Findings
1. **Source-Offset Validity**: **100.0%** across all 2,103 annotated spans in the historical 101-note corpus. Every extracted entity strictly grounds to its verbatim text slice.
2. **Defect Identified & Resolved in Medication Deduplication**:
   - *Previous Defect*: In `HybridClinicalEntityExtractor._extract_medications`, the deduplication key was `(norm, ctx["assertion"], ctx["temporality"])`. Multiple distinct medications sharing the same broad pharmacological class (e.g., Warfarin and Heparin both categorized as `"Anticoagulant / Antiplatelet"`) collided on this key, causing the second drug to be silently dropped and merged into the first.
   - *Fix Implemented*: Updated `dedup_key` to `(matched_med.lower(), ctx["assertion"], ctx["temporality"])`. Now, repeated mentions of the *same* drug are deduplicated, while distinct drugs are preserved with their respective dosages and routes.
3. **PRN Indication Extraction Added**:
   - In previous iterations, PRN was matched only as a frequency token (`PRN`), and PRN indications (e.g., `"PRN for headache"`, `"PRN for nausea"`) were dropped.
   - Regex-guided clause extraction was added to bind `prn_indication` directly into medication attributes while ensuring the symptom is never mistaken for a medication name.
4. **Conditional Instruction Parsing Added**:
   - Previously, conditional clinical directives such as `"If BP < 90, inform MO"` or `"Hold Metoprolol if SBP < 100"` were captured only as unclassified narrative clauses.
   - Implemented [`extract_conditional_instructions`](file:///c:/Users/akg50/Desktop/prototype/backend/extraction/structured_generator.py#L221-L269) in `StructuredHandoverGenerator`, which explicitly separates trigger conditions (`"BP < 90"`, `"SBP < 100"`) from resulting clinical actions (`"inform MO"`, `"Hold Metoprolol"`).
5. **Three-Tier Evaluation Discipline**:
   - All 7 relational attribute tasks are formally documented as **`NOT EVALUABLE`** on the historical 101-note dataset to eliminate unscientific metric fabrication.

---

## 2. Output Schema and Extraction Architecture Audit (Task 1)

### 2.1 The End-to-End Extraction Pipeline

```
Unstructured Clinical Handover Note
        │
        ├──► Protected Sentence Splitter (clinical_context_extractor.split_sentences_protected)
        │    - Preserves abbreviations (Dr., temp., min., etc.) and decimal dosages (12.5 mg)
        │
        ├──► Entity Extractor (HybridClinicalEntityExtractor / CategoryWiseHybridExtractor)
        │    - Demographics: Bed, Name, Age, Gender, Consultant
        │    - Conditions & Symptoms: Lexicon matching + context window
        │    - Medications: Pharmaceutical regexes + localized clause parser
        │    - Investigations: Diagnostic regexes + status parser
        │    - Treatments: Nursing care activities
        │
        ├──► Context & Assertion Engine (clinical_context_extractor.analyze_assertion)
        │    - Assertion: Affirmative / Positive, Negated, Possible / Uncertain
        │    - Temporality: Current, Historical, Planned
        │
        ├──► Shorthand & Hinglish Normalizer
        │    - Indian clinical abbreviations & Roman-Hindi symptom mapping
        │
        ├──► Open-Vocabulary Candidate Extractor
        │    - Unclassified narrative preservation with flagged_for_review status
        │
        └──► Structured Handover Generator (StructuredHandoverGenerator)
             - 9-Category Handover
             - ISBAR Structure
             - Executive Shift Summary
             - Pending Continuity Tasks
             - Conditional Directives (Trigger vs Action)
             - Follow-Up Plan
```

### 2.2 Output Schema Representation

| Clinical Concept | Internal Representation | Schema Field Names | Missing Value Handling |
|---|---|---|---|
| **Medication Name** | `source_text`, `normalized_concept` | `entity["text"]`, `entity["normalized"]` | Mandatory |
| **Medication Dose** | Bound string in attributes | `attributes["dosage"]` | `"Unspecified dose in text"` (Legacy) / `null` (Contract) |
| **Medication Route** | Bound uppercase string | `attributes["route"]` (e.g. `PO`, `IV`, `SUBCUT`) | `"Unspecified route"` / `null` |
| **Medication Frequency** | Bound canonical string | `attributes["frequency"]` (e.g. `BD`, `TDS`, `DAILY`) | `"Unspecified frequency"` / `null` |
| **PRN Indication** | Bound symptom/trigger string | `attributes["prn_indication"]` | `None` / `null` |
| **Investigation Name** | `source_text`, `normalized_concept` | `entity["text"]`, `entity["normalized"]` | Mandatory |
| **Investigation Status** | Progress state enum | `attributes["status"]` (`Completed`, `Sent`, `Pending`, etc.) | `"Unspecified"` |
| **Assertion** | Context classification | `attributes["assertion"]` (`Positive`, `Negated`, `Possible`) | Defaults to `Positive` |
| **Temporality** | Temporal classification | `attributes["temporality"]` (`Current`, `Historical`, `Planned`) | Defaults to `Current` |
| **Care Activities** | `source_text`, normalized type | `entity["text"]`, `entity["category"] = "Treatment"` | Mandatory |
| **Pending Tasks** | Task dictionary | `task["task"]`, `task["type"]`, `task["priority"]`, `task["status"]` | Defaults to `"Unassigned"` |
| **Conditional Directives** | Structured instruction | `instruction["trigger_condition"]`, `instruction["resulting_action"]` | Separated |
| **Evidence Spans** | Exact character offsets | `start_char`, `end_char`, `evidence_text` | Mandatory |
| **Unknown Terms** | Open-vocabulary candidate | `review_status: "flagged_for_review"`, `unclassified_narrative: true` | Flags clinical review |

---

## 3. Attribute-Level Evaluation & Annotation Availability Matrix (Task 2)

The table below documents the evaluation status of all 12 target clinical capabilities across data sources:

| # | Clinical Extraction Capability | Historical 101-Note Corpus Status | 7 Schema Fixtures Status | Planned 250-Note Benchmark |
|:---:|---|:---:|:---:|:---:|
| **1** | **Medication Mention Extraction** | **EVALUATED** (Strict F1: 27.86%, Lenient: 56.72%) | Evaluated (Regression) | Full Benchmark |
| **2** | **Medication-to-Dose Binding** | **NOT EVALUABLE** (0 gold relational links) | Evaluated (100% F1) | Full Relational Annotation |
| **3** | **Medication-to-Route Binding** | **NOT EVALUABLE** (0 gold relational links) | Evaluated (80.0% F1) | Full Relational Annotation |
| **4** | **Medication-to-Frequency Binding** | **NOT EVALUABLE** (0 gold relational links) | Evaluated (100% F1) | Full Relational Annotation |
| **5** | **PRN Indication Binding** | **NOT EVALUABLE** (0 gold PRN links) | Evaluated (Regression) | Full Relational Annotation |
| **6** | **Investigation Mention Extraction** | **EVALUATED** (Strict F1: 6.86%, Lenient: 28.43%) | Evaluated (Regression) | Full Benchmark |
| **7** | **Investigation Status Classification** | **NOT EVALUABLE** (0 gold linked status tags) | Evaluated (Regression) | Full Status Annotation |
| **8** | **Assertion Classification** | **NOT EVALUABLE** (0 gold assertion labels) | Evaluated (Regression) | Full ConText Annotation |
| **9** | **Temporality Classification** | **NOT EVALUABLE** (0 gold temporality labels) | Evaluated (Regression) | Full Temporal Annotation |
| **10** | **Pending-Task Extraction** | **NOT EVALUABLE** (0 gold task labels) | Evaluated (Regression) | Full Task Annotation |
| **11** | **Conditional Trigger/Action Separation** | **NOT EVALUABLE** (0 gold conditional labels) | Evaluated (Regression) | Full Conditional Annotation |
| **12** | **Evidence Grounding & Offset Validity** | **EVALUATED** (**100.0% Valid Offsets**) | Evaluated (100% Valid) | Full Offset Validation |

### Why pseudo-metrics are rejected:
In the historical 101-note NICTA corpus, entity mentions (e.g. `"Digoxin"` and `"125mcg"`) were annotated as standalone unlinked spans. The dataset contains **zero relationship pointers** indicating which dosage belongs to which medication. Evaluating attribute binding on this corpus would require hallucinating gold links. Marking these tasks **`NOT EVALUABLE`** preserves scientific integrity.

---

## 4. Controlled Medication Binding Error Analysis (Task 3)

Six controlled clinical scenarios were tested to evaluate binding integrity and boundary isolation:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 CONTROLLED MEDICATION BINDING AUDIT RESULTS                 │
├─────────┬───────────────────────────────────────────┬────────────┬──────────┤
│ Test ID │ Clinical Scenario Tested                  │ Status     │ Outcome  │
├─────────┼───────────────────────────────────────────┼────────────┼──────────┤
│ TC_M_01 │ Multi-Drug Sentence Attribute Separation  │ PASSED     │ No leak  │
│ TC_M_02 │ Distinct Drug Deduplication (Warfarin/Hep)│ PASSED     │ Both kept│
│ TC_M_03 │ Missing Attribute Preservation            │ PASSED     │ Null kept│
│ TC_M_04 │ PRN Indication Binding (headache)         │ PASSED     │ Bound    │
│ TC_M_05 │ Negated Medication Exclusion (Aspirin)    │ PASSED     │ Negated  │
│ TC_M_06 │ Historical Temporality (Prior Digoxin)    │ PASSED     │ Histor.  │
└─────────┴───────────────────────────────────────────┴────────────┴──────────┘
```

1. **Multi-Drug Clause Separation**:
   - Input: `"Prescribed Tab Furosemide 40 mg PO daily and Metoprolol 12.5 mg BD."`
   - *Furosemide* binds: `dosage = "40 mg"`, `route = "PO"`, `frequency = "DAILY"`.
   - *Metoprolol* binds: `dosage = "12.5 mg"`, `frequency = "BD"`, `route = "Unspecified route"`.
   - **Finding**: Route `"PO"` was not leaked to Metoprolol. Clause-break regex (`and`, `;`, `,`) isolates medication scopes.
2. **Distinct Drug Preservation in Shared Pharmacological Classes**:
   - Input: `"Ceased Warfarin; commenced Heparin 5000 units subcut."`
   - Both Warfarin and Heparin belong to the class `"Anticoagulant / Antiplatelet"`.
   - **Finding**: Both drugs are extracted as separate entities. Heparin retains `5000 units SUBCUT` while Warfarin retains `Unspecified dose in text`.
3. **PRN Indication Separation**:
   - Input: `"Paracetamol 1g PO QID PRN for headache."`
   - **Finding**: `prn_indication` is bound as `"headache"`, and `"headache"` is not misclassified as a drug entity.
4. **Negated Medication Handling**:
   - Input: `"Patient denies taking any Aspirin or blood thinners."`
   - **Finding**: Aspirin is extracted with `assertion = "Negated"` and `is_negated = True`.
5. **Historical Medication Handling**:
   - Input: `"Prior history of Digoxin 125mcg daily, ceased last year."`
   - **Finding**: Digoxin is extracted with `temporality = "Historical"`.

---

## 5. Investigation and Task Semantics Audit (Task 4)

### 5.1 Investigation Status Semantics
The investigation status parser in `backend/extraction/entity_extractor.py` was evaluated across clinical progress states:

| Source Context | Extractor Status | Benchmark Schema Target | Analysis |
|---|---|---|---|
| `"Chest X-Ray is completed"` | `Completed` | `Completed` | Correct |
| `"Blood cultures sent off to lab"` | `Sent` | `Sent` | Correct |
| `"Renal biopsy is pending"` | `Pending` | `Pending` | Correct |
| `"Awaiting urine microscopy results"`| `Awaiting Results` | `Awaiting Results` | Correct |
| `"Renal ultrasound ordered"` | `Pending` | `Ordered` | **Gap**: `Ordered` is conflated with `Pending`. |
| `"No CT scan performed"` | `Not Ordered / Denied` | `Unknown` + Negated | Handled with `is_negated: True`. |
| `"CXR done yesterday"` | `Completed` | `Completed` | Correct |
| `"ECG"` (no context) | `Unspecified` | `Unknown` | Minor enum label difference. |

### 5.2 Conditional Instructions Audit
* **Input Evaluated**: `"If BP < 90, inform MO. Hold Metoprolol if SBP < 100."`
* **Parser Evaluated**: [`extract_conditional_instructions`](file:///c:/Users/akg50/Desktop/prototype/backend/extraction/structured_generator.py#L221-L269)
* **Output Produced**:
  ```json
  [
    {
      "trigger_condition": "BP < 90",
      "resulting_action": "inform MO",
      "instruction_type": "Conditional Order / Threshold Directive"
    },
    {
      "trigger_condition": "SBP < 100",
      "resulting_action": "Hold Metoprolol",
      "instruction_type": "Conditional Order / Threshold Directive"
    }
  ]
  ```
* **Finding**: Trigger conditions and resulting clinical actions are now **explicitly separated and structured**, preventing conditional directives from being obscured as generic narrative text.

---

## 6. Evaluation Harness and Three-Tier Results Breakdown (Task 5)

The evaluation harness was executed via [scripts/evaluate_clinical_attributes.py](file:///c:/Users/akg50/Desktop/prototype/scripts/evaluate_clinical_attributes.py) and serialized to [data/gold_standard/clinical_attribute_evaluation_results.json](file:///c:/Users/akg50/Desktop/prototype/data/gold_standard/clinical_attribute_evaluation_results.json).

### Tier A: Historical 101-Note Corpus Results
* **Total Documents**: 101 (8,487 tokens, 2,103 annotated spans).
* **Source-Offset Validity**: **100.0%** (2,103/2,103 exact character matches).
* **Medication Mentions**:
  - Strict F1: **27.86%** (P: 41.79%, R: 20.90%, TP: 28, FP: 39, FN: 106)
  - Lenient F1: **56.72%** (P: 85.07%, R: 42.54%, TP: 57, FP: 10, FN: 77)
* **Investigation Mentions**:
  - Strict F1: **6.86%** (P: 11.48%, R: 4.90%, TP: 7, FP: 54, FN: 136)
  - Lenient F1: **28.43%** (P: 47.54%, R: 20.28%, TP: 29, FP: 32, FN: 114)
* **Relational Attributes**: Formally documented as **NOT EVALUABLE**.

### Tier B: Synthetic Schema Regression Test Results (7 Notes)
*(Technical Verification Only — Not General Clinical Evidence)*
* **Dose-Binding F1**: **100.0%** (TP: 6, FP: 0, FN: 0)
* **Route-Binding F1**: **80.0%** (TP: 4, FP: 1, FN: 1)
* **Frequency-Binding F1**: **100.0%** (TP: 6, FP: 0, FN: 0)
* **PRN Indication Binding**: Verified on synthetic fixtures.
* **Source-Offset Validity**: **100.0%** across all 54 fixture entities.

### Tier C: Not-Yet-Evaluable Capabilities
Capabilities awaiting the independent 250-note benchmark:
- Supervised clinical relation extraction (Medication $\to$ Dose/Route/Frequency/PRN).
- Supervised investigation status classification.
- Supervised ConText assertion classification.
- Supervised temporal event sequencing.

---

## 7. Testing, Safety, and Repository Integrity (Task 6)

A dedicated test suite was implemented in [tests/test_clinical_attribute_evaluation.py](file:///c:/Users/akg50/Desktop/prototype/tests/test_clinical_attribute_evaluation.py):
1. `test_01_cross_medication_attribute_contamination`: Verifies clause boundary isolation between Furosemide and Metoprolol.
2. `test_02_distinct_drugs_sharing_pharmacological_class`: Verifies Warfarin and Heparin are both extracted.
3. `test_03_missing_attribute_preservation`: Asserts unmentioned dosages remain unspecified.
4. `test_04_prn_indication_binding`: Asserts PRN indication is bound and not confused for a medication.
5. `test_05_investigation_status_distinctions`: Asserts Completed, Sent, and Pending statuses.
6. `test_06_negation_and_temporality_preservation`: Asserts negated chest pain and historical asthma.
7. `test_07_conditional_trigger_and_action_separation`: Asserts trigger and action separation.
8. `test_08_evidence_offset_integrity`: Asserts exact string slicing across all entities.
9. `test_09_structured_summary_fidelity`: Asserts that executive summary excludes negated chest pain from active reason.
10. `test_10_attribute_results_artifact_schema`: Validates schema of `clinical_attribute_evaluation_results.json`.

### Full Test Suite Execution Results
- `python -m unittest tests/test_clinical_attribute_evaluation.py` $\to$ **10/10 PASS** in **0.090s**.
- Full test suite: **201/201 tests PASS** across all modules in **12.8s** with 0 regressions.

---

## 8. Summary & Next Steps

1. **Features Genuinely Evaluated**: Source-offset grounding (100%), medication mention extraction (56.7% lenient F1), investigation mention extraction (28.4% lenient F1), and controlled attribute binding tests.
2. **Features Formally NOT EVALUABLE**: All 7 relational and contextual attribute tasks on the historical 101-note corpus due to absence of gold link annotations.
3. **Defects Fixed**:
   - Distinct drug deduplication collision bug resolved.
   - PRN indication extraction implemented.
   - Conditional trigger/action separation implemented.
   - Source text trimming offset synchronization corrected.
4. **Recommended Next Step**:
   - Proceed with annotation and collection of the planned **250-note independent clinical benchmark** designed in Step 4.2 to obtain the ground truth relation links necessary for general clinical attribute validation.
