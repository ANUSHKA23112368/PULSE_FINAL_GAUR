# PULSE — Independent Benchmark Design & Evaluation Architecture
**Document Version:** 1.0.0 (Phase 5, Step 4.2)  
**Classification:** Research Prototype Specification — Independent Evaluation Framework  
**Scope:** Multi-Specialty Indian Clinical Handover Intelligence Benchmark  

---

## 1. Executive Summary & Objective

The **Patient Update & Log Structuring Engine (PULSE)** is a clinical handover intelligence research prototype developed to convert complex, unstructured clinical notes and handover communications into structured, evidence-grounded patient handover summaries.

In Phase 5, Step 4.1, a rigorous technical audit identified critical limitations in historical benchmark claims:
1. The **101-note Nursing Handover Corpus** represents Commonwealth English (Australian hospital nursing handovers), completely lacking Indian clinical shorthand, Roman-Hindi/Hinglish phrasing, and reference tags for clinical assertion or temporality.
2. The **10-case Generalization Challenge Set** served as a developmental capability probe rather than an independent clinical validation suite. Furthermore, because challenge scenarios and normalizer dictionaries were authored concurrently, evaluating extractors on those 10 cases carries inherent contamination risk.
3. Historical claims of "0.0% hallucination" were an artifact of naive substring existence checking, failing to monitor negation inversion, attribute misbinding, or clinical assertion fidelity.

### Primary Objective of Step 4.2
Design an **independent, multi-specialty, clinically grounded benchmark framework** specifically tailored for Indian clinical documentation environments. This framework defines:
- A standardized **250-note multi-specialty evaluation corpus architecture**.
- A rigorous **annotation specification** capturing entity boundaries, canonical normalizations, directed attribute relationships, assertion, temporality, and investigation tracking.
- A **three-way isolated dataset split** (Development, Validation, Held-out Test) enforced by cryptographic firewalls to prevent data leakage and dictionary overfitting.
- A **double-blind clinical annotation and adjudication workflow** utilizing inter-rater reliability metrics (Krippendorff's $\alpha$, unitized span F1, and Cohen's $\kappa$).
- Strict **ethical, privacy, and regulatory governance protocols** compliant with Indian Digital Information Security in Healthcare (DISHA) principles, the Digital Personal Data Protection Act (DPDP 2023), and international HIPAA Safe Harbor de-identification standards.

> **CRITICAL DIRECTIVE:** This specification defines benchmark architecture and validation scaffolding. It strictly prohibits model fine-tuning, weight downloads, or claiming clinical validation before independent clinical adjudication is complete.

---

## 2. Clinical Scope & Multi-Specialty Representation

Clinical handover documentation in Indian healthcare facilities spans secondary and tertiary hospitals, government medical colleges, private hospital networks, and community clinics. Handover documentation styles, vocabulary density, abbreviation patterns, and clinical urgency vary substantially across departments.

To ensure authentic evaluation, the proposed benchmark incorporates six key clinical departments:

```
+---------------------------------------------------------------------------------------------------+
|                                  PULSE MULTI-SPECIALTY COVERAGE                                   |
+--------------------------+--------------------------+---------------------------------------------+
| Specialty Department     | Target Note Count        | Core Documentation Characteristics          |
+--------------------------+--------------------------+---------------------------------------------+
| 1. General Medicine      | 50 Notes (20%)           | Complex comorbidities (T2DM, HTN, CKD),     |
|                          |                          | polypharmacy, multi-system monitoring       |
+--------------------------+--------------------------+---------------------------------------------+
| 2. General & Ortho Surg  | 45 Notes (18%)           | Post-op status, drains, wound appearance,   |
|                          |                          | operative findings, NPO orders, analgesia   |
+--------------------------+--------------------------+---------------------------------------------+
| 3. Pediatrics & NICU     | 40 Notes (16%)           | Weight-based decimal dosing (mg/kg), birth  |
|                          |                          | history, developmental milestones, vaccines |
+--------------------------+--------------------------+---------------------------------------------+
| 4. Obstetrics & Gyn (OBG)| 35 Notes (14%)           | Obstetric score (G/P/L/A), gestational age, |
|                          |                          | fetal heart rate, labor stages, lochia      |
+--------------------------+--------------------------+---------------------------------------------+
| 5. Emergency Medicine    | 40 Notes (16%)           | High abbreviation density, rapid triage,    |
|                          |                          | trauma protocols, acute symptom onset       |
+--------------------------+--------------------------+---------------------------------------------+
| 6. Critical Care (ICU)   | 40 Notes (16%)           | Inotropic support, ventilator settings,     |
|                          |                          | invasive lines, ABG values, GCS, acuity     |
+--------------------------+--------------------------+---------------------------------------------+
| TOTAL CORPUS             | 250 Handover Notes       | 100% Offset-Aligned & Clinically Audited    |
+--------------------------+--------------------------+---------------------------------------------+
```

