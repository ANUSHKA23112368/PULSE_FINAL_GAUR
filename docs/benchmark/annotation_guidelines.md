# PULSE — Clinical Annotation Guidelines & Protocol Manual
**Document Version:** 1.0.0 (Phase 5, Step 4.2)  
**Target Audience:** Clinical Annotators (MBBS, MD, Clinical Nurse Informaticists, Medical Terminologists)  
**Scope:** Gold-Standard Handover Annotation for Indian Clinical NLP  

---

## 1. Ethical Foundations & Core Annotation Principles

### Principle 1: Evidence Preservation & Verbatim Grounding
Every annotated entity must be grounded in an exact, contiguous character span in the source text. 
- **Character Spans:** Annotations use 0-indexed half-open intervals `[start_char, end_char)`.
- **Verbatim Rule:** `source_text == raw_text[start_char:end_char]`. Never trim or expand spans across non-contiguous tokens unless utilizing the `all_spans` multi-span mechanism.
- **No Whitespace Padding:** Never include leading or trailing spaces in entity spans (e.g., annotate `"Paracetamol"`, not `" Paracetamol "`).

### Principle 2: Zero Clinical Invention (No Diagnostic Extrapolation)
Annotate strictly what is documented in the text.
- If a note states *"Patient has high sugar"*, annotate `Clinical_Observation` with text `"high sugar"`. **DO NOT** annotate an unstated diagnosis of `"Diabetes Mellitus"` unless explicitly written in the note.
- If a medication dosage is missing (e.g., *"Tab Metoprolol BD"*), record `dosage: null`. **DO NOT** assume standard doses (e.g., 25 mg or 50 mg).

### Principle 3: Separation of Raw Text, Normalization, and Provenance
When encountering Indian clinical shorthand or Roman-Hindi/Hinglish phrasing:
1. `source_text`: The exact verbatim string as written (e.g., `"chakkar aa raha hai"`, `"K/C/O"`).
2. `normalized_concept`: The standardized medical concept (e.g., `"Dizziness"`, `"Known Case Of"`).
3. `normalization_provenance`: The mapping dictionary or rule applied (e.g., `"hinglish_mapping"`, `"indian_shorthand_dict"`).

---

## 2. Harmonized Clinical Macro-Categories & Definitions

Every extracted entity must be assigned to one of the **10 Harmonized Macro-Categories**:

| Macro-Category | Description | Inclusion Examples | Exclusion Examples |
|---|---|---|---|
| `Demographics_Bed` | Patient physical location | *"Bed 4"*, *"Bed 12B"*, *"Room 201"*, *"ICU Bed 2"* | General wards (*"acute ward"*) |
| `Demographics_Name` | Patient first, middle, last name | *"Arthur Pendelton"*, *"Mr. Rajesh Sharma"*, *"Sunita"* | Clinician names, relative names |
| `Demographics_Age` | Chronological age | *"68 years"*, *"4 months"*, *"72 yo"*, *"POD 3 infant"* | Duration of illness (*"for 3 days"*) |
| `Demographics_Gender` | Gender identity or biological sex | *"Male"*, *"Female"*, *"he"*, *"she"*, *"F"* | Clinical sex-linked diagnoses |
| `Demographics_Doctor` | Attending physician or consultant | *"Dr. Edwards"*, *"Dr Sharma"*, *"Consultant Surgeon"* | Pharmacists, non-clinical visitors |
| `Clinical_Condition` | Formal disease, syndrome, pathology | *"congestive cardiac failure"*, *"T2DM"*, *"HTN"*, *"appendicitis"* | Symptoms (*"pain"*), lab tests (*"RBS"*) |
| `Clinical_Observation` | Symptom, clinical sign, bedside finding | *"shortness of breath"*, *"headache"*, *"pedal edema"*, *"GCS 15/15"* | Formal diagnoses, medications |
| `Medication` | Pharmacological agent or IV fluid | *"Furosemide"*, *"Metoprolol"*, *"RL"*, *"Normal Saline"*, *"PCM"* | Medical contraptions (*"IV cannula"*) |
| `Investigation_Procedure` | Lab test, imaging, diagnostic probe | *"Chest X-Ray"*, *"CBC"*, *"USG abdomen"*, *"CT head"*, *"troponin-T"* | Surgical therapies (*"appendectomy"*) |
| `Care_Activity` | Nursing intervention, treatment, activity | *"foley catheter insertion"*, *"dressing change"*, *"nebulization"* | Diagnostic investigations |
| `Plan_Goal` | Care plan, pending handover task | *"Discharge planned tomorrow"*, *"fluid restriction 1L"* | Past completed events |
| `Unclassified` | Ambiguous acronym or open candidate | *"XYZ documented"*, *"suspected OD on unknown tabs"* | Standard verified medical concepts |

