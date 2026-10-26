# PULSE — Independent Benchmark Coverage Matrix & Distribution Rationale
**Document Version:** 1.0.0 (Phase 5, Step 4.2)  
**Corpus Target Size:** 250 Clinical Handover Notes  
**Standardized Format:** JSON Offset-Aligned Schema (`PULSEGoldStandardHandoverNote`)  

---

## 1. Overview & Rationale for Non-Uniform Distribution

A common error in benchmark construction is enforcing an artificial, uniform distribution across clinical categories (e.g., allocating exactly 25 notes to every specialty or phenomenon). Clinical reality in hospital handover documentation is inherently non-uniform:
- **Pediatrics & NICU:** Features intense concentration of weight-based decimal dosing (`0.05 mg`, `12.5 mcg/kg/min`) and liquid formulations (`ml/hr`), but minimal Roman-Hindi expressions compared to adult medicine wards.
- **Emergency Care:** Exhibits the highest density of diagnostic uncertainty (`Possible` assertion), rapid triage shorthand (`GCS`, `RBS`, `S/B`, `C/O`), and pending investigations (`Ordered`, `Sent`), but low chronic disease temporality.
- **General Medicine:** Represents the highest prevalence of polypharmacy (4+ concurrent medications with risk of cross-talk attribute binding errors), chronic comorbidities (`K/C/O T2DM, HTN, CKD`), and Roman-Hindi/Hinglish symptom descriptions (*"chakkar"*, *"kamzori"*, *"pet mein jalan"*).
- **Critical Care (ICU/CCU):** Characterized by multi-line inotropic support, invasive monitoring parameters (`CVP`, `MAP`, `ventilator mode`), and high acuity false-positive risks.
- **Obstetrics & Gynecology:** Contains unique obstetric shorthand (`G2P1L1A0`, `POG 34 wks`, `FHR 140 bpm`) and time-sensitive pending delivery plans.
- **General & Orthopedic Surgery:** Dominated by post-operative day tracking (`POD 2`), surgical drain outputs, wound status, and pain analgesia regimens.

Therefore, the PULSE 250-Note Benchmark establishes a **clinically rationalized, non-uniform coverage distribution**.

---

## 2. Multi-Specialty & Dataset Split Distribution

The 250 notes are divided across the three isolated partitions:
- **Development (DEV-100):** 100 Notes (40%) — Open for lexicon expansion, regex refinement, and regression testing.
- **Validation (VAL-50):** 50 Notes (20%) — Restricted for threshold calibration and ablation analysis.
- **Held-Out Test (HELD-OUT-100):** 100 Notes (40%) — Cryptographically locked for blinded evaluation.

```
+---------------------------------------------------------------------------------------------------------+
|                                    SPECIALTY DISTRIBUTION ACROSS SPLITS                                 |
+------------------------------+------------+------------+---------------+-------------+------------------+
| Clinical Specialty           | Dev (100)  | Val (50)   | Test (100)    | Total Notes | % of Corpus      |
+------------------------------+------------+------------+---------------+-------------+------------------+
| 1. General Medicine          | 20         | 10         | 20            | 50          | 20.0%            |
| 2. General & Ortho Surgery   | 18         | 9          | 18            | 45          | 18.0%            |
| 3. Pediatrics & NICU         | 16         | 8          | 16            | 40          | 16.0%            |
| 4. Obstetrics & Gynecology   | 14         | 7          | 14            | 35          | 14.0%            |
| 5. Emergency Care (Casualty) | 16         | 8          | 16            | 40          | 16.0%            |
| 6. Critical Care (ICU/CCU)   | 16         | 8          | 16            | 40          | 16.0%            |
+------------------------------+------------+------------+---------------+-------------+------------------+
| TOTAL NOTES                  | 100 (40%)  | 50 (20%)   | 100 (40%)     | 250         | 100.0%           |
+------------------------------+------------+------------+---------------+-------------+------------------+
```

---

## 3. Clinical & Documentation Phenomena Coverage Matrix

Every note in the benchmark is tagged with the primary and secondary documentation phenomena it manifests. The target instance representation across the 250 notes is specified below:

| Phenomenon Code | Clinical Documentation Phenomenon | Target Note Count | Min. Entity Target Instances | Primary Clinical Department Focus | Clinical Justification & Rationale |
|---|---|---:|---:|---|---|
| `PHEN_01` | **Indian Clinical Shorthand** (`K/C/O`, `S/B`, `C/O`, `B/L`, `RBS`) | 160 notes (64%) | 450 instances | Medicine, Surgery, Emergency | Standard practice across Indian hospital shifts; non-Indian models fail to parse. |
| `PHEN_02` | **Roman-Hindi / Hinglish Phrases** (*chakkar*, *ulti*, *chhati mein dard*) | 80 notes (32%) | 180 instances | Medicine, Emergency, Surgery | Reflects bilingual handover reality; prevents translation hallucination. |
| `PHEN_03` | **Decimal Dosage Fidelity** (`0.25 mg`, `12.5 mg`, `0.05 mg`) | 95 notes (38%) | 220 instances | Pediatrics, ICU, Medicine | High risk of ten-fold overdose if decimal points or leading zeros are dropped. |
| `PHEN_04` | **Medication Attribute Binding** (Parent $\rightarrow$ Dose, Route, Freq) | 210 notes (84%) | 650 medications | All Specialties | Handover communication must bind dose strictly to drug; prevents attribute swap. |
| `PHEN_05` | **Multi-Medication Cross-Talk Defense** (4+ meds in one note) | 75 notes (30%) | 380 medications | ICU, Medicine, Surgery | Tests graph binding algorithms under complex polypharmacy conditions. |
| `PHEN_06` | **Investigation Lifecycle Tracking** (Ordered vs Sent vs Done) | 180 notes (72%) | 420 investigations | Emergency, Surgery, Medicine | Pending investigations represent primary source of handover clinical omissions. |
| `PHEN_07` | **Clinical Negation** (*"denies"*, *"no"*, *"nahi hai"*) | 130 notes (52%) | 310 instances | All Specialties | Affirming a denied symptom introduces severe diagnostic error. |
| `PHEN_08` | **Clinical Uncertainty / Differentials** (*"suspected"*, *"rule out"*) | 85 notes (34%) | 160 instances | Emergency, Medicine | Differentiates confirmed diagnoses from provisional working diagnoses. |
| `PHEN_09` | **Temporality** (Active Presenting vs Historical Background) | 140 notes (56%) | 340 instances | Medicine, OBG, Surgery | Distinguishes acute issues requiring immediate care from stable chronic history. |
| `PHEN_10` | **Pending Actions & Care Goals** (Handover actionable tasks) | 165 notes (66%) | 290 plan items | All Specialties | ISBAR handover requires concrete actionable tasks for incoming shift. |
| `PHEN_11` | **Ambiguous Acronyms** (`OD`, `MS`, `PT`, `CA`) | 50 notes (20%) | 90 instances | Emergency, Medicine, Surgery | Disambiguation test: `OD` (once daily vs right eye vs overdose). |
| `PHEN_12` | **Open-Vocabulary / Unseen Entities** (Novel drugs, rare syndromes) | 65 notes (26%) | 110 instances | ICU, Medicine, Pediatrics | Evaluates contract preservation of previously uncatalogued clinical concepts. |
| `PHEN_13` | **Negative Controls & Linguistic Distractors** (*"acute ward"*, *"petition"*) | 45 notes (18%) | 75 distractors | All Specialties | Audits specificity; ensures administrative text does not trigger clinical entities. |
| `PHEN_14` | **Incomplete / Conflicting Information** (Vague notes, missing doses) | 55 notes (22%) | 95 instances | Emergency, Surgery | Tests system resilience: must record `null` rather than inventing clinical facts. |
| `PHEN_15` | **Standard Commonwealth English Baseline** | 40 notes (16%) | 120 instances | Medicine, Surgery | Backward compatibility verification against Australian 101 corpus baseline. |

---

## 4. Cross-Specialty Phenomena Density Matrix

The following heat matrix illustrates the expected concentration of phenomena across clinical departments (H = High, M = Moderate, L = Low):

```
+-----------------------------------+----+----+----+----+----+----+----+----+----+----+
| Phenomenon / Department           | MED| SUR| PED| OBG| EMG| ICU| DEV| VAL| TEST|
+-----------------------------------+----+----+----+----+----+----+----+----+----+----+
| Shorthand (K/C/O, S/B, C/O)       | H  | H  | M  | H  | H  | H  | 64 | 32 | 64 |
| Hinglish Phrases (chakkar, ulti)  | H  | M  | L  | M  | H  | L  | 32 | 16 | 32 |
| Decimal Dosages (0.25, 12.5 mg)   | M  | L  | H  | L  | M  | H  | 38 | 19 | 38 |
| Polypharmacy Cross-Talk (4+ meds) | H  | M  | L  | L  | M  | H  | 30 | 15 | 30 |
| Investigation Status Tracking     | H  | H  | M  | M  | H  | H  | 72 | 36 | 72 |
| Clinical Negation (No, Nahi hai)  | H  | H  | M  | M  | H  | H  | 52 | 26 | 52 |
| Clinical Uncertainty (Possible)   | M  | M  | M  | M  | H  | M  | 34 | 17 | 34 |
| Temporality (Historical K/C/O)    | H  | M  | L  | H  | M  | M  | 56 | 28 | 56 |
| Pending Handover Actions          | H  | H  | H  | H  | H  | H  | 66 | 33 | 66 |
| Ambiguous Acronyms (OD, MS)       | M  | M  | L  | M  | H  | M  | 20 | 10 | 20 |
| Open-Vocabulary / Unseen Terms    | M  | M  | M  | L  | M  | H  | 26 | 13 | 26 |
| Negative Controls (acute ward)    | M  | M  | L  | L  | M  | L  | 18 | 9  | 18 |
| Incomplete / Vague Notes          | M  | M  | L  | L  | H  | L  | 22 | 11 | 22 |
+-----------------------------------+----+----+----+----+----+----+----+----+----+----+
```

---

## 5. Minimum Quality & Adjudication Thresholds

Every note admitted to the final 250-note corpus must satisfy strict certification criteria:
1. **Double-Blind Clinical Annotation:** At least two independent qualified annotators (MBBS / MD / Clinical Nurse Informaticist) must annotate the note independently.
2. **Agreement Threshold:** Inter-rater agreement before adjudication must reach:
   - Span F1 $\ge 0.80$
   - Categorical Cohen's $\kappa \ge 0.85$ (Assertion, Temporality, Investigation Status)
   - Medication-attribute link agreement $F_{1,\text{link}} \ge 0.90$
3. **Adjudication Certification:** All span, category, and attribute discrepancies must be resolved and signed off by a Senior Clinical Adjudicator.
4. **Verbatim Offsets Guarantee:** 100% of entity character offsets must pass automated verification (`raw_text[start:end] == source_text`).
5. **No Synthetic Misrepresentation:** Any synthetic scaffolding note must be explicitly flagged with `"is_synthetic": true`. Real clinical notes must possess verified IRB/EC ethics authorization and complete Safe Harbor de-identification before inclusion.
