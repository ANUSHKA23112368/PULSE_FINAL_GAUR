"""
PULSE Bio_ClinicalBERT Entity & Span Extractor
Provides deep-learning clinical named entity recognition using fine-tuned Bio_ClinicalBERT.
Harmonizes model predictions with PULSE clinical categories, exact character offsets,
and clinical assertion scoping (negation, temporality, and uncertainty).
"""

import os
import sys
import re
from typing import Dict, Any, List, Optional, Tuple
import torch
from transformers import BertTokenizerFast, AutoModelForTokenClassification

from backend.extraction.context_extractor import clinical_context_extractor

MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models", "clinical_bert"))

MACRO_CATEGORIES = [
    "Demographics_Bed",
    "Demographics_Name",
    "Demographics_Age",
    "Demographics_Gender",
    "Demographics_Doctor",
    "Clinical_Condition",
    "Clinical_Observation",
    "Medication",
    "Investigation_Procedure",
    "Plan_Goal",
    "Care_Activity"
]

LABEL_LIST = ["O"]
for cat in MACRO_CATEGORIES:
    LABEL_LIST.append(f"B-{cat}")
    LABEL_LIST.append(f"I-{cat}")

ID2LABEL = {i: l for i, l in enumerate(LABEL_LIST)}
LABEL2ID = {l: i for i, l in enumerate(LABEL_LIST)}

DISALLOWED_STOPWORDS = {
    "if", "and", "ad", "or", "to", "for", "in", "on", "at", "by", "with", "from",
    "of", "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "me", "my", "myself", "he", "she",
    "him", "her", "his", "it", "its", "they", "them", "their", "this", "that",
    "these", "those", "after", "before", "given", "give", "gives", "taking",
    "take", "takes", "told", "tell", "come", "meet", "dosage", "dose", "test",
    "testing", "tests", "day", "days", "week", "weeks", "some", "little", "bit",
    "relief", "temporal", "c"
}

KNOWN_INVESTIGATION_TERMS = {
    "wbc", "rbc", "platelet", "platelets", "platelettes", "ecg", "ekg",
    "ct", "ct scan", "mri", "mri scan", "x-ray", "cxr", "ultrasound",
    "biopsy", "blood test", "blood tests", "pathology", "fbc", "cbc",
    "urinalysis", "urine test", "echo", "echocardiogram", "troponin",
    "bgl", "blood glucose", "angiogram"
}

ANATOMICAL_LOCATIONS = {
    "brain", "head", "chest", "abdomen", "abdominal", "neck", "arm", "leg",
    "lung", "lungs", "heart", "kidney", "kidneys", "liver", "eye", "eyes", "ear", "ears"
}