---

## 3. Detailed Annotation Specifications

### 3.1 Medication Attribute Binding Specification
Medications are central to handover safety. Annotators must establish direct hierarchical links from each `Medication` parent entity to its bound attributes:

```
[Medication: Paracetamol] (ID: ent_01)
       │
       ├─── [dosage: 1g] (ID: ent_01_dose)
       ├─── [route: PO] (ID: ent_01_route)
       └─── [frequency: PRN] (ID: ent_01_freq)
```

#### Bound Attribute Fields:
1. `dosage`: Verbatim dosage string (e.g., `"1g"`, `"40 mg"`, `"0.25 mg"`, `"12.5 mg"`, `"100mg IV"`).
   - *Decimal Rule:* Retain leading zeros and decimal points verbatim (`"0.25 mg"`).
2. `route`: Administration route (e.g., `"PO"`, `"IV"`, `"IM"`, `"SC"`, `"Inhalation"`, `"Topical"`, `"Sublingual"`).
3. `frequency`: Administration schedule (e.g., `"OD"`, `"BD"`, `"TDS"`, `"QID"`, `"Q4H"`, `"PRN"` / `"SOS"`, `"mane"`, `"nocte"`, `"stat"`).
4. `prn_indication`: Reason for PRN use (e.g., *"for pain"*, *"for fever"*).

---

### 3.2 Investigation Status Specification
Every `Investigation_Procedure` entity must be assigned exactly one lifecycle status:

1. `ORDERED`: The investigation has been recommended, ordered, or scheduled, but specimens have not yet been sent.
   - Evidence phrases: *"Advised USG"*, *"Order CT chest"*, *"Scheduled for echo next shift"*.
2. `SENT`: The specimen has been collected and dispatched to the pathology/radiology department.
   - Evidence phrases: *"Blood cultures sent off to lab"*, *"Urine sample sent"*, *"Biopsy dispatched"*.
3. `AWAITING_RESULTS`: The test has been performed or specimen received; results are currently awaited.
   - Evidence phrases: *"Awaiting potassium results"*, *"Echo report awaited"*, *"Troponin result pending"*.
4. `COMPLETED`: The investigation report is available and documented in the chart.
   - Evidence phrases: *"Chest X-Ray is completed"*, *"Echocardiogram done this morning"*, *"RBS showed 180 mg/dl"*.
5. `UNKNOWN`: The text mentions the test without documenting its operational status (e.g., *"CBC and LFT"*).

---

### 3.3 Clinical Assertion Specification
Clinical assertion captures the diagnostic certainty and polarity of symptoms, findings, and conditions:

1. `Positive` / `Present` (Default): The entity is affirmed as present in the patient.
   - Example: *"Patient has severe headache."* $\rightarrow$ `assertion: "Positive"`
2. `Negated`: The entity is explicitly documented as absent or denied.
   - Evidence phrases: *"denies"*, *"no"*, *"nil"*, *"free of"*, *"nahi hai"*, *"absent"*.
   - Example: *"Patient denies chest pain."* $\rightarrow$ `assertion: "Negated"`
   - Example: *"Bukhar nahi hai."* $\rightarrow$ `assertion: "Negated"`
3. `Possible` / `Uncertain`: The finding is considered a differential, possibility, or suspected risk.
   - Evidence phrases: *"suspected"*, *"rule out"*, *"possible"*, *"likely"*, *"shayad"*, *"query"*, *"?"*.
   - Example: *"Shayad infection hai."* $\rightarrow$ `assertion: "Possible"`
   - Example: *"Query appendicitis."* $\rightarrow$ `assertion: "Possible"`

---

### 3.4 Temporality Specification
Temporality anchors clinical findings relative to the current handover shift:

1. `Current` / `Recent` (Default): Finding is active during the current admission or handover shift.
   - Example: *"Complains of shortness of breath right now."* $\rightarrow$ `temporality: "Current"`
2. `Historical`: Finding occurred in the past, represents chronic background, or has resolved.
   - Evidence phrases: *"K/C/O"*, *"history of"*, *"diagnosed 5 years back"*, *"kal hui thi, par ab nahi hai"*.
   - Example: *"K/C/O T2DM and HTN."* $\rightarrow$ `temporality: "Historical"`
   - Example: *"Kal ulti hui thi, par ab theek hai."* $\rightarrow$ `temporality: "Historical"`
