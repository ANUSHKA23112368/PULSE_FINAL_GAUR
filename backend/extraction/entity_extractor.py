"""
PULSE Clinical Entity Extractor
Defines the ClinicalEntityExtractor interface and provides a modular
HybridClinicalEntityExtractor combining clinical dictionaries, regular expressions,
clinical risk heuristics, and deduplicated semantic groupings.

Also includes an extensible BioClinicalBertEntityExtractor stub with TODO hooks
for future experimental integration of a fine-tuned transformer model.
"""

import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from backend.extraction.context_extractor import clinical_context_extractor
from backend.extraction.contract import ClinicalEntity, BaseClinicalExtractor, ExtractorRegistry

class ClinicalEntityExtractor(BaseClinicalExtractor):
    """
    Abstract Base Class for Clinical Entity Extraction, conforming to BaseClinicalExtractor.
    Future fine-tuned Bio_ClinicalBERT or SciSpacy models must implement this interface.
    """
    def __init__(self, name: str = "clinical_entity_extractor", version: str = "1.0.0", supports_open_vocabulary: bool = False):
        super().__init__(name=name, version=version, supports_open_vocabulary=supports_open_vocabulary)

    @abstractmethod
    def extract(self, text: str) -> Dict[str, Any]:
        pass


class BioClinicalBertEntityExtractor(ClinicalEntityExtractor):
    """
    Candidate Architecture Extension Point:
    Bio_ClinicalBERT (Alsentzer et al., 2019) Token Classification / NER pipeline.
    
    RESEARCH NOTE:
    Bio_ClinicalBERT is a proposed candidate backbone for PULSE. It has NOT yet
    been fine-tuned on the 101 nursing handover reference files.
    When fine-tuned checkpoints become available, this class can be initialized
    with the PyTorch/HuggingFace AutoModelForTokenClassification weights without
    changing any downstream API or frontend contracts.
    """
    def __init__(self, model_checkpoint: Optional[str] = None):
        self.model_checkpoint = model_checkpoint or "emilyalsentzer/Bio_ClinicalBERT"
        self.is_loaded = False
        # TODO: When fine-tuned weights are ready:
        # from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
        # self.tokenizer = AutoTokenizer.from_pretrained(self.model_checkpoint)
        # self.model = AutoModelForTokenClassification.from_pretrained(self.model_checkpoint)
        # self.ner_pipeline = pipeline("ner", model=self.model, tokenizer=self.tokenizer)
        # self.is_loaded = True

    def extract(self, text: str) -> Dict[str, Any]:
        raise NotImplementedError(
            "Bio_ClinicalBERT fine-tuning pipeline is planned for future experimental evaluation. "
            "Use HybridClinicalEntityExtractor for the working prototype."
        )


