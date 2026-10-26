# PULSE — Independent Benchmark Annotation Protocol & Data Governance Manual
**Document Path**: [docs/benchmark/independent_benchmark_annotation_protocol.md](file:///c:/Users/akg50/Desktop/prototype/docs/benchmark/independent_benchmark_annotation_protocol.md)  
**Version**: 1.0.0 (Phase 5, Step 6.0)  
**Status**: Ready for Independent Clinical Data Collection & Protocol Review  
**Classification**: Research Specification & Data Governance Standard  

---

## 1. Intended Use and Evaluation Objectives

### 1.1 Project Mission
The **Patient Update & Log Structuring Engine (PULSE)** is a clinical handover intelligence research prototype designed to convert unstructured, heterogeneous clinical handover notes into structured, source-grounded clinical summaries. The system aims to assist incoming healthcare professionals during shift changes by organizing critical patient information according to clinical standards (e.g., ISBAR: Identification, Situation, Background, Assessment, Recommendation) while rigorously preserving verbatim source evidence, uncertainty, temporality, investigation tracking, and medication safety relationships.

### 1.2 Evaluation Objectives
The objective of this Independent Benchmark Annotation Protocol is to establish an uncompromised, gold-standard clinical evaluation framework for PULSE. Previous evaluations relied on a historical development corpus of 101 notes (derived from Australian nursing handovers) and 7 synthetic schema fixtures. The historical corpus:
- Has already guided feature engineering, lexicon tuning, and model selection.
- Completely lacks relational ground truth linking medications to dosages, routes, or frequencies.
- Contains zero reference annotations for assertion, temporality, investigation workflow statuses, or conditional clinical directives.

The independent benchmark will provide the first **fully relational, multi-specialty, clinically validated test bed** specifically representative of acute and subacute clinical documentation in Indian hospital settings, including Indian clinical shorthand and Roman-Hindi (Hinglish) clinical expressions.

> **CRITICAL DIRECTIVE ON EVALUATION INTEGRITY:**  
> This protocol specifies the design, governance, and validation standards for an independent 250-note benchmark. As of Phase 5, Step 6.0, the benchmark exists as an **approved protocol and validation architecture**. Real clinical patient records have **not** been collected, accessed, or annotated. Zero institutional approvals or clinical annotators are fabricated.

---

## 2. Inclusion and Exclusion Criteria

The benchmark targets 250 diverse clinical handover communications across 6 core clinical disciplines. Notes must reflect genuine handover workflow conditions rather than sanitized textbook summaries.

### 2.1 Discipline Distribution Matrix
| Specialty Department | Target Note Count | Proportion | Documentation Focus |
|---|:---:|:---:|---|
| **1. General Medicine** | 50 Notes | 20.0% | Multimorbidity (T2DM, HTN, CKD), polypharmacy, glycemic monitoring, altered sensorium. |
| **2. Surgery & Orthopedics** | 45 Notes | 18.0% | Post-operative days (POD), wound status, drain outputs, NPO status, multimodal analgesia. |
| **3. Pediatrics & NICU** | 40 Notes | 16.0% | Weight-based decimal dosing (mg/kg), gestational age, phototherapy, developmental milestones. |
| **4. Obstetrics & Gynecology** | 35 Notes | 14.0% | Obstetric index (G/P/L/A), fetal heart sounds, contractions, postpartum hemorrhage checks. |
| **5. Emergency Medicine** | 40 Notes | 16.0% | High-density shorthand, rapid triage vitals, acute trauma, pending toxicology and imaging. |
| **6. Critical Care (ICU / HDU)** | 40 Notes | 16.0% | Invasive ventilation (FiO2, PEEP), vasoactive titrations, arterial blood gas, Glasgow Coma Scale. |
| **TOTAL BENCHMARK** | **250 Notes** | **100.0%** | **Documented in formal manifest with cryptographic verification** |

### 2.2 Inclusion Criteria
A clinical handover note is eligible for inclusion in the benchmark if and only if it satisfies all of the following conditions:
1. **Clinical Shift Communication:** Represents an authentic written or transcribed spoken clinical handover note between medical officers, residents, fellows, or nursing staff.
2. **Substantive Clinical Content:** Contains at least one clinical condition or observation, plus at least one medication, investigation, or planned action.
3. **Length Bounds:** Has a minimum character length of 80 characters and a maximum character length of 3,500 characters (excluding metadata headers).
4. **Natural Linguistic Variety:** Reflects standard Indian hospital documentation practices, including English clinical narrative, Indian clinical shorthand (e.g., `K/C/O`, `C/O`, `S/B`, `RBS`, `POD`), or Roman-Hindi expressions (e.g., *"chakkar"*, *"chhati me dard"*).
5. **Full Consent & Governance:** Sourced exclusively under approved institutional ethics committee (IEC) protocol or authorized de-identified data transfer agreement.

### 2.3 Exclusion Criteria
A note must be excluded if any of the following apply:
1. **Administrative Only:** Contains purely administrative, billing, insurance, or scheduling text devoid of clinical findings (e.g., *"Patient discharge clearance pending from TPA desk"*).
2. **Sanitized Synthetic Teaching Vignettes:** Text authored for medical student examinations or textbook questions that do not reflect actual ward handover habits.
3. **Extreme Truncation:** Unintelligible text fragments under 80 characters (e.g., *"Bed 4 stable"*).
4. **Irreversible Corruptions:** OCR or encoding artifacts exceeding 10% of total character count.
5. **Unconsented or Re-identifiable Records:** Any document containing unredacted Direct Personal Identifiers (DPId) that cannot be safely de-identified.

---

## 3. Note-Level De-Identification and Privacy Requirements

Patient confidentiality and data privacy are non-negotiable prerequisites. The benchmark must comply with:
- **Digital Personal Data Protection Act (DPDP 2023, India)**.
- **National Digital Health Mission (NDHM) / Ayushman Bharat Digital Mission (ABDM) Data Privacy Framework**.
- **HIPAA Safe Harbor De-identification Standard (45 CFR § 164.514(b)(2))**.

### 3.1 18-Category Identifier Removal Matrix
All notes ingested into the benchmark corpus must undergo rigorous primary de-identification and independent secondary audit prior to annotation:

| Identifier Category | De-Identification Rule | Replacement Protocol |
|---|---|---|
| **Names (Patient, Relative)** | Remove all direct names | Replace with standardized pseudonym (e.g., `[Patient Name 042]`) or realistic synthetic placeholder. |
| **Geographic Subdivisions** | Remove all addresses, streets, wards, pin codes | Retain only state or broad region if clinically relevant (e.g., endemic malaria zone). |
| **Dates** | Jitter all admission, event, and birth dates | Maintain internal temporal consistency by shifting all dates within a patient episode by an arbitrary uniform offset $\Delta \in [-30, +30]$ days. |
| **Telephone & Fax Numbers** | Complete redaction | Remove entirely. |
| **Email Addresses & Web URLs** | Complete redaction | Remove entirely. |
| **Hospital / UHID Numbers** | Complete redaction | Replace with synthetic token (e.g., `UHID-SYN-9081`). |
| **Health Plan / Insurance IDs** | Complete redaction | Remove entirely. |
| **Account & Billing Numbers** | Complete redaction | Remove entirely. |
| **Certificate / License Numbers**| Complete redaction | Remove entirely. |
| **Vehicle Identifiers / Plates** | Complete redaction | Remove entirely. |
| **Medical Device Serial Numbers**| Complete redaction | Remove entirely. |
| **Biometric Identifiers** | Complete redaction | Remove entirely. |
| **Full-Face Photographs** | Complete redaction | Excluded from corpus. |
| **Clinician Identifying Names** | Redact treating clinician surname | Replace with synthetic name (e.g., `Dr. Edwards`, `Dr. Sharma [Synthetic]`). |
| **Ages over 89 Years** | Aggregate ages $\ge 90$ | Replace with `"90+"` or categorize as elderly. |

### 3.2 Two-Stage Privacy Verification
1. **Automated Redaction Pass:** High-sensitivity regex and NER pass to flag prospective phone numbers, pin codes, UHIDs, and dates.
2. **Blinded Manual Privacy Review:** A privacy auditor reviews every de-identified note character-by-character. The note receives a `de_identification_verified: true` certificate in the dataset manifest only after explicit sign-off.

---

## 4. Entity-Span Annotation Rules

### 4.1 Coordinate Representation
- **0-Indexed Half-Open Offsets:** Every entity span must be documented as `[start_char, end_char)`.
- **Verbatim Slice Invariant:** `raw_text[start_char:end_char] == source_text`.
- **Whitespace Discipline:** Spans must never start or end with whitespace. Punctuation terminating a sentence must not be included unless it is an intrinsic part of an acronym (e.g., `"K/C/O"` is valid, `"HTN."` is invalid; annotate `"HTN"`).

### 4.2 Harmonized Clinical Macro-Categories
Every annotated entity must be classified into one of 12 approved clinical macro-categories:

```
+--------------------------------------------------------------------------------------------------+
|                                12 HARMONIZED CLINICAL MACRO-CATEGORIES                           |
+--------------------------+--------------------------+--------------------------------------------+
| Category                 | Description              | Canonical Inclusion Examples               |
+--------------------------+--------------------------+--------------------------------------------+
| 1. Demographics_Bed      | Bed or physical room loc | Bed 4, Bed 12B, ICU Bed 2, Room 401        |
| 2. Demographics_Name     | Patient name (de-ident)  | Arthur Pendelton, Rajesh Sharma            |
| 3. Demographics_Age      | Chronological age        | 68 years, 4 months, 72 yo                  |
| 4. Demographics_Gender   | Gender or biological sex | Male, Female, M, F                         |
| 5. Demographics_Doctor   | Attending / consultant   | Dr Edwards, Dr Sharma, On-call Registrar   |
| 6. Clinical_Condition    | Formal pathology/disease | T2DM, HTN, acute appendicitis, NSTEMI      |
| 7. Clinical_Observation  | Sign, symptom, finding   | shortness of breath, pedal edema, GCS 15   |
| 8. Medication            | Drug or medicinal fluid  | Furosemide, Metoprolol, RL, Ceftriaxone    |
| 9. Investigation_Procedure| Diagnostic test/imaging  | Chest X-Ray, Blood culture, CT Head, ECG   |
| 10. Care_Activity        | Nursing/clinical therapy | Foley catheterization, dressing change     |
| 11. Plan_Goal            | Handover goal / directive| Fluid restriction 1L, mobilize shift 2     |
| 12. Unclassified         | Unknown term / candidate | Novel acronym, unclear shorthand           |
+--------------------------+--------------------------+--------------------------------------------+
```

### 4.3 Boundary Rules for Compound and Nested Entities
1. **Compound Diagnostic Terms:** When a diagnosis includes anatomical location or severity, annotate the entire unified diagnostic phrase as `Clinical_Condition` (e.g., annotate `"left lower lobe pneumonia"`, not `"left lower lobe"` + `"pneumonia"`).
2. **Modifier vs Root Entity:** When a symptom modifies a diagnosis (e.g., *"severe chest pain due to unstable angina"*), annotate `"chest pain"` as `Clinical_Observation` and `"unstable angina"` as `Clinical_Condition`.

---

## 5. Medication Attribute Binding Specification

Medication safety is the highest clinical risk area in clinical handover. The benchmark implements a fully relational graph linking each `Medication` parent entity to its directed attributes.

### 5.1 Directed Relational Model
Each `Medication` entity serves as a source node with directed edges to dependent attribute spans:
```
[Medication: Metoprolol] (ID: ent_med_01)
       │
       ├── has_dose ────────► [12.5 mg] (start: 154, end: 161)
       ├── has_route ───────► [PO]      (start: 162, end: 164)
       ├── has_frequency ───► [BD]      (start: 165, end: 167)
       └── has_prn_indication► [null]
```

### 5.2 Attribute Definitions & Edge Constraints
1. **`dosage`:** Verbatim quantity and unit of measure (e.g., `"40 mg"`, `"1 g"`, `"0.25 mg"`, `"15 mg/kg"`).
   - *Decimal Preservation Rule:* Never alter or strip leading zeros (e.g., `"0.25 mg"` must not be parsed as `"25 mg"`).
2. **`route`:** Administration path (e.g., `"PO"`, `"IV"`, `"IM"`, `"SC"`, `"Inhalation"`, `"PR"`, `"SL"`).
3. **`frequency`:** Administration frequency or timing schedule (e.g., `"OD"`, `"BD"`, `"TDS"`, `"QID"`, `"Q6H"`, `"PRN"`, `"SOS"`, `"stat"`, `"mane"`, `"nocte"`).
4. **`prn_indication`:** The clinical justification or conditional trigger for PRN/SOS medication administration (e.g., `"for severe headache"`, `"if temp > 38.5C"`, `"for nausea"`).

### 5.3 Shared and Compound Orders
- **Shared Administration:** When an order states *"IV fluids and Ceftriaxone"*, the route `"IV"` must be linked to both `"fluids"` and `"Ceftriaxone"` via separate relational edges.
- **Null Preservation:** If an attribute is not explicitly documented in the note (e.g., *"Prescribed Metoprolol BD"*), the `dosage` attribute edge must remain `null`. Annotators are **strictly prohibited from imputing standard adult doses**.

---

## 6. Clinical Assertion and Temporality Labels

Every `Clinical_Condition`, `Clinical_Observation`, and `Medication` entity must be tagged with explicit assertion and temporality attributes.

### 6.1 Assertion Enum
| Assertion Value | Clinical Meaning | Linguistic Trigger Examples |
|---|---|---|
| **`Positive`** (Affirmed) | Finding is affirmed to be present in the patient. | *"Patient has fever"*, *"K/C/O HTN"*, *"bilateral crepitations present"*. |
| **`Negated`** (Absent/Denied) | Finding is explicitly denied, ruled out, or absent. | *"No chest pain"*, *"denies dyspnea"*, *"no history of diabetes"*, *"bukhar nahi hai"*. |
| **`Possible`** (Uncertain) | Finding is suspected, differential, or unconfirmed. | *"Suspected dengue"*, *"differential includes PE"*, *"r/o appendicitis"*, *"shayad infection hai"*. |

#### Negation Scope Boundary Rule:
Negation applies across coordinate clauses up to the first contrasting conjunction:
- *"No fever, cough, or dyspnea, but reports mild headache"* $\implies$ fever, cough, dyspnea are `Negated`; headache is `Positive`.

### 6.2 Temporality Enum
| Temporality Value | Clinical Meaning | Linguistic Trigger Examples |
|---|---|---|
| **`Current`** | Pertains to the current shift, presenting episode, or active condition. | *"Currently febrile"*, *"complains of acute abdomen"*, *"BP 130/80 on admission"*. |
| **`Historical`** | Pre-existing medical history, past surgical history, remote resolved event. | *"Known diabetic for 10 years"*, *"H/O appendectomy in 2018"*, *"childhood asthma"*. |
| **`Planned`** | Scheduled future intervention, anticipated procedure, conditional action. | *"Scheduled for ultrasound tomorrow morning"*, *"plan for discharge next shift"*. |

---

## 7. Investigation Workflow Status Semantics

Clinical investigations undergo a strict operational lifecycle. A clinical handover engine must never represent an uncompleted investigation as completed. Every `Investigation_Procedure` entity must be assigned exactly one workflow status:

| Status Enum | Operational State | Verbatim Trigger Examples |
|---|---|---|
| **`Ordered`** | Investigation prescribed/requested; specimen not yet collected. | *"Advised CT brain"*, *"requisition placed for USG"*, *"order repeat CBC"*. |
| **`Sent`** | Biological specimen collected and dispatched to laboratory/imaging. | *"Blood cultures sent to microbiology"*, *"CSF sent for cytology"*. |
| **`Awaiting Results`**| Test conducted or specimen in processing; report awaited. | *"Awaiting troponin result"*, *"potassium report awaited"*, *"echo report pending"*. |
| **`Completed`** | Result is available and documented in the chart/handover. | *"Chest X-Ray completed: clear"*, *"CT abdomen shows acute appendicitis"*. |
| **`Not Ordered`** | Investigation considered but explicitly withheld, cancelled, or contraindicated. | *"MRI cancelled due to pacemaker"*, *"troponin not indicated"*. |
| **`Unspecified`** | Investigation mentioned without workflow status evidence. | *"Patient has a CT scan"* (status ambiguous). |

---

## 8. Pending Tasks and Conditional Directives

Clinical handovers convey critical forward-looking instructions to the oncoming team.

### 8.1 Contingent / Conditional Directives
When a handover contains conditional instructions (e.g., *"If SBP < 90 mmHg, inform MO on call and hold Metoprolol"*), annotators must capture both elements as a linked tuple:
- **`trigger_condition`:** The physiological or clinical boundary triggering action (e.g., `"SBP < 90 mmHg"`).
- **`resulting_action`:** The clinical intervention required (e.g., `"inform MO on call and hold Metoprolol"`).
- **`source_span`:** The full contiguous sentence ground truth.

### 8.2 Structured Continuity Tasks
Tasks must be categorized by task type and clinical urgency:
- **Task Type:** `Investigation_Followup`, `Medication_Administration`, `Nursing_Intervention`, `Consultation_Request`, `Discharge_Planning`.
- **Priority:** `Urgent` (action required $\le 1$ hour), `Routine` (during the shift), `Elective` (next 24–48 hours).

---

## 9. Handling Ambiguous, Conflicting, and Missing Information

1. **Unknown Clinical Acronyms:** If a clinician writes an unverified abbreviation (e.g., *"Patient has PVO"*), retain the exact verbatim text in `source_text`, leave `normalized_concept` identical to verbatim, and set `review_status: "flagged_for_review"`.
2. **Conflicting Clinical Entries:** If a handover contains contradictory statements (e.g., narrative states *"patient afebrile"* but vitals list *"temp 101.4 F"*), annotators must annotate both entities verbatim and flag both with `conflict_flag: true`. Annotators must **never** reconcile clinical contradictions arbitrarily.
3. **Roman-Hindi (Hinglish) Vernacular:** Match against standardized medical concepts (e.g., *"sir dard"* $\implies$ `"Headache"`, *"kamzori"* $\implies$ `"Asthenia/Weakness"`), preserve the verbatim Hindi string, and set `language_origin: "hinglish"`.

---

## 10. Annotation and Adjudication Procedures

### 10.1 Reviewer Qualifications
- **Primary Annotators:** At least two independent licensed clinical reviewers per document (MBBS, MD, or Senior Registered Clinical Nurse Informaticist with $\ge 3$ years of clinical documentation experience).
- **Senior Adjudicator:** A senior specialist physician (MD / MS / DNB) with clinical informatics expertise.

### 10.2 Double-Blind Annotation Workflow
```
[Unannotated Clinical Note]
          │
          ├──► Blinded Annotator 1 (Dr. A) ──► Annotation Set 1
          │
          └──► Blinded Annotator 2 (Dr. B) ──► Annotation Set 2
                                                     │
                                                     ▼
                                      [Automated Concordance Engine]
                                                     │
                        ┌────────────────────────────┴────────────────────────────┐
                        ▼                                                         ▼
              Full Agreement Spans                                     Discordant Spans / Links
                        │                                                         │
                        ▼                                                         ▼
              Auto-Accepted to Gold                                   Senior Clinical Adjudication
                        │                                                         │
                        └────────────────────────────┬────────────────────────────┘
                                                     ▼
                                      [Consensus Gold Standard]
```

1. **Phase 1 — Blinded Annotation:** Annotator 1 and Annotator 2 annotate the document independently on an isolated annotation server without viewing each other's work.
2. **Phase 2 — Concordance Calculation:** An automated script identifies exact matching spans and relational edges. All matching spans are automatically promoted.
3. **Phase 3 — Clinical Adjudication:** All discordant spans, overlapping boundaries, discordant assertions, or conflicting attribute links are reviewed by the Senior Adjudicator, who makes the binding clinical consensus determination.

---

## 11. Inter-Annotator Agreement (IAA) Methodology

Inter-annotator agreement must be calculated prior to adjudication to assess annotation guideline clarity and reproducibility.

### 11.1 Metrics
1. **Span-Level Agreement (Unitized Span F1 / F-Measure):**
   Evaluates agreement on character boundaries and entity categories:
   $$\text{Agreement}_{\text{span}} = \frac{2 \cdot |A_1 \cap A_2|}{|A_1| + |A_2|}$$
   Calculated under both Strict (exact character match) and Lenient (token overlap) criteria.
2. **Attribute Classification Agreement (Cohen's $\kappa$):**
   Evaluates categorical attributes (Assertion, Temporality, Investigation Status) on aligned spans:
   $$\kappa = \frac{P_o - P_e}{1 - P_e}$$
3. **Relational Link Agreement (Krippendorff's $\alpha$):**
   Evaluates multi-annotator nominal agreement on directed medication-to-attribute links.

### 11.2 Quality Thresholds
- **Mandatory Quality Gate:** For any specialty sub-corpus to be certified for gold standard release, it must achieve:
  - Unitized Strict Span F1 $\ge 0.80$
  - Assertion $\kappa \ge 0.85$
  - Investigation Status $\kappa \ge 0.85$
  - Medication Attribute Linking $\alpha \ge 0.85$
- If agreement falls below threshold, annotation guidelines are refined, annotators are retrained, and the sub-corpus is re-annotated.

---

## 12. Dataset Versioning and Provenance Requirements

1. **Semantic Versioning:** The benchmark dataset adheres to SemVer (e.g., `v1.0.0-gold`).
2. **Document Checksums:** Every note has a recorded SHA-256 hash of its raw text:
   $$\text{doc\_hash} = \text{SHA256}(\text{raw\_text.encode('utf-8'))}$$
3. **Immutable Manifest:** All documents, checksums, specialty labels, annotator pseudonyms, and adjudication logs are registered in an immutable JSON manifest.
4. **Git LFS Storage:** Annotations are stored under Git Large File Storage (LFS) with strict commit tagging.

---

## 13. Three-Way Split Protocol (Dev / Val / Test)

The 250 notes are strictly partitioned into three disjoint subsets:

```
+--------------------------------------------------------------------------------------------------+
|                            PULSE 250-NOTE THREE-WAY PARTITION ARCHITECTURE                       |
+--------------------------+--------------------------+--------------------------------------------+
| Partition                | Allocation               | Purpose & Access Control Rules             |
+--------------------------+--------------------------+--------------------------------------------+
| **Development (DEV)**    | 100 Notes (40.0%)        | Accessible to engineers for lexicon tuning,|
|                          |                          | error analysis, regex crafting.            |
+--------------------------+--------------------------+--------------------------------------------+
| **Validation (VAL)**      | 50 Notes (20.0%)         | Used exclusively for hyperparameter tuning,|
|                          |                          | threshold calibration, and CRF selection.  |
+--------------------------+--------------------------+--------------------------------------------+
| **Held-Out Test (TEST)**  | 100 Notes (40.0%)        | Cryptographically locked. Blinded run only.|
|                          |                          | Zero developer inspection permitted.       |
+--------------------------+--------------------------+--------------------------------------------+
```

### 13.1 Anti-Leakage Rules (Firewall Protocol)
1. **Document-Level & Patient-Episode Disjointness:** No note from the same patient, admission episode, or identical institutional shift template may appear in more than one partition.
2. **Blinded Held-Out Test Set:** The 100 held-out test notes are encrypted with `AES-256`. The decryption key is held by an independent evaluation auditor.
3. **Single Execution Milestone:** The held-out benchmark runner is executed only once per release milestone. Model weights, lexicons, and pipeline hashes are frozen prior to decryption.

---

## 14. Evaluation Metrics Specification

| Metric | Formulation | Gold Requirement | Currently Computable? |
|---|---|---|:---:|
| **Strict Span Precision / Recall / F1** | Exact start, end, and category match | Entity Spans | **Yes** (Evaluated on 101 notes) |
| **Lenient Span Precision / Recall / F1** | Character overlap and category match | Entity Spans | **Yes** (Evaluated on 101 notes) |
| **Source-Offset Validity** | $note\_text[s:e] == source\_text$ | Raw text | **Yes** (100% verified) |
| **Medication Attribute Binding F1** | Correct drug-to-dose/route/freq edge | Relational Links | **Requires 250-Note Benchmark** |
| **Assertion Precision / Recall / F1** | Match on `Positive`, `Negated`, `Possible` | Assertion Tags | **Requires 250-Note Benchmark** |
| **Temporality F1** | Match on `Current`, `Historical`, `Planned`| Temporality Tags | **Requires 250-Note Benchmark** |
| **Investigation Status F1** | Match on 6 status enums | Status Tags | **Requires 250-Note Benchmark** |
| **Conditional Task Extraction** | Match on condition-action tuples | Contingent Tuples | **Requires 250-Note Benchmark** |
| **Unsupported Attribute Rate** | Unreferenced attributes / total extracted | Full Adjudication | **Requires 250-Note Benchmark** |

---

## 15. Data Governance and Readiness Checklist

The following regulatory and institutional milestones must be completed before real patient records are ingested:

```
+--------------------------------------------------------------------------------------------------+
|                                DATA GOVERNANCE PREREQUISITE CHECKLIST                            |
+----+---------------------------------------------------------------+--------------+---------------+
| #  | Prerequisite Item                                             | Status       | Action Owner  |
+----+---------------------------------------------------------------+--------------+---------------+
| 1. | Institutional Ethics Committee (IEC / IRB) Protocol Review    | UNRESOLVED   | Principal Inv |
| 2. | Formal Institutional Data-Owner Authorization Letter         | UNRESOLVED   | Hospital Admin|
| 3. | Data Transfer Agreement (DTA) / Data Use Agreement (DUA)      | UNRESOLVED   | Legal Counsel |
| 4. | De-Identification Validation & HIPAA Safe Harbor Compliance   | SPECIFIED    | Privacy Team  |
| 5. | Encrypted Role-Based Storage (AES-256 at rest, TLS 1.3 transit)| SPECIFIED    | DevOps / Sec  |
| 6. | Clinical Annotator Recruitment & Credential Verification      | UNRESOLVED   | Clinical Lead |
| 7. | Independent Adjudication Committee Formation                  | UNRESOLVED   | Clinical Lead |
| 8. | Benchmark Manifest Integrity Scaffolding                      | COMPLETED    | Eng Team      |
+----+---------------------------------------------------------------+--------------+---------------+
```

### Readiness Assessment
- **Protocol Status:** **PROTOCOL-READY** (Comprehensive annotation manual, relational schema, and split rules defined).
- **Data Status:** **NOT DATA-READY** (Zero real clinical records collected or authorized).
- **Annotation Status:** **NOT ANNOTATION-READY** (No annotators recruited or institutional approvals granted).
- **Evaluation Status:** **NOT EVALUATION-READY** (Benchmark dataset does not yet exist).