---

## 3. Linguistic & Clinical Documentation Phenomena Matrix

Indian clinical documentation features distinctive linguistic blends, regional shorthand, and formatting habits that confound standard Western clinical NLP pipelines. The benchmark explicitly audits 15 distinct phenomena:

### 3.1 Indian Clinical Shorthand & Acronyms
Indian clinicians routinely employ specific clinical abbreviations:
- `K/C/O`: Known Case Of (e.g., *"K/C/O CAD, post-PTCA"*)
- `C/O`: Complaints Of (e.g., *"C/O chest tightness x 2 hrs"*)
- `S/B`: Seen By (e.g., *"S/B On-call Medicine SR"*)
- `B/L`: Bilateral (e.g., *"B/L creps in lung bases"*)
- `NAD`: No Abnormality Detected
- `RBS` / `FBS` / `PPBS`: Random, Fasting, Post-Prandial Blood Sugar
- `LMP` / `EDD` / `POG`: Last Menstrual Period, Estimated Date of Delivery, Period of Gestation
- `POD`: Post-Operative Day (e.g., *"POD 2 exploratory laparotomy"*)
- `GCS`: Glasgow Coma Scale (e.g., *"GCS E4V5M6 = 15/15"*)

### 3.2 Roman-Script Hinglish Clinical Expressions
In oral handovers transcribed by voice or informal notes, clinicians frequently mix Hindi symptom terminology written in the Roman alphabet:
- Pain: *"Chhati mein dard"*, *"pet mein jalan"*, *"sir dard"*
- Sensations: *"Chakkar aa raha hai"* (Dizziness), *"ghabrahat ho rahi hai"* (Anxiety/Palpitations), *"kamzori"* (Weakness)
- Gastrointestinal: *"Ulti hui thi"* (Vomiting), *"dust lag gaye"* (Diarrhea), *"pet phoola hua hai"* (Abdominal Distension)
- Systemic: *"Tez bukhar hai"* (High Fever), *"saans phool rahi hai"* (Shortness of Breath)

### 3.3 Decimal Dosage Fidelity & Critical Multi-Medication Notes
Medication safety requires absolute precision in numeric dosages:
- Leading zeros: `0.25 mg` Digoxin, `0.05 mg` Thyroxine, `0.5 ml` injections. A system must never corrupt `0.25` into `25` or `0`.
- Split frequencies: `BD` (Twice Daily), `TDS` (Thrice Daily), `OD` (Once Daily), `QID` (Four Times Daily), `SOS` / `PRN` (As Needed), `mane` (Morning), `nocte` (Night).
- Cross-talk defense: When a single note contains 4 or more medications (e.g., Ceftriaxone, Pantoprazole, Paracetamol, Tramadol), the system must bind each dose and route strictly to the correct parent medication without attribute swapping.

### 3.4 Investigation Lifecycle Tracking
Clinical investigations pass through distinct operational states that dictate clinician actions:
- `ORDERED`: Clinician advised or prescribed test (e.g., *"Advised urgent CT pulmonary angiogram"*).
- `SENT`: Specimen sent to laboratory (e.g., *"Blood cultures sent to microbiology"*).
- `AWAITING_RESULTS`: Specimen received; test running (e.g., *"Awaiting serum electrolytes report"*).
- `COMPLETED`: Results available in chart (e.g., *"Chest X-ray completed: shows right lower lobe infiltrate"*).

### 3.5 Negation, Uncertainty & Temporality
- **Negation:** Distinguish affirmed findings from explicitly denied symptoms (*"No chest pain"*, *"Bukhar nahi hai"*, *"Denies shortness of breath"*).
- **Uncertainty / Differential:** Distinguish confirmed diagnoses from working differentials (*"Suspected pulmonary embolism"*, *"Shayad dengue ho sakta hai"*, *"Rule out sepsis"*).
- **Temporality:** Distinguish active presenting complaints (*"Currently febrile"*) from remote medical history (*"H/O cholecystectomy 5 years back"*, *"Childhood asthma, resolved"*) and planned interventions (*"Scheduled for echo tomorrow"*).