class ClinicalBERTExtractor:
    """
    Neural clinical entity extraction engine using fine-tuned Bio_ClinicalBERT.
    Provides subword alignment, span decoding, and assertion scoping.
    """
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or MODEL_DIR
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = None
        self.model = None
        self._is_loaded = False
        self._load_model()

    def _load_model(self):
        try:
            if os.path.exists(self.model_path) and os.path.exists(os.path.join(self.model_path, "config.json")):
                self.tokenizer = BertTokenizerFast.from_pretrained(self.model_path)
                self.model = AutoModelForTokenClassification.from_pretrained(self.model_path).to(self.device)
                self.model.eval()
                self._is_loaded = True
            else:
                self._is_loaded = False
        except Exception as e:
            print(f"Notice: ClinicalBERTExtractor could not load local weights: {e}")
            self._is_loaded = False

    def is_available(self) -> bool:
        return self._is_loaded

    def reload(self):
        self._load_model()

    def extract_spans(self, text: str) -> List[Dict[str, Any]]:
        """
        Runs Bio_ClinicalBERT forward pass and reconstructs character-level entity spans.
        """
        if not self._is_loaded or not text.strip():
            return []

        encoding = self.tokenizer(
            text,
            return_offsets_mapping=True,
            truncation=True,
            max_length=256,
            return_tensors="pt"
        )

        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)
        offset_mapping = encoding["offset_mapping"].squeeze(0).cpu().numpy()

        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits.squeeze(0)
            probs = torch.softmax(logits, dim=-1).cpu().numpy()
            preds = torch.argmax(logits, dim=-1).cpu().numpy()

        spans = []
        current_span = None

        for idx, (sub_start, sub_end) in enumerate(offset_mapping):
            sub_start, sub_end = int(sub_start), int(sub_end)
            if sub_start == 0 and sub_end == 0:
                continue

            pred_id = int(preds[idx])
            pred_label = ID2LABEL.get(pred_id, "O")
            token_prob = float(probs[idx][pred_id])

            # Check if this token is in the middle of an alphanumeric word (subword continuation)
            is_word_continuation = (sub_start > 0 and text[sub_start - 1].isalnum() and text[sub_start].isalnum())

            if is_word_continuation and current_span is not None:
                # Part of the same word that started the span — continue the span regardless of subword label
                current_span["end_char"] = sub_end
                current_span["text"] = text[current_span["start_char"]:sub_end]
                current_span["token_probs"].append(token_prob)
                continue

            if pred_label.startswith("B-") or (pred_label.startswith("I-") and (current_span is None or current_span["category"] != pred_label[2:])):
                if current_span:
                    spans.append(current_span)
                cat = pred_label[2:]

                # Snap start backward to whole word start if starting in middle of alphanumeric token
                span_start = sub_start
                while span_start > 0 and text[span_start - 1].isalnum():
                    span_start -= 1

                # Snap end forward to whole word end
                span_end = sub_end
                while span_end < len(text) and text[span_end].isalnum():
                    span_end += 1

                current_span = {
                    "category": cat,
                    "start_char": span_start,
                    "end_char": span_end,
                    "text": text[span_start:span_end],
                    "token_probs": [token_prob]
                }
            elif pred_label.startswith("I-"):
                cat = pred_label[2:]
                if current_span and current_span["category"] == cat:
                    current_span["end_char"] = sub_end
                    while current_span["end_char"] < len(text) and text[current_span["end_char"]].isalnum():
                        current_span["end_char"] += 1
                    current_span["text"] = text[current_span["start_char"]:current_span["end_char"]]
                    current_span["token_probs"].append(token_prob)
            else:
                if current_span:
                    spans.append(current_span)
                    current_span = None

        if current_span:
            spans.append(current_span)

        # Post-clean spans: strip leading/trailing punctuation or whitespace, filter stopwords
        cleaned_spans = []
        for sp in spans:
            raw_span_text = sp["text"]
            stripped = raw_span_text.strip(" ,.;:!?\n\t")
            if not stripped:
                continue

            # Snap to word boundaries
            offset_left = raw_span_text.find(stripped)
            new_start = sp["start_char"] + offset_left
            new_end = new_start + len(stripped)
            while new_start > 0 and text[new_start - 1].isalnum():
                new_start -= 1
            while new_end < len(text) and text[new_end].isalnum():
                new_end += 1

            word_text = text[new_start:new_end].strip(" ,.;:!?\n\t")
            if not word_text:
                continue

            word_lower = word_text.lower()
            # Drop single letters and disallowed English stopwords/fragments
            if word_lower in DISALLOWED_STOPWORDS or len(word_text) <= 1:
                continue

            sp["start_char"] = new_start
            sp["end_char"] = new_end
            sp["text"] = word_text

            # Reclassify known investigation terms that BERT might classify as Observation
            if word_lower in KNOWN_INVESTIGATION_TERMS or re.search(r"\b(?:test\s+for|for\s+test)\s+" + re.escape(word_lower), text.lower()):
                sp["category"] = "Investigation_Procedure"

            # Reclassify known medication terms
            if word_lower in {"combiflam", "ibuprofen", "advil", "paracetamol", "panadol", "tylenol"}:
                sp["category"] = "Medication"

            if sp.get("token_probs"):
                sp["raw_model_probability"] = round(float(sum(sp["token_probs"]) / len(sp["token_probs"])), 4)
            else:
                sp["raw_model_probability"] = None
            cleaned_spans.append(sp)

        # Deduplicate overlapping spans (keep the longer span or prioritized category)
        final_spans = []
        for s in cleaned_spans:
            duplicate = False
            for existing in final_spans:
                if (existing["start_char"] <= s["start_char"] and existing["end_char"] >= s["end_char"]) or \
                   (s["start_char"] <= existing["start_char"] and s["end_char"] >= existing["end_char"]):
                    if len(s["text"]) > len(existing["text"]):
                        existing["start_char"] = s["start_char"]
                        existing["end_char"] = s["end_char"]
                        existing["text"] = s["text"]
                        existing["category"] = s["category"]
                        existing["raw_model_probability"] = s["raw_model_probability"]
                    duplicate = True
                    break
            if not duplicate:
                final_spans.append(s)

        return final_spans

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Maps raw neural spans into structured PULSE categories with assertion analysis.
        """
        from backend.extraction.entity_extractor import clinical_entity_extractor

        if not self._is_loaded:
            # Clean fallback to hybrid rule extractor if weights are not ready
            return clinical_entity_extractor.extract(text)

        spans = self.extract_spans(text)
        sentence_spans = clinical_context_extractor.split_sentences_protected(text)

        def find_sent(s_pos: int) -> str:
            for s_txt, s_st, s_en in sentence_spans:
                if s_st <= s_pos <= s_en:
                    return s_txt
            return sentence_spans[0][0] if sentence_spans else ""

        entities: Dict[str, Any] = {
            "patient_information": [],
            "conditions": [],
            "symptoms": [],
            "medications": [],
            "investigations": [],
            "treatments": [],
            "measurements": [],
            "abbreviations": [],
            "clinical_risks": []
        }

        # Deduplication maps
        cond_map = {}
        symp_map = {}
        med_map = {}
        inv_map = {}
        trt_map = {}

        for sp in spans:
            cat = sp["category"]
            span_text = sp["text"]
            st = sp["start_char"]
            en = sp["end_char"]
            span_prob = sp.get("raw_model_probability")
            src_sent = find_sent(st)

            ctx = clinical_context_extractor.analyze_assertion(span_text, st, en, text)

            if cat == "Demographics_Bed":
                entities["patient_information"].append({
                    "category": "Patient Information",
                    "field": "Bed / Room",
                    "value": span_text,
                    "detail": f"Bed {span_text}",
                    "confidence": None,
                    "confidence_type": "uncalibrated_raw_probability",
                    "raw_model_probability": span_prob,
                    "calibrated": False,
                    "extraction_method": "Bio_ClinicalBERT Token Classification (Uncalibrated Softmax)",
                    "source_sentence": src_sent,
                    "start_char": st,
                    "end_char": en
                })
            elif cat == "Demographics_Name":
                entities["patient_information"].append({
                    "category": "Patient Information",
                    "field": "Patient Name",
                    "value": span_text,
                    "detail": span_text,
                    "confidence": None,
                    "confidence_type": "uncalibrated_raw_probability",
                    "raw_model_probability": span_prob,
                    "calibrated": False,
                    "extraction_method": "Bio_ClinicalBERT Token Classification (Uncalibrated Softmax)",
                    "source_sentence": src_sent,
                    "start_char": st,
                    "end_char": en
                })
            elif cat == "Demographics_Age":
                entities["patient_information"].append({
                    "category": "Patient Information",
                    "field": "Age",
                    "value": span_text,
                    "detail": span_text,
                    "confidence": None,
                    "confidence_type": "uncalibrated_raw_probability",
                    "raw_model_probability": span_prob,
                    "calibrated": False,
                    "extraction_method": "Bio_ClinicalBERT Token Classification (Uncalibrated Softmax)",
                    "source_sentence": src_sent,
                    "start_char": st,
                    "end_char": en
                })
            elif cat == "Demographics_Gender":
                entities["patient_information"].append({
                    "category": "Patient Information",
                    "field": "Gender / Sex",
                    "value": "Male" if span_text.lower() in ["he", "his", "him", "male"] else "Female",
                    "detail": span_text,
                    "confidence": None,
                    "confidence_type": "uncalibrated_raw_probability",
                    "raw_model_probability": span_prob,
                    "calibrated": False,
                    "extraction_method": "Bio_ClinicalBERT Token Classification (Uncalibrated Softmax)",
                    "source_sentence": src_sent,
                    "start_char": st,
                    "end_char": en
                })
            elif cat == "Demographics_Doctor":
                entities["patient_information"].append({
                    "category": "Patient Information",
                    "field": "Attending Consultant",
                    "value": span_text,
                    "detail": span_text,
                    "confidence": None,
                    "confidence_type": "uncalibrated_raw_probability",
                    "raw_model_probability": span_prob,
                    "calibrated": False,
                    "extraction_method": "Bio_ClinicalBERT Token Classification (Uncalibrated Softmax)",
                    "source_sentence": src_sent,
                    "start_char": st,
                    "end_char": en
                })
            elif cat == "Clinical_Condition":
                key = (span_text.lower(), ctx["assertion"], ctx["temporality"])
                if key not in cond_map:
                    cond_map[key] = {
                        "category": "Condition",
                        "text": span_text,
                        "normalized": span_text.title(),
                        "assertion": ctx["assertion"],
                        "temporality": ctx["temporality"],
                        "is_negated": ctx["is_negated"],
                        "is_uncertain": ctx["is_uncertain"],
                        "is_historical": ctx["is_historical"],
                        "is_planned": ctx["is_planned"],
                        "context_cue": ctx["cue"],
                        "confidence": None,
                        "confidence_type": "uncalibrated_raw_probability",
                        "raw_model_probability": span_prob,
                        "calibrated": False,
                        "extraction_method": "Bio_ClinicalBERT Token Classification (Uncalibrated Softmax)",
                        "source_sentence": src_sent,
                        "start_char": st,
                        "end_char": en,
                        "all_spans": [(st, en)],
                        "occurrences": 1
                    }
                else:
                    cond_map[key]["occurrences"] += 1
            elif cat == "Clinical_Observation":
                key = (span_text.lower(), ctx["assertion"], ctx["temporality"])
                if key not in symp_map:
                    symp_map[key] = {
                        "category": "Symptom",
                        "text": span_text,
                        "normalized": span_text.title(),
                        "assertion": ctx["assertion"],
                        "temporality": ctx["temporality"],
                        "is_negated": ctx["is_negated"],
                        "is_uncertain": ctx["is_uncertain"],
                        "is_historical": ctx["is_historical"],
                        "is_planned": ctx["is_planned"],
                        "context_cue": ctx["cue"],
                        "confidence": None,
                        "confidence_type": "uncalibrated_raw_probability",
                        "raw_model_probability": span_prob,
                        "calibrated": False,
                        "extraction_method": "Bio_ClinicalBERT Token Classification (Uncalibrated Softmax)",
                        "source_sentence": src_sent,
                        "start_char": st,
                        "end_char": en,
                        "all_spans": [(st, en)],
                        "occurrences": 1
                    }
                else:
                    symp_map[key]["occurrences"] += 1
            elif cat == "Medication":
                key = (span_text.lower(), ctx["assertion"], ctx["temporality"])
                if key not in med_map:
                    dose_m = re.search(r"\b(\d+\s*(?:mg|mcg|ml|units?|puffs?|dosage|doses?)|variable\s*dose|sliding\s*scale|\d+\s+nitros?)\b", src_sent, re.IGNORECASE)
                    freq_m = re.search(r"\b(qid|bd|tds|prn|daily|mane|nocte|hourly)\b", src_sent, re.IGNORECASE)
                    route_m = re.search(r"\b(iv|oral|po|subcut|sc|topical|sublingual|inhal(?:er|ation))\b", src_sent, re.IGNORECASE)
                    med_map[key] = {
                        "category": "Medication",
                        "text": span_text,
                        "normalized": span_text.title(),
                        "dosage": dose_m.group(0) if dose_m else "Unspecified dose in text",
                        "frequency": freq_m.group(0).upper() if freq_m else "Unspecified frequency",
                        "route": route_m.group(0).upper() if route_m else "Unspecified route",
                        "assertion": ctx["assertion"],
                        "temporality": ctx["temporality"],
                        "is_negated": ctx["is_negated"],
                        "is_uncertain": ctx["is_uncertain"],
                        "confidence": None,
                        "confidence_type": "uncalibrated_raw_probability",
                        "raw_model_probability": span_prob,
                        "calibrated": False,
                        "extraction_method": "Bio_ClinicalBERT Token Classification (Uncalibrated Softmax)",
                        "source_sentence": src_sent,
                        "start_char": st,
                        "end_char": en,
                        "all_spans": [(st, en)],
                        "occurrences": 1
                    }
                else:
                    med_map[key]["occurrences"] += 1
            elif cat == "Investigation_Procedure":
                key = (span_text.lower(), ctx["assertion"], ctx["temporality"])
                if key not in inv_map:
                    inv_map[key] = {
                        "category": "Investigation",
                        "text": span_text,
                        "normalized": span_text.title(),
                        "assertion": ctx["assertion"],
                        "temporality": ctx["temporality"],
                        "is_negated": ctx["is_negated"],
                        "is_uncertain": ctx["is_uncertain"],
                        "is_planned": ctx["is_planned"],
                        "confidence": None,
                        "confidence_type": "uncalibrated_raw_probability",
                        "raw_model_probability": span_prob,
                        "calibrated": False,
                        "extraction_method": "Bio_ClinicalBERT Token Classification (Uncalibrated Softmax)",
                        "source_sentence": src_sent,
                        "start_char": st,
                        "end_char": en,
                        "all_spans": [(st, en)],
                        "occurrences": 1
                    }
                else:
                    inv_map[key]["occurrences"] += 1
            elif cat in ["Care_Activity", "Plan_Goal"]:
                key = (span_text.lower(), ctx["assertion"], ctx["temporality"])
                if key not in trt_map:
                    trt_map[key] = {
                        "category": "Treatment",
                        "text": span_text,
                        "normalized": span_text.title(),
                        "assertion": ctx["assertion"],
                        "temporality": ctx["temporality"],
                        "is_negated": ctx["is_negated"],
                        "confidence": None,
                        "confidence_type": "uncalibrated_raw_probability",
                        "raw_model_probability": span_prob,
                        "calibrated": False,
                        "extraction_method": "Bio_ClinicalBERT Token Classification (Uncalibrated Softmax)",
                        "source_sentence": src_sent,
                        "start_char": st,
                        "end_char": en,
                        "all_spans": [(st, en)],
                        "occurrences": 1
                    }
                else:
                    trt_map[key]["occurrences"] += 1

        entities["conditions"] = list(cond_map.values())
        entities["symptoms"] = list(symp_map.values())
        entities["medications"] = list(med_map.values())
        entities["investigations"] = list(inv_map.values())
        entities["treatments"] = list(trt_map.values())

        # Hybrid integration: Merge high-precision rule-based investigations and medications
        rule_entities = clinical_entity_extractor.extract(text)

        # Merge investigations
        existing_inv_texts = {inv["text"].lower() for inv in entities["investigations"]}
        for r_inv in rule_entities.get("investigations", []):
            if r_inv["text"].lower() not in existing_inv_texts:
                entities["investigations"].append(r_inv)
                existing_inv_texts.add(r_inv["text"].lower())

        # Purge any investigation or anatomical site that was misclassified as a symptom or condition
        def _is_investigation_entity(text_str: str) -> bool:
            tl = text_str.lower()
            if tl in existing_inv_texts or tl in KNOWN_INVESTIGATION_TERMS:
                return True
            words = set(re.findall(r"[a-zA-Z]+", tl))
            if any(term in words for term in KNOWN_INVESTIGATION_TERMS) or any(inv in words for inv in existing_inv_texts):
                return True
            return False

        entities["symptoms"] = [
            s for s in entities["symptoms"]
            if not _is_investigation_entity(s["text"]) and s["text"].lower().strip() not in ANATOMICAL_LOCATIONS
        ]
        entities["conditions"] = [
            c for c in entities["conditions"]
            if not _is_investigation_entity(c["text"]) and c["text"].lower().strip() not in ANATOMICAL_LOCATIONS
        ]

        # Merge medications
        existing_med_texts = {m["text"].lower() for m in entities["medications"]}
        for r_med in rule_entities.get("medications", []):
            if r_med["text"].lower() not in existing_med_texts:
                entities["medications"].append(r_med)
                existing_med_texts.add(r_med["text"].lower())

        # Purge medications from treatments or symptoms
        entities["treatments"] = [
            t for t in entities["treatments"]
            if t["text"].lower() not in existing_med_texts
        ]
        entities["symptoms"] = [
            s for s in entities["symptoms"]
            if s["text"].lower() not in existing_med_texts
        ]

        # Also merge rule conditions and symptoms if not already detected
        existing_cond_texts = {c["text"].lower() for c in entities["conditions"]}
        for r_cond in rule_entities.get("conditions", []):
            if r_cond["text"].lower() not in existing_cond_texts and r_cond["text"].lower() not in existing_inv_texts:
                entities["conditions"].append(r_cond)
                existing_cond_texts.add(r_cond["text"].lower())

        existing_symp_texts = {s["text"].lower() for s in entities["symptoms"]}
        for r_symp in rule_entities.get("symptoms", []):
            if r_symp["text"].lower() not in existing_symp_texts and r_symp["text"].lower() not in existing_inv_texts and r_symp["text"].lower() not in existing_med_texts:
                entities["symptoms"].append(r_symp)
                existing_symp_texts.add(r_symp["text"].lower())

        # Also run measurement regexes to ensure vitals (BP, GCS, BGL) are captured accurately
        clinical_entity_extractor._extract_measurements(text, sentence_spans, entities["measurements"])
        clinical_entity_extractor._extract_abbreviations(text, sentence_spans, entities["abbreviations"])

        # Compute clinical risks safely
        entities["clinical_risks"] = clinical_entity_extractor._extract_clinical_risks(text, entities)

        return entities


# Global singleton instance
clinical_bert_extractor = ClinicalBERTExtractor()