3. `Planned`: Event or action scheduled for a future shift or post-discharge.
   - Evidence phrases: *"Plan for"*, *"scheduled tomorrow"*, *"for discharge"*, *"to undergo"*.
   - Example: *"Patient is for carotid doppler tomorrow morning."* $\rightarrow$ `temporality: "Planned"`

---

### 3.5 Roman-Hindi / Hinglish Normalization Specification
When annotating Hinglish clinical expressions:
- Span boundaries must cover the **entire idiomatic phrase** responsible for the clinical finding.
- The `normalized_concept` must capture the standard clinical meaning in standard medical English.

| Source Hinglish Text | Character Span Example | Macro-Category | Normalized Concept | Assertion | Temporality |
|---|---|---|---|---|---|
| `"chakkar aa raha hai"` | `[20, 39)` | `Clinical_Observation` | `"Dizziness"` | `Positive` | `Current` |
| `"ulti hui thi"` | `[52, 65)` | `Clinical_Observation` | `"Vomiting"` | `Positive` | `Historical` |
| `"Chhati mein dard"` | `[62, 78)` | `Clinical_Observation` | `"Chest Pain"` | `Positive` | `Current` |
| `"tez bukhar hai"` | `[87, 101)` | `Clinical_Observation` | `"Fever"` | `Positive` | `Current` |
| `"Kamzori lag rahi hai"` | `[103, 123)` | `Clinical_Observation` | `"Weakness"` | `Positive` | `Current` |
| `"saans lene mein dikkat"` | `[15, 37)` | `Clinical_Observation` | `"Dyspnea"` | `Positive` | `Current` |
| `"pet mein jalan"` | `[40, 54)` | `Clinical_Observation` | `"Heartburn/Dyspepsia"` | `Positive` | `Current` |

---

## 4. Complete JSON Annotation Schema

Every gold-standard note must adhere strictly to the following machine-verifiable JSON schema:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "PULSEGoldStandardHandoverNote",
  "type": "object",
  "required": [
    "document_id",
    "specialty",
    "raw_text",
    "char_count",
    "is_synthetic",
    "dataset_split",
    "entities",
    "annotation_metadata"
  ],
  "properties": {
    "document_id": { "type": "string" },
    "specialty": { 
      "type": "string",
      "enum": ["General Medicine", "Surgery & Orthopedics", "Pediatrics & NICU", "Obstetrics & Gynecology", "Emergency Care", "Critical Care (ICU)"]
    },
    "raw_text": { "type": "string" },
    "char_count": { "type": "integer" },
    "is_synthetic": { "type": "boolean" },
    "dataset_split": { 
      "type": "string",
      "enum": ["development", "validation", "held_out_test"]
    },
    "entities": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "entity_id",
          "macro_category",
          "source_text",
          "start_char",
          "end_char",
          "assertion",
          "temporality",
          "review_status"
        ],
        "properties": {
          "entity_id": { "type": "string" },
          "macro_category": {
            "type": "string",
            "enum": [
              "Demographics_Bed", "Demographics_Name", "Demographics_Age", 
              "Demographics_Gender", "Demographics_Doctor", "Clinical_Condition", 
              "Clinical_Observation", "Medication", "Investigation_Procedure", 
              "Care_Activity", "Plan_Goal", "Unclassified"
            ]
          },
          "source_text": { "type": "string" },
          "start_char": { "type": "integer", "minimum": 0 },
          "end_char": { "type": "integer", "minimum": 1 },
          "normalized_concept": { "type": ["string", "null"] },
          "assertion": { 
            "type": "string",
            "enum": ["Positive", "Negated", "Possible"]
          },
          "temporality": {
            "type": "string",
            "enum": ["Current", "Historical", "Planned"]
          },
          "investigation_status": {
            "type": ["string", "null"],
            "enum": [null, "Ordered", "Sent", "Awaiting Results", "Completed", "Unknown"]
          },
          "medication_attributes": {
            "type": ["object", "null"],
            "properties": {
              "dosage": { "type": ["string", "null"] },
              "route": { "type": ["string", "null"] },
              "frequency": { "type": ["string", "null"] },
              "prn_indication": { "type": ["string", "null"] }
            }
          },
          "review_status": {
            "type": "string",
            "enum": ["confirmed", "flagged_for_review", "unreviewed"]
          }
        }
      }
    },
    "annotation_metadata": {
      "type": "object",
      "required": ["annotator_ids", "adjudication_status"],
      "properties": {
        "annotator_ids": { "type": "array", "items": { "type": "string" } },
        "adjudication_status": { 
          "type": "string",
          "enum": ["single_annotated", "dual_annotated_unadjudicated", "clinically_adjudicated"]
        },
        "adjudicator_id": { "type": ["string", "null"] },
        "adjudication_notes": { "type": ["string", "null"] }
      }
    }
  }
}
```

---

## 5. Human Review & Inter-Rater Reliability (IRR) Protocol

To ensure true clinical ground truth, all benchmark notes must pass through a two-stage blinded clinical annotation process:

```
[Unannotated De-identified Clinical Note]
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
  [Annotator A]        [Annotator B]
   (MD Medicine)        (Clinical Nurse Spec)
         │                   │
         └─────────┬─────────┘
                   ▼
     [Automated Disagreement Report]
         • Span boundary delta > 0
         • Macro-category mismatch
         • Attribute binding conflict
         • Assertion / Temporality delta
                   │
                   ▼
     [Senior Clinical Adjudicator]
       (MBBS / Senior Consultant)
                   │
                   ▼
   [Final Audited Gold Standard Note]