### 3.6 Negative Controls & Acuity False Positives
To prevent over-triggering:
- Linguistic distractor: *"Patient admitted to acute ward"* must NOT extract "acute condition" or "headache".
- Non-clinical tokens: *"Signed petition for discharge against medical advice"* must NOT extract "petition" as a symptom or disease.
- Title/Administrative tokens: *"Dr. Heartley visited"* must NOT extract "heart" as a cardiology finding.

---

## 4. Benchmark Architecture & Three-Way Dataset Partition

To prevent data contamination, model overfitting, and developmental leakage, the 250-note corpus is strictly partitioned into three independent subsets:

```
+--------------------------------------------------------------------------------------------------+
|                            PULSE 250-NOTE CORPUS THREE-WAY PARTITION                             |
+--------------------------------------------------------------------------------------------------+
|                                                                                                  |
|   +--------------------------+    +--------------------------+    +--------------------------+   |
|   |   DEVELOPMENT SET (DEV)  |    |  VALIDATION SET (VAL)    |    |   HELD-OUT TEST (TEST)   |   |
|   |   100 Notes (40%)        |    |  50 Notes (20%)          |    |   100 Notes (40%)        |   |
|   +--------------------------+    +--------------------------+    +--------------------------+   |
|   | • Rule & Regex Tuning    |    | • Hyperparameter tuning  |    | • Cryptographically locked |
|   | • Lexicon expansion      |    | • Threshold calibration  |    | • Zero developer access  |   |
|   | • Error inspection       |    | • Error analysis cycles  |    | • Blinded execution      |   |
|   | • Regression testing     |    | • Component ablation     |    | • Final benchmark report |   |
|   +--------------------------+    +--------------------------+    +--------------------------+   |
|                                                                                                  |
+--------------------------------------------------------------------------------------------------+
```

### 4.1 Development Set (PULSE-DEV-100)
- **Size:** 100 Notes (40% of corpus).
- **Purpose:** Used by software engineers and computational linguists to design regexes, refine dictionary rules, develop normalization mappings, and implement feature extractors.
- **Access:** Unrestricted access for iterative development, unit testing, and regression verification.

### 4.2 Validation Set (PULSE-VAL-50)
- **Size:** 50 Notes (20% of corpus).
- **Purpose:** Used for model selection, threshold calibration, and hyperparameter tuning (e.g., regularized logistic regression $C$ value, subword aggregation thresholds).
- **Access:** Evaluated periodically in batch mode. Developers may inspect aggregate performance metrics, but individual note error inspection is strictly logged to prevent manual memorization.

### 4.3 Independent Held-Out Evaluation Set (PULSE-HELD-OUT-100)
- **Size:** 100 Notes (40% of corpus).
- **Purpose:** Final, unbiased evaluation of system performance across all models (pure rules, statistical baselines, Bio_ClinicalBERT, PULSE hybrid).
- **Isolation Firewall (Anti-Leakage Protocol):**
  1. The held-out dataset is encrypted (`AES-256`) and stored in a restricted directory.
  2. Developers, rule authors, and prompt engineers are **strictly prohibited** from viewing raw texts or annotations from this set.
  3. No lexicon, regex pattern, vocabulary item, or normalizer mapping may be added to the codebase based on inspection of held-out notes.
  4. The benchmark runner is executed on the held-out set **only once per release milestone** via an automated, audited execution script.
  5. The evaluation script logs SHA-256 hashes of all model weights, rule lexicons, and codebase files before evaluation commences to guarantee reproducibility.

---

## 5. Model Evaluation Protocol