class HybridClinicalEntityExtractor(ClinicalEntityExtractor):
    """
    Production-grade hybrid clinical information extractor tailored for nursing handovers.
    Combines:
    1. Clinical dictionaries (conditions, symptoms, medications, procedures)
    2. Regular expressions for demographics, vitals, measurements, dosages
    3. Clinical Safety & Risk Alert identification (Fall Risk, Glycemic Alert, Cardiac Alert)
    4. Deduplication & clinical entity consolidation
    5. Clinical abbreviations catalog
    """

    def __init__(self):
        super().__init__(name="hybrid_rule", version="2.0.0", supports_open_vocabulary=True)
        self._init_dictionaries()

    def _init_dictionaries(self):
        # Clinical abbreviations with validated medical expansions
        self.abbreviations_map = {
            "BP": "Blood Pressure",
            "GCS": "Glasgow Coma Scale",
            "BGL": "Blood Glucose Level",
            "BGLS": "Blood Glucose Levels",
            "BSL": "Blood Sugar Level",
            "MRI": "Magnetic Resonance Imaging",
            "CT": "Computed Tomography",
            "ECG": "Electrocardiogram",
            "IV": "Intravenous",
            "PRN": "Pro Re Nata (As Needed)",
            "QID": "Quater In Die (Four Times Daily)",
            "BD": "Bis In Die (Twice Daily)",
            "TDS": "Ter Die Sumendum (Three Times Daily)",
            "AF": "Atrial Fibrillation",
            "COPD": "Chronic Obstructive Pulmonary Disease",
            "DM": "Diabetes Mellitus",
            "HPN": "Hypertension",
            "HTN": "Hypertension",
            "UTI": "Urinary Tract Infection",
            "MRSA": "Methicillin-Resistant Staphylococcus Aureus",
            "OBS": "Observations / Vital Signs",
            "CXR": "Chest X-Ray",
            "FBC": "Full Blood Count",
            "IDC": "Indwelling Catheter",
            "ADL": "Activities of Daily Living",
            "SOB": "Shortness of Breath",
            "PO": "Per Os (Orally)",
            "NOF": "Neck of Femur",
            "NBM": "Nil By Mouth",
            "CCF": "Congestive Cardiac Failure",
            "AMI": "Acute Myocardial Infarction",
            "TIA": "Transient Ischaemic Attack",
            "CVA": "Cerebrovascular Accident (Stroke)",
            "DVT": "Deep Vein Thrombosis",
            "PE": "Pulmonary Embolism",
            "OA": "Osteoarthritis",
            "RA": "Rheumatoid Arthritis",
            "TKR": "Total Knee Replacement",
            "THR": "Total Hip Replacement",
            "MET": "Medical Emergency Team",
            "K/C/O": "Known Case Of",
            "C/O": "Complaining Of",
            "S/B": "Seen By",
            "B/L": "Bilateral",
            "NAD": "No Abnormality Detected",
            "RBS": "Random Blood Sugar",
            "CBC": "Complete Blood Count",
            "USG": "Ultrasonography (Ultrasound)",
            "OPD": "Outpatient Department",
            "OHA": "Oral Hypoglycemic Agent",
            "OD": "Once Daily (Omni Die)",
            "BID": "Twice Daily (Bis In Die)",
            "TID": "Three Times Daily (Ter Die Sumendum)",
            "SOS": "As Needed (Si Opus Sit)",
            "HS": "At Bedtime (Hora Somni)",
            "STAT": "Immediately / Single Dose (Statim)"
        }

        # Medical Conditions
        self.condition_patterns = [
            (r"\b(?:type\s*1\s*dm|type\s*1\s*diabetes)\b", "Type 1 Diabetes Mellitus"),
            (r"\b(?:type\s*2\s*dm|type\s*2\s*diabetes)\b", "Type 2 Diabetes Mellitus"),
            (r"\b(?:diabetes\s*mellitus|diabetes)\b", "Diabetes Mellitus"),
            (r"\b(?:hpn|htn|hypertension|high\s*blood\s*pressure)\b", "Hypertension"),
            (r"\b(?:copd|chronic\s*obstructive\s*pulmonary\s*disease)\b", "Chronic Obstructive Pulmonary Disease"),
            (r"\b(?:asthma)\b", "Asthma"),
            (r"\b(?:stroke|cva|transient\s*ischaemic\s*attack|tia)\b", "Cerebrovascular Accident / Stroke"),
            (r"\b(?:bell['’]s\s*palsy|facial\s*palsy)\b", "Bell's Palsy (Facial Palsy)"),
            (r"\b(?:cataract|cataracts)\b", "Cataracts"),
            (r"\b(?:glaucoma)\b", "Glaucoma"),
            (r"\b(?:atrial\s*fibrillation|af)\b", "Atrial Fibrillation"),
            (r"\b(?:urinary\s*tract\s*infection|uti)\b", "Urinary Tract Infection"),
            (r"\b(?:mrsa)\b", "MRSA Colonization/Infection"),
            (r"\b(?:congestive\s*cardiac\s*failure|heart\s*failure|ccf)\b", "Congestive Cardiac Failure"),
            (r"\b(?:dementia|alzheimer['’]s)\b", "Dementia / Cognitive Impairment"),
            (r"\b(?:epilepsy|seizure\s*disorder)\b", "Epilepsy / Seizure Disorder"),
            (r"\b(?:osteoarthritis|rheumatoid\s*arthritis|arthritis|oa|ra)\b", "Arthritis"),
            (r"\b(?:parkinson['’]s|parkinsons)\b", "Parkinson's Disease"),
            (r"\b(?:pneumonia)\b", "Pneumonia"),
            (r"\b(?:cellulitis)\b", "Cellulitis"),
            (r"\b(?:angina)\b", "Angina Pectoris"),
            (r"\b(?:renal\s*failure|kidney\s*disease|ckd)\b", "Chronic Kidney Disease"),
            (r"\b(?:depression|anxiety|bipolar)\b", "Psychiatric History"),
            (r"\b(?:fracture|fractured\s*nof|broken\s*hip)\b", "Fracture"),
            (r"\b(?:infections?)\b", "Infection (Suspected / Documented)"),
            (r"\b(?:history\s*of\s*([a-zA-Z0-9\s]+?)(?:,|\.|\sand\s|\swith\s))", "Documented Medical History")
        ]

        # Symptoms
        self.symptom_patterns = [
            (r"\b(?:previous\s*chest\s*pains?|chest\s*pain[s]?)\b", "Chest Pain / Angina Symptoms"),
            (r"\b(?:headache[s]?)\b", "Headache (Cephalgia)"),
            (r"\b(?:vertigo)\b", "Vertigo (Vestibular)"),
            (r"\b(?:tinnitus)\b", "Tinnitus"),
            (r"\b(?:photophobia)\b", "Photophobia (Light Sensitivity)"),
            (r"\b(?:pain[s]?|abdominal\s*pain|back\s*pain|joint\s*pain)\b", "Pain"),
            (r"\b(?:nausea|vomiting|emesis)\b", "Nausea / Emesis"),
            (r"\b(?:dizziness|lightheadedness|dizzy)\b", "Dizziness / Presyncope"),
            (r"\b(?:shortness\s*of\s*breath|dyspnoea|dyspnea|sob)\b", "Dyspnea / Shortness of Breath"),
            (r"\b(?:weakness|lethargy|fatigue|malaise)\b", "Lethargy / Generalized Weakness"),
            (r"\b(?:fever|febrile|pyrexia|chills|rigors)\b", "Febrile Episode / Fever"),
            (r"\b(?:cough|productive\s*cough|sputum)\b", "Cough"),
            (r"\b(?:unsteady\s*(?:at\s*times)?|ataxia|unsteadiness|falls?|loss\s*of\s*balance)\b", "Gait Unsteadiness / Ataxia"),
            (r"\b(?:confusion|delirium|disorientated|disoriented)\b", "Acute Confusion / Delirium"),
            (r"\b(?:almost\s*blind|blind|impaired\s*vision|poor\s*vision)\b", "Severe Visual Impairment"),
            (r"\b(?:swelling|edema|oedema)\b", "Peripheral Edema")
        ]

        # Medications
        self.medication_patterns = [
            (r"\b(?:digoxin|lanoxin)\b", "Digoxin (Cardiac Glycoside)"),
            (r"\b(?:nitro|nitros|nitroglycerin|gtn|glyceryl\s*trinitrate)\b", "Glyceryl Trinitrate (GTN / Nitro)"),
            (r"\b(?:sliding\s*scale\s*insulin|variable\s*dose(?:\s*insulin)?|insulin|lantus|novorapid|actrapid|humalog)\b", "Insulin (Subcutaneous Regimen)"),
            (r"\b(?:antibiotic[s]?|ceftriaxone|augmentin|amoxicillin|flucloxacillin|gentamicin|tazocin)\b", "Antibiotic Therapy"),
            (r"\b(?:paracetamol|panadol|tylenol|acetaminophen)\b", "Paracetamol (Analgesia)"),
            (r"\b(?:morphine|endone|oxycodone|tramadol|codeine|fentanyl)\b", "Opioid Analgesic"),
            (r"\b(?:metoprolol|atenolol|bisoprolol|carvedilol)\b", "Beta-Adrenoreceptor Antagonist"),
            (r"\b(?:ramipril|perindopril|lisinopril|enalapril)\b", "ACE Inhibitor"),
            (r"\b(?:frusemide|furosemide|spironolactone)\b", "Loop Diuretic"),
            (r"\b(?:heparin|clexane|enoxaparin|warfarin|aspirin|plavix|clopidogrel)\b", "Anticoagulant / Antiplatelet"),
            (r"\b(?:ventolin|salbutamol|atrovent|ipratropium|seretide|symbicort)\b", "Inhaled Bronchodilator"),
            (r"\b(?:prednisone|prednisolone|dexamethasone)\b", "Systemic Corticosteroid"),
            (r"\b(?:statin|atorvastatin|rosuvastatin|simvastatin)\b", "HMG-CoA Reductase Inhibitor"),
            (r"\b(?:metformin|gliclazide|jardiance)\b", "Oral Hypoglycemic Agent"),
            (r"\b(?:ondansetron|maxolon|metoclopramide)\b", "Antiemetic Agent"),
            (r"\b(?:laxative[s]?|coloxyl|senna|movicol)\b", "Aperient / Bowel Management"),
            (r"\b(?:combiflam|ibuprofen|advil|brufen|nurofen)\b", "Combiflam (Ibuprofen / Paracetamol Analgesia)"),
            (r"\b(?:pain\s*killer[s]?|painkiller[s]?|pain\s*medication[s]?|(?:some\s+)?medicines?(?:\s+for\s+relief\s+of\s+pain)?|pain\s*relief\s*medicines?|medicines?\s+for\s+pain|analgesics?)\b", "Analgesic / Pain Killer"),
            (r"\b(?:calcium\s*(?:tablets?|supplements?|syrup)|vitamin\s*d[3]?\s*(?:tablets?|supplements?|capsules?|drops?)|calcium\s*(?:and|&)\s*vitamin\s*d\s*(?:tablets?|supplements?|capsules?|drops?)|multivitamin[s]?)\b", "Calcium & Vitamin D Supplements")
        ]

        # Investigations
        self.investigation_patterns = [
            (r"\b(?:test\s+(?:of|for)\s+(?:serum\s+)?calcium|calcium\s+test|calcium\s+level[s]?)\b", "Serum Calcium Test"),
            (r"\b(?:test\s+(?:of|for)\s+vitamin\s*d|vitamin\s*d\s*test|vitamin\s*d\s*level[s]?|\bvitamin\s*d\b)\b", "Vitamin D Test"),
            (r"\b(?:test\s+(?:of|for)\s+calcium\s+(?:and|&)\s+vitamin\s*d)\b", "Serum Calcium & Vitamin D Lab Panel"),
            (r"\b(?:renal\s*biopsy|biopsy)\b", "Renal Biopsy / Diagnostic Tissue Biopsy"),
            (r"\b(?:brain\s*mri|mri(?:\s*scan)?)\b", "Brain Magnetic Resonance Imaging (MRI)"),
            (r"\b(?:carotid\s*doppler|doppler\s*ultrasound|carotid\s*ultrasound)\b", "Carotid Doppler Ultrasound"),
            (r"\b(?:ct(?:\s*(?:head|brain|chest|abdomen|pelvis|scan))?|computed\s*tomography(?:\s*(?:head|brain|chest|abdomen|pelvis))?)\b", "Computed Tomography (CT Scan)"),
            (r"\b(?:ecg|electrocardiogram|telemetry|cardiac\s*monitor(?:ing)?)\b", "12-Lead ECG / Telemetry"),
            (r"\b(?:wbc|white\s*blood\s*(?:cells?|count))\b", "White Blood Cell Count (WBC)"),
            (r"\b(?:rbc|red\s*blood\s*(?:cells?|count))\b", "Red Blood Cell Count (RBC)"),
            (r"\b(?:platelets?|platelettes?)\b", "Platelet Count"),
            (r"\b(?:chest\s*x-?ray|cxr|x-?ray)\b", "Chest Radiography (CXR)"),
            (r"\b(?:bgl[s]?|blood\s*glucose|blood\s*sugar|bsl)\b", "Blood Glucose Monitoring (BGL)"),
            (r"\b(?:blood\s*test[s]?|pathology|fbc|cbc|complete\s*blood\s*count|full\s*blood\s*count|uec|lfts?|inr|troponin|blood\s*cultures?(?:\s*results?)?)\b", "Pathology / Blood Analysis"),
            (r"\b(?:urine\s*test|urinalysis|midstream\s*urine|msu)\b", "Urinalysis (MSU)"),
            (r"\b(?:ultrasound|uss|usg|ultrasonography)\b", "Ultrasound Sonography"),
            (r"\b(?:echo|echocardiogram)\b", "Transthoracic Echocardiogram"),
            (r"\b(?:angiogram|angiography)\b", "Coronary Angiogram")
        ]

        # Treatments
        self.treatment_patterns = [
            (r"\b(?:iv\s*antibiotics?|intravenous\s*antibiotics?|iv\s*infusion|iv\s*fluids?|iv\s*line|drip)\b", "Intravenous Infusion Therapy"),
            (r"\b(?:sliding\s*scale\s*insulin|variable\s*dose(?:\s*insulin)?)\b", "Sliding Scale Glycemic Protocol"),
            (r"\b(?:dressing|wound\s*dressing|wound\s*care|sutures?|clips?|vacuum\s*dressing|vac)\b", "Wound Management / Dressing"),
            (r"\b(?:oxygen(?:\s*therapy)?|o2(?:\s*via\s*nasal\s*prongs|\s*mask)?)\b", "Supplemental Oxygen Therapy"),
            (r"\b(?:catheter|idc|indwelling\s*catheter|catheterisation|catheterization)\b", "Indwelling Urinary Catheter Care"),
            (r"\b(?:physio(?:therapy)?|mobility\s*assistance|physiotherapist\s*review)\b", "Physiotherapy & Mobility Assistance"),
            (r"\b(?:needs\s*assistance|assistance\s*with\s*adls?|assistance|self\s*caring|ambulant)\b", "ADL & Ward Mobility Level"),
            (r"\b(?:dietitian\s*review|diabetic\s*educator|referral\s*to\s*[a-zA-Z\s]+)\b", "Specialist / Allied Health Referral"),
            (r"\b(?:monitoring|under\s*monitoring|neurological\s*observations?|neuro\s*obs)\b", "Clinical & Vital Sign Monitoring"),
            (r"\b(?:nebuliser|nebulizer|nebs|spacer)\b", "Nebulized Inhalation Therapy")
        ]

        # Measurements & Vital Signs
        self.measurement_patterns = [
            (r"\b(?:bp|blood\s*pressure)(?:\s*(?:is|was|of|recorded\s*as)?)?\s*(\d{2,3}\s*/\s*\d{2,3}(?:\s*mmhg)?|not\s*so\s*bad|high\s*normal(?:\s*range)?|stable|elevated|low|high)\b", "Blood Pressure"),
            (r"\b(?:gcs)(?:\s*(?:is|was|of)?)?\s*(\d{1,2}(?:\s*(?:pupils?\s*equal\s*and\s*reactive|pupils?\s*reactive|e\d+v\d+m\d+)?)?)\b", "Glasgow Coma Scale (GCS)"),
            (r"\b(?:obs|observations)(?:\s*(?:are|were)?)?\s*(stable|unstable|satisfactory|within\s*normal\s*limits)\b", "General Vital Observations"),
            (r"\b(?:pupils?\s*(?:are\s*)?equal\s*and\s*reactive)\b", "Pupillary Reflex"),
            (r"\b(?:hr|heart\s*rate|pulse)(?:\s*(?:is|was|of)?)?\s*(\d{2,3}(?:\s*bpm)?)\b", "Heart Rate"),
            (r"\b(?:temp|temperature)(?:\s*(?:is|was|of)?)?\s*(\d{2}(?:\.\d)?(?:\s*(?:c|degrees))?)\b", "Core Temperature"),
            (r"\b(?:sats|spo2|oxygen\s*saturation)(?:\s*(?:is|was|of)?)?\s*(\d{2,3}\s*%(?:\s*on\s*air|\s*on\s*oxygen)?)\b", "Pulse Oximetry (SpO2)"),
            (r"\b(?:bgl|bgls|rbs|random\s*blood\s*sugar|blood\s*glucose|blood\s*sugar|bsl)(?:\s*(?:trend\s*used\s*to\s*be|was|is|running)?)?\s*(high(?:\s*during\s*the\s*am)?|low|normal|\d+(\.\d+)?(?:\s*(?:mmol/l|mg/dl))?)\b", "Blood Glucose Value (BGL)")
        ]

    def _split_into_sentences(self, text: str) -> List[Tuple[str, int, int]]:
        return clinical_context_extractor.split_sentences_protected(text)

    def _find_source_sentence(self, match_start: int, sentence_spans: List[Tuple[str, int, int]]) -> str:
        for sent_text, s_start, s_end in sentence_spans:
            if s_start <= match_start <= s_end:
                return sent_text
        return sentence_spans[0][0] if sentence_spans else ""

    def extract(self, text: str) -> Dict[str, Any]:
        if not text:
            return {
                "patient_information": [],
                "conditions": [],
                "symptoms": [],
                "medications": [],
                "investigations": [],
                "treatments": [],
                "measurements": [],
                "abbreviations": [],
                "clinical_risks": [],
                "unclassified_candidates": [],
                "all_entities": []
            }

        sentence_spans = self._split_into_sentences(text)

        entities: Dict[str, Any] = {
            "patient_information": [],
            "conditions": [],
            "symptoms": [],
            "medications": [],
            "investigations": [],
            "treatments": [],
            "measurements": [],
            "abbreviations": [],
            "clinical_risks": [],
            "unclassified_candidates": [],
            "all_entities": []
        }

        # 1. Patient Information Extraction
        self._extract_patient_info(text, sentence_spans, entities["patient_information"])

        # 2. Medical Conditions Extraction (Consolidated & deduplicated)
        self._extract_pattern_category(text, sentence_spans, self.condition_patterns, "Condition", entities["conditions"])

        # 3. Symptoms Extraction (Consolidated & deduplicated)
        self._extract_pattern_category(text, sentence_spans, self.symptom_patterns, "Symptom", entities["symptoms"])

        # 3b. Hinglish Clinical Expression Mapping (Roman-Hindi symptoms)
        from backend.extraction.hinglish_mapper import clinical_hinglish_mapper
        existing_symptom_spans = {(s["start_char"], s["end_char"]) for s in entities["symptoms"] if "start_char" in s and "end_char" in s}
        hinglish_symptoms = clinical_hinglish_mapper.extract_hinglish_symptoms(text, sentence_spans)
        for hs in hinglish_symptoms:
            h_start = hs.source_start
            h_end = hs.source_end
            has_overlap = any(
                not (h_end <= s_start or h_start >= s_end)
                for s_start, s_end in existing_symptom_spans
            )
            if not has_overlap:
                entities["symptoms"].append(hs.to_dict())
                existing_symptom_spans.add((h_start, h_end))

        # 4. Medications Extraction
        self._extract_medications(text, sentence_spans, entities["medications"])

        # 5. Investigations Extraction
        self._extract_pattern_category(text, sentence_spans, self.investigation_patterns, "Investigation", entities["investigations"])

        # 6. Treatments Extraction
        self._extract_pattern_category(text, sentence_spans, self.treatment_patterns, "Treatment", entities["treatments"])

        # 7. Measurements & Vital Signs Extraction
        self._extract_measurements(text, sentence_spans, entities["measurements"])

        # 8. Clinical Abbreviations Catalog
        self._extract_abbreviations(text, sentence_spans, entities["abbreviations"])

        # 9. Open-Vocabulary Candidate Extraction & Unclassified Narrative Preservation
        from backend.extraction.open_vocabulary_extractor import open_vocabulary_extractor

        known_med_spans = {(m["start_char"], m["end_char"]) for m in entities["medications"] if "start_char" in m and "end_char" in m}
        candidate_meds = open_vocabulary_extractor.extract_candidate_medications(text, sentence_spans, known_med_spans)
        for cm in candidate_meds:
            entities["medications"].append(cm.to_dict())

        known_inv_spans = {(inv["start_char"], inv["end_char"]) for inv in entities["investigations"] if "start_char" in inv and "end_char" in inv}
        candidate_invs = open_vocabulary_extractor.extract_candidate_investigations(text, sentence_spans, known_inv_spans)
        for ci in candidate_invs:
            entities["investigations"].append(ci.to_dict())

        # Collect all matched spans across dictionary and candidate entities
        all_matched_spans = set()
        for cat_k in ["conditions", "symptoms", "medications", "investigations", "treatments", "measurements"]:
            for item in entities[cat_k]:
                st = item.get("start_char") or item.get("source_start")
                en = item.get("end_char") or item.get("source_end")
                if st is not None and en is not None:
                    all_matched_spans.add((st, en))

        # Capture unclassified candidate Hinglish complaints
        candidate_hinglish = clinical_hinglish_mapper.extract_unknown_hinglish_candidates(text, sentence_spans, existing_spans=all_matched_spans)
        for ch in candidate_hinglish:
            entities["unclassified_candidates"].append(ch.to_dict())

        unclassified = open_vocabulary_extractor.extract_unclassified_clauses(text, sentence_spans, all_matched_spans)
        entities["unclassified_candidates"].extend([u.to_dict() for u in unclassified])

        # 10. Standardize every entity record through ClinicalEntity contract
        all_standardized = []
        for cat_k in ["patient_information", "conditions", "symptoms", "medications", "investigations", "treatments", "measurements", "unclassified_candidates"]:
            standardized_list = []
            for item in entities[cat_k]:
                c_ent = ClinicalEntity.from_dict(item, default_method="deterministic_rule")
                c_dict = c_ent.to_dict()
                standardized_list.append(c_dict)
                all_standardized.append(c_dict)
            entities[cat_k] = standardized_list

        entities["all_entities"] = all_standardized

        # 11. Clinical Safety & Risk Alerts
        entities["clinical_risks"] = self._extract_clinical_risks(text, entities)

        return entities

    def _extract_patient_info(self, text: str, sentence_spans: List[Tuple[str, int, int]], output_list: List[Dict[str, Any]]):
        bed_match = re.search(r"\b(?:bed|room)\s+([a-zA-Z0-9]+)\b", text, re.IGNORECASE)
        if bed_match:
            output_list.append({
                "category": "Patient Information",
                "field": "Bed / Room",
                "value": bed_match.group(0),
                "detail": f"Bed {bed_match.group(1)}",
                "confidence": None,
                "confidence_type": "deterministic_rule",
                "raw_model_probability": None,
                "calibrated": False,
                "rule_source": "Bed Pattern Regular Expression",
                "matching_method": "Regex Pattern Matching",
                "source_sentence": self._find_source_sentence(bed_match.start(), sentence_spans),
                "start_char": bed_match.start(),
                "end_char": bed_match.end()
            })

        name_patterns = [
            r"(?:bed\s+[a-zA-Z0-9]+[\s,]+)([A-Z][a-zA-Z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-zA-Z]+)",
            r"^([A-Z][a-zA-Z]+(?:\s+[a-zA-Z]+){1,3})(?:[\s,]+(?:bed|\d+|under))",
            r"(?:patient\s+is\s+)([A-Z][a-zA-Z]+\s+[A-Z][a-zA-Z]+)"
        ]
        for pat in name_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                name_val = m.group(1).strip(", ")
                if name_val.lower() not in ["the patient", "he came", "she came", "this patient", "bed"]:
                    output_list.append({
                        "category": "Patient Information",
                        "field": "Patient Name",
                        "value": name_val,
                        "detail": name_val,
                        "confidence": None,
                        "confidence_type": "deterministic_rule",
                        "raw_model_probability": None,
                        "calibrated": False,
                        "rule_source": "Patient Name Pattern Matching",
                        "matching_method": "Named Entity Context Pattern",
                        "source_sentence": self._find_source_sentence(m.start(1), sentence_spans),
                        "start_char": m.start(1),
                        "end_char": m.end(1)
                    })
                    break

        age_patterns = [
            (r"\b(\d{1,3})\s*(?:years|yo|y\.?o\.?|years\s*old)\b", lambda m: f"{m.group(1)} years"),
            (r"\b(?:Forty-eight|Fifty|Sixty|Seventy|Eighty|Ninety|Twenty|Thirty)[-\s]?[a-zA-Z]*\s*years\b", lambda m: m.group(0)),
            (r",\s*(\d{1,3})\s*,\s*bed", lambda m: f"{m.group(1)} years"),
            (r"bed\s+\d+[\s,]+(\d{1,3})\s+under", lambda m: f"{m.group(1)} years")
        ]
        for pat, formatter in age_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                output_list.append({
                    "category": "Patient Information",
                    "field": "Age",
                    "value": formatter(m),
                    "detail": formatter(m),
                    "confidence": None,
                    "confidence_type": "deterministic_rule",
                    "raw_model_probability": None,
                    "calibrated": False,
                    "rule_source": "Age Regular Expression",
                    "matching_method": "Regex Pattern Matching",
                    "source_sentence": self._find_source_sentence(m.start(), sentence_spans),
                    "start_char": m.start(),
                    "end_char": m.end()
                })
                break

        gender_m = re.search(r"\b(he|his|him|she|her|hers|male|female)\b", text, re.IGNORECASE)
        if gender_m:
            token = gender_m.group(1).lower()
            gender_val = "Male" if token in ["he", "his", "him", "male"] else "Female"
            output_list.append({
                "category": "Patient Information",
                "field": "Gender / Sex",
                "value": gender_val,
                "detail": f"Verified via clinical pronoun/record ('{gender_m.group(1)}')",
                "confidence": None,
                "confidence_type": "deterministic_rule",
                "raw_model_probability": None,
                "calibrated": False,
                "rule_source": "Clinical Pronoun / Gender Lexicon",
                "matching_method": "Exact Lexical Match",
                "source_sentence": self._find_source_sentence(gender_m.start(), sentence_spans),
                "start_char": gender_m.start(),
                "end_char": gender_m.end()
            })

        doc_m = re.search(r"\b(?:under\s+|s\s*[\/\.]\s*b\s+|seen\s+by\s+)?(Dr\.?\s+[A-Z][a-zA-Z]+)\b", text, re.IGNORECASE)
        if doc_m:
            output_list.append({
                "category": "Patient Information",
                "field": "Attending Consultant",
                "value": doc_m.group(1),
                "detail": doc_m.group(1),
                "confidence": None,
                "confidence_type": "deterministic_rule",
                "raw_model_probability": None,
                "calibrated": False,
                "rule_source": "Consultant Title Pattern Matching",
                "matching_method": "Named Entity Context Pattern",
                "source_sentence": self._find_source_sentence(doc_m.start(1), sentence_spans),
                "start_char": doc_m.start(1),
                "end_char": doc_m.end(1)
            })

    def _determine_investigation_status(self, matched_text: str, start: int, end: int, source_sent: str, is_negated: bool) -> str:
        if is_negated:
            return "Not Ordered / Denied"

        s_lower = source_sent.lower()

        # 1. Awaiting Results (check before generic pending)
        if (
            re.search(r"\b(?:awaiting|waiting\s+for)\b.*?\b(?:results?|reports?|findings?)\b", s_lower)
            or re.search(r"\b(?:awaiting|waiting\s+for)\b", s_lower)
            or re.search(r"\b(?:results?|reports?|findings?)\s+(?:are\s+)?(?:awaited|pending)\b", s_lower)
        ):
            return "Awaiting Results"

        # 2. Sent / Specimen Collected (sent to lab, results not yet available)
        if re.search(r"\b(?:sent(?:\s+off|\s+to\s+lab|\s+for\s+testing)?|collected)\b", s_lower) and not re.search(r"\b(?:completed|returned|received)\b", s_lower):
            return "Sent"

        # 3. Completed (explicitly documented as completed/done/returned)
        if re.search(r"\b(?:completed|done|returned\s+from|came\s+back\s+from|had\s+a)\b", s_lower) and not re.search(r"\b(?:is\s+pending|pending|planned(?:\s+for)?|scheduled(?:\s+for)?|booked(?:\s+for)?)\b", s_lower):
            return "Completed"

        # 4. Pending / Scheduled / Ordered
        if re.search(r"\b(?:is\s+pending|pending|planned(?:\s+for)?|scheduled(?:\s+for)?|booked(?:\s+for)?|to\s+be\s+done|needs\s+another|ordered|order\s+test)\b", s_lower):
            return "Pending"

        # 5. Documented without explicit status
        return "Unspecified"

    def _extract_pattern_category(self, text: str, sentence_spans: List[Tuple[str, int, int]], patterns: List[Tuple[str, str]], category_label: str, output_list: List[Dict[str, Any]]):
        matched_dict = {}
        for pat, normalized_name in patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                span = (m.start(), m.end())
                matched_text = m.group(0).strip()
                source_sent = self._find_source_sentence(m.start(), sentence_spans)
                ctx = clinical_context_extractor.analyze_assertion(matched_text, m.start(), m.end(), text)

                inv_status = self._determine_investigation_status(matched_text, m.start(), m.end(), source_sent, ctx["is_negated"]) if category_label == "Investigation" else None

                # Key preserves assertion, temporality, and investigation status
                dedup_key = (normalized_name, ctx["assertion"], ctx["temporality"], inv_status) if category_label == "Investigation" else (normalized_name, ctx["assertion"], ctx["temporality"])
                if dedup_key not in matched_dict:
                    entity_record = {
                        "category": category_label,
                        "text": matched_text,
                        "normalized": normalized_name,
                        "assertion": ctx["assertion"],
                        "temporality": ctx["temporality"],
                        "is_negated": ctx["is_negated"],
                        "is_uncertain": ctx["is_uncertain"],
                        "is_historical": ctx["is_historical"],
                        "is_planned": ctx["is_planned"],
                        "context_cue": ctx["cue"],
                        "confidence": None,
                        "confidence_type": "deterministic_rule",
                        "raw_model_probability": None,
                        "calibrated": False,
                        "rule_source": f"PULSE {category_label} Lexicon & Context Scope",
                        "matching_method": "Clinical Lexicon & Regex Match",
                        "source_sentence": source_sent,
                        "start_char": m.start(),
                        "end_char": m.end(),
                        "all_spans": [span],
                        "occurrences": 1
                    }
                    if category_label == "Investigation":
                        entity_record["status"] = inv_status
                    matched_dict[dedup_key] = entity_record
                else:
                    matched_dict[dedup_key]["all_spans"].append(span)
                    matched_dict[dedup_key]["occurrences"] += 1

        for item in matched_dict.values():
            output_list.append(item)

    def _extract_medications(self, text: str, sentence_spans: List[Tuple[str, int, int]], output_list: List[Dict[str, Any]]):
        matched_meds = {}

        # 1. Collect all raw medication matches across text
        raw_matches = []
        for pat, norm in self.medication_patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                raw_matches.append({
                    "start": m.start(),
                    "end": m.end(),
                    "text": m.group(0).strip(),
                    "norm": norm
                })

        # Deduplicate overlapping matches by preserving longer spans
        raw_matches.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))
        filtered_matches = []
        for rm in raw_matches:
            if not any(rm["start"] >= sel["start"] and rm["end"] <= sel["end"] for sel in filtered_matches):
                filtered_matches.append(rm)

        # 2. Process matches within their local sentence and clause scope to prevent attribute leakage
        dosage_regex = re.compile(
            r"(?<!\w)(?:(?:\d+(?:\.\d+)?|\.\d+)\s*(?:mg|mcg|g|gm|grams?|ml|units?|puffs?|dosage|doses?)|variable\s*dose|sliding\s*scale|\d+\s+nitros?)\b",
            re.IGNORECASE
        )
        freq_regex = re.compile(r"\b(qid|bd|tds|prn|daily|mane|nocte|hourly)\b", re.IGNORECASE)
        route_regex = re.compile(r"\b(iv|oral|po|subcut|sc|topical|sublingual|inhal(?:er|ation))\b", re.IGNORECASE)
        clause_break_regex = re.compile(r"(?:;\s*|,\s*(?:and\s+)?|\s+and\s+|\s+then\s+|\s*\+\s*)", re.IGNORECASE)

        for sent_text, s_start, s_end in sentence_spans:
            sent_meds = [m for m in filtered_matches if s_start <= m["start"] < s_end]
            if not sent_meds:
                continue

            num_meds = len(sent_meds)
            for idx, med_info in enumerate(sent_meds):
                start, end = med_info["start"], med_info["end"]
                matched_med = med_info["text"]
                norm = med_info["norm"]
                rel_start = start - s_start
                rel_end = end - s_start

                # Determine localized clause boundaries
                if num_meds == 1:
                    local_scope = sent_text
                else:
                    # Left bound
                    if idx == 0:
                        left_idx = 0
                    else:
                        prev_rel_end = sent_meds[idx - 1]["end"] - s_start
                        between_prev = sent_text[prev_rel_end:rel_start]
                        delims = list(clause_break_regex.finditer(between_prev))
                        if delims:
                            left_idx = prev_rel_end + delims[-1].end()
                        else:
                            left_idx = prev_rel_end + (rel_start - prev_rel_end) // 2

                    # Right bound
                    if idx == num_meds - 1:
                        right_idx = len(sent_text)
                    else:
                        next_rel_start = sent_meds[idx + 1]["start"] - s_start
                        between_next = sent_text[rel_end:next_rel_start]
                        delim = clause_break_regex.search(between_next)
                        if delim:
                            right_idx = rel_end + delim.start()
                        else:
                            right_idx = rel_end + (next_rel_start - rel_end) // 2

                    local_scope = sent_text[left_idx:right_idx]

                ctx = clinical_context_extractor.analyze_assertion(matched_med, start, end, text)

                dosage_match = dosage_regex.search(local_scope)
                dosage = dosage_match.group(0) if dosage_match else "Unspecified dose in text"

                from backend.extraction.shorthand_normalizer import clinical_shorthand_normalizer
                freq_info = clinical_shorthand_normalizer.extract_medication_frequency(local_scope, text, start, end)
                if freq_info:
                    frequency = freq_info["canonical_token"]
                else:
                    freq_match = freq_regex.search(local_scope)
                    frequency = freq_match.group(0).upper() if freq_match else "Unspecified frequency"

                route_match = route_regex.search(local_scope)
                route = route_match.group(0).upper() if route_match else "Unspecified route"

                dedup_key = (norm, ctx["assertion"], ctx["temporality"])
                if dedup_key not in matched_meds:
                    matched_meds[dedup_key] = {
                        "category": "Medication",
                        "text": matched_med,
                        "normalized": norm,
                        "dosage": dosage,
                        "frequency": frequency,
                        "route": route,
                        "assertion": ctx["assertion"],
                        "temporality": ctx["temporality"],
                        "is_negated": ctx["is_negated"],
                        "is_uncertain": ctx["is_uncertain"],
                        "confidence": None,
                        "confidence_type": "deterministic_rule",
                        "raw_model_probability": None,
                        "calibrated": False,
                        "rule_source": "PULSE Medication Lexicon",
                        "matching_method": "Medication Lexicon Matching",
                        "source_sentence": sent_text,
                        "start_char": start,
                        "end_char": end,
                        "all_spans": [(start, end)],
                        "occurrences": 1
                    }
                else:
                    matched_meds[dedup_key]["all_spans"].append((start, end))
                    matched_meds[dedup_key]["occurrences"] += 1

        for item in matched_meds.values():
            output_list.append(item)

    def _extract_measurements(self, text: str, sentence_spans: List[Tuple[str, int, int]], output_list: List[Dict[str, Any]]):
        from backend.extraction.shorthand_normalizer import clinical_shorthand_normalizer

        seen_meas = set()

        # 1. Structured Glasgow Coma Scale (GCS) notation parser
        gcs_findings = clinical_shorthand_normalizer.parse_gcs(text, sentence_spans)
        for gcs in gcs_findings:
            key = (gcs["type"], gcs["text"].lower())
            seen_meas.add(key)
            output_list.append(gcs)

        # 2. General Measurement Patterns (skipping GCS if handled by structured parser)
        for pat, m_type in self.measurement_patterns:
            if m_type == "Glasgow Coma Scale (GCS)" and gcs_findings:
                continue
            for m in re.finditer(pat, text, re.IGNORECASE):
                matched = m.group(0).strip()
                key = (m_type, matched.lower())
                if key not in seen_meas:
                    seen_meas.add(key)
                    source_sent = self._find_source_sentence(m.start(), sentence_spans)
                    output_list.append({
                        "category": "Measurement",
                        "type": m_type,
                        "text": matched,
                        "confidence": None,
                        "confidence_type": "deterministic_rule",
                        "raw_model_probability": None,
                        "calibrated": False,
                        "rule_source": "Clinical Measurement Regex",
                        "matching_method": "Regex Pattern Matching",
                        "source_sentence": source_sent,
                        "start_char": m.start(),
                        "end_char": m.end()
                    })

    def _extract_abbreviations(self, text: str, sentence_spans: List[Tuple[str, int, int]], output_list: List[Dict[str, Any]]):
        from backend.extraction.shorthand_normalizer import clinical_shorthand_normalizer
        normalized_abbrs = clinical_shorthand_normalizer.normalize_abbreviations(text, sentence_spans)
        for item in normalized_abbrs:
            output_list.append(item)

    def _extract_clinical_risks(self, text: str, entities: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Synthesizes real-world clinical safety flags (Fall Risk, Glycemic Alert, Cardiac Alert, Neurological Alert).
        Requires affirmative, non-negated, current clinical findings.
        """
        risks = []
        lower = text.lower()

        # 1. Fall Risk: requires affirmative mobility or balance concern (and not negated)
        fall_risk_active = False
        for s in entities.get("symptoms", []):
            if s.get("normalized") in ["Gait Unsteadiness / Ataxia", "Severe Visual Impairment"] and not s.get("is_negated"):
                fall_risk_active = True
                break
        for trt in entities.get("treatments", []):
            if "assistance" in trt.get("text", "").lower() and not trt.get("is_negated"):
                fall_risk_active = True
                break
        if not fall_risk_active:
            m = re.search(r'\b(?:unsteady|ataxia|loss\s+of\s+balance)\b', lower)
            if m:
                ctx = clinical_context_extractor.analyze_assertion(m.group(0), m.start(), m.end(), text)
                if not ctx["is_negated"]:
                    fall_risk_active = True

        if fall_risk_active:
            risks.append({
                "risk_type": "Fall Risk Alert",
                "severity": "High",
                "rationale": "Patient documented with affirmative unsteadiness, transfer assistance requirement, or visual impairment.",
                "care_directive": "Ensure call bell within reach; assist during transfers; non-slip footwear."
            })

        # 2. Cardiovascular / Ischemic Alert:
        # MUST BE CURRENT AND AFFIRMATIVE! If chest pain is denied or historical, DO NOT FIRE!
        cardiac_active = False
        cardiac_rationale = ""
        for s in entities.get("symptoms", []):
            if s.get("normalized") == "Chest Pain / Angina Symptoms":
                if not s.get("is_negated") and not s.get("is_historical"):
                    cardiac_active = True
                    cardiac_rationale = "Active current chest pain or angina symptoms documented."
                    break
        if not cardiac_active:
            for c in entities.get("conditions", []):
                if c.get("normalized") in ["Angina Pectoris", "Cerebrovascular Accident / Stroke"] and not c.get("is_negated"):
                    cardiac_active = True
                    cardiac_rationale = f"Active documented {c.get('normalized')}."
                    break
        if not cardiac_active:
            for m in entities.get("medications", []):
                if "nitro" in m.get("normalized", "").lower() and "no effect" in lower:
                    cardiac_active = True
                    cardiac_rationale = "Nitroglycerin administration with refractory symptoms documented."
                    break

        if cardiac_active:
            risks.append({
                "risk_type": "Cardiovascular / Ischemic Alert",
                "severity": "High",
                "rationale": cardiac_rationale,
                "care_directive": "Continuous observation; notify medical team immediately if pain recurs; repeat 12-lead ECG."
            })

        # 3. Glycemic / Diabetic Alert:
        glycemic_active = False
        for med in entities.get("medications", []):
            if "insulin" in med.get("normalized", "").lower():
                glycemic_active = True
                break
        if not glycemic_active and any(term in lower for term in ["sliding scale", "bgl trend", "high during the am"]):
            glycemic_active = True

        if glycemic_active:
            risks.append({
                "risk_type": "Glycemic Management Alert",
                "severity": "Medium",
                "rationale": "Active insulin regimen with variable dosing or morning glycemic fluctuations.",
                "care_directive": "Pre-prandial BGL monitoring; clarify sliding scale dose with medical team prior to administration."
            })

        # 4. Neurological / Coma Alert:
        neuro_active = False
        for s in entities.get("symptoms", []):
            if s.get("normalized") in ["Headache (Cephalgia)", "Vertigo (Vestibular)", "Photophobia (Light Sensitivity)"] and not s.get("is_negated") and not s.get("is_historical"):
                neuro_active = True
                break
        if not neuro_active:
            for c in entities.get("conditions", []):
                if "bell's palsy" in c.get("normalized", "").lower() and not c.get("is_negated"):
                    neuro_active = True
                    break
        if not neuro_active and any(term in lower for term in ["gcs", "brain mri"]):
            neuro_active = True

        if neuro_active:
            risks.append({
                "risk_type": "Neurological Monitoring Alert",
                "severity": "Medium",
                "rationale": "Ongoing central nervous system or cranial nerve symptoms under active observation.",
                "care_directive": "Routine 4-hourly neuro observations; assess pupillary reaction and limb symmetry."
            })

        return risks

# Global singleton instance
clinical_entity_extractor = HybridClinicalEntityExtractor()
ExtractorRegistry.register("rule", clinical_entity_extractor)
ExtractorRegistry.register("hybrid", clinical_entity_extractor)