```

### 5.1 Inter-Rater Reliability Metrics
Before adjudication, independent annotations from Annotator A and Annotator B must be compared across three statistical dimensions:

1. **Span-Level Unitized Agreement (Krippendorff's $\alpha_u$):**
   Evaluates agreement on continuous character span boundaries and category assignment. Target: $\alpha_u \ge 0.80$.
2. **Categorical Attribute Agreement (Cohen's $\kappa$):**
   Calculated across aligned entity spans for:
   - Macro-category assignment ($\kappa_{\text{cat}}$)
   - Clinical assertion ($\kappa_{\text{ass}}$)
   - Clinical temporality ($\kappa_{\text{temp}}$)
   - Investigation lifecycle status ($\kappa_{\text{inv}}$)
   Target: $\kappa \ge 0.85$ for all categorical attributes.
3. **Medication Binding Agreement ($F_1$ link agreement):**
   Evaluates whether Annotator A and B linked the exact same dosage, frequency, and route spans to the same medication parent entity. Target: $F_{1,\text{link}} \ge 0.90$.

---

## 6. Edge Cases & Decision Rules

1. **Ambiguous Acronyms (e.g., `OD`):**
   - If context indicates medication schedule (*"Tab Remdesivir 100mg IV OD"*), annotate as `frequency: "OD"`.
   - If context indicates right eye (*"Injury to OD"*), annotate `Clinical_Observation` with `normalized_concept: "Right Eye"`.
   - If context indicates drug overdose (*"Suspected OD on sleeping pills"*), annotate `Clinical_Condition` with `review_status: "flagged_for_review"`.
2. **Multiple Doses for One Medication:**
   - Example: *"Take Prednisolone 20mg in morning and 10mg in evening"*.
   - Create two directed links: link 1 (dose: `"20mg"`, freq: `"morning"`), link 2 (dose: `"10mg"`, freq: `"evening"`).
3. **Compound Symptoms:**
   - Example: *"Nausea and vomiting"*.
   - Annotate as two distinct entities: span `[0, 6)` `"Nausea"` (`Clinical_Observation`), span `[11, 19)` `"vomiting"` (`Clinical_Observation`). Never combine into a single compound entity.
4. **Acronyms with Periods / Slashes:**
   - Maintain verbatim formatting: `"K/C/O"`, `"B/L"`, `"S.O.S."`.
5. **Negative Controls:**
   - If a sentence contains non-clinical terms that resemble medical conditions (e.g., *"Patient admitted to acute ward yesterday. Handover petition reviewed."*):
   - **DO NOT** annotate `"acute ward"` as a Condition.
   - **DO NOT** annotate `"petition"` as a symptom.
   - Leave non-clinical text completely unannotated.

---

## 7. Quality Assurance Checklist for Adjudicators

Before certifying a note as `clinically_adjudicated`:
- [ ] Every character span `[start_char, end_char)` matches `raw_text` character-for-character.
- [ ] No entity span contains leading or trailing whitespace.
- [ ] Every medication has its dosage, route, and frequency bound to the correct medication ID.
- [ ] Every investigation has an explicit status (`Ordered`, `Sent`, `Awaiting Results`, `Completed`, `Unknown`).
- [ ] Negated symptoms have `assertion: "Negated"`.
- [ ] Historical conditions (e.g. `K/C/O`) have `temporality: "Historical"`.
- [ ] Ambiguous acronyms or novel clinical terms have `review_status: "flagged_for_review"`.
- [ ] Both annotators' identities and adjudicator ID are recorded.
- [ ] Note is explicitly tagged with `is_synthetic: true` if synthetic scaffolding.