Every extractor evaluated on the PULSE Benchmark must interface through the standardized [`BaseClinicalExtractor`](file:///c:/Users/akg50/Desktop/prototype/backend/extraction/contract.py#L39-L120) contract and output [`ClinicalEntity`](file:///c:/Users/akg50/Desktop/prototype/backend/extraction/contract.py#L40) records.

### 5.1 Evaluated Approaches
1. **Pure Rule-Based Engine:** Deterministic lexicons, clinical regexes, and morphology rules.
2. **Statistical Sequence Classifier:** Linguistic feature vectorizer (`DictVectorizer`) with L2-regularized sequence logistic classification.
3. **Bio_ClinicalBERT Baseline:** Fine-tuned token classification transformer (`emilyalsentzer/Bio_ClinicalBERT`) evaluated across subword token boundaries.
4. **PULSE Hybrid Pipeline:** Integrated extraction pipeline combining deterministic lexicons, Indian clinical shorthand normalizers, Roman-Hindi mappers, contextual assertion/temporality resolvers, and open-vocabulary candidate preservation.
5. **Local Small Language Model (SLM):** Explicitly audited. Evaluated only if a quantized, local GGUF/ONNX/PyTorch model (e.g., BioMistral-7B-Q4, Llama-3-Med-8B-Q4) is available locally. External hosted LLM APIs remain strictly prohibited.

### 5.2 Evaluated Metrics & Mathematical Formulas

Every metric must report explicit numerators and denominators (e.g., $19/21\ (90.5\%)$).

1. **Strict Span Matching:**
   A predicted span $p = (s_p, e_p, c_p)$ matches a gold reference span $g = (s_g, e_g, c_g)$ if and only if:
   $$s_p = s_g \quad \land \quad e_p = e_g \quad \land \quad \text{norm\_cat}(c_p) = \text{norm\_cat}(c_g)$$
   Precision ($P$), Recall ($R$), and F1 score ($F_1$):
   $$P_{\text{strict}} = \frac{TP_{\text{strict}}}{|P|}, \quad R_{\text{strict}} = \frac{TP_{\text{strict}}}{|G|}, \quad F_{1,\text{strict}} = \frac{2 \cdot P \cdot R}{P + R}$$

2. **Lenient Span Matching:**
   A predicted span $p$ matches gold span $g$ if:
   $$\max(s_p, s_g) < \min(e_p, e_g) \quad \land \quad \text{norm\_cat}(c_p) = \text{norm\_cat}(c_g)$$
   Each gold entity can be matched by at most one prediction (1-to-1 matching). Extra overlapping predictions are counted as false positives ($FP$).

3. **Medication Attribute Binding Accuracy:**
   For all gold medications $m \in G_{\text{med}}$ with bound attributes $A(m) \subseteq \{\text{dose}, \text{route}, \text{frequency}\}$:
   $$\text{Binding Accuracy} = \frac{\sum_{m \in G_{\text{med}}} \sum_{a \in A(m)} \mathbb{I}(p_{\text{bound}}(m, a) = g(m, a))}{\sum_{m \in G_{\text{med}}} |A(m)|}$$

4. **Clinical Assertion Accuracy:**
   $$\text{Assertion Accuracy} = \frac{\sum_{e \in G_{\text{aligned}}} \mathbb{I}(\text{pred\_assertion}(e) = \text{gold\_assertion}(e))}{|G_{\text{aligned}}|}$$

5. **Investigation Status Accuracy:**
   $$\text{Status Accuracy} = \frac{\sum_{i \in G_{\text{inv}}} \mathbb{I}(\text{pred\_status}(i) = \text{gold\_status}(i))}{|G_{\text{inv}}|}$$

6. **Source Groundedness Taxonomy (Replacing Naive Hallucination):**
   Every predicted entity is classified into one of five mutually exclusive grounding categories:
   - $N_{\text{supp}}$: `source_supported_extraction`
   - $N_{\text{norm}}$: `valid_normalization`
   - $N_{\text{unsupp\_ass}}$: `unsupported_assertion`
   - $N_{\text{unsupp\_attr}}$: `unsupported_attribute`
   - $N_{\text{unres}}$: `unresolved_case`
   $$\text{Groundedness Ratio} = \frac{N_{\text{supp}} + N_{\text{norm}}}{N_{\text{total\_extracted}}}$$

---

## 6. Execution Timeline & Governance Gateways

```
Phase 5, Step 4.2: Benchmark Design & Annotation Specification (CURRENT)
       │
       ▼
Gate 1: Clinical Protocol Review & Institutional Ethics Approval (IRB/EC)
       │
       ▼
Phase 5, Step 4.3: Double-Blind Clinical Annotation & Gold Standard Adjudication
       │
       ▼
Gate 2: Inter-Rater Reliability Threshold Verification (Krippendorff's α ≥ 0.80)
       │
       ▼
Phase 5, Step 4.4: Automated Blinded Benchmark Execution & Publication Report
```

This roadmap guarantees that before any model is evaluated or compared, the benchmark dataset has achieved verified clinical authorization, cryptographic isolation, and high inter-rater agreement.
