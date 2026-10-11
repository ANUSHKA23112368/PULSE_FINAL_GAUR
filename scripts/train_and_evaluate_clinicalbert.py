"""
PULSE Phase C: Bio_ClinicalBERT Fine-Tuning & 5-Fold Cross-Validation Evaluation Harness
Trains and evaluates emilyalsentzer/Bio_ClinicalBERT on the adjudicated gold standard clinical corpus.
Computes strict and lenient span-level Precision, Recall, and F1 across all 5 cross-validation folds.
Saves the fine-tuned model checkpoint for PULSE backend deployment and exports benchmark results.
"""

import os
import sys
import json
import time
import re
from collections import defaultdict
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    BertTokenizerFast,
    AutoModelForTokenClassification,
    get_linear_schedule_with_warmup
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

CORPUS_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "gold_standard_corpus.json")
SPLITS_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "train_test_splits.json")
BASELINE_RESULTS_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "baseline_evaluation_results.json")
OUTPUT_RESULTS_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "clinicalbert_evaluation_results.json")
MODEL_OUTPUT_DIR = os.path.join(BASE_DIR, "backend", "models", "clinical_bert")

MODEL_CHECKPOINT = "emilyalsentzer/Bio_ClinicalBERT"

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

CATEGORY_MAP = {
    # Bed
    "PatientIntroduction_CurrentBed": "Demographics_Bed",
    "PatientIntroduction_CurrentRoom": "Demographics_Bed",
    # Name
    "PatientIntroduction_GivenNames/Initials": "Demographics_Name",
    "PatientIntroduction_Lastname": "Demographics_Name",
    # Age
    "PatientIntroduction_Ageinyears": "Demographics_Age",
    # Gender
    "PatientIntroduction_Gender": "Demographics_Gender",
    # Consultant
    "PatientIntroduction_UnderDr_Lastname": "Demographics_Doctor",
    "PatientIntroduction_UnderDr_GivenNames/Initials": "Demographics_Doctor",
    "Appointment/Procedure_ClinicianLastname": "Demographics_Doctor",
    "Appointment/Procedure_ClinicianGivenNames/Initials": "Demographics_Doctor",
    # Conditions / History
    "PatientIntroduction_AdmissionReason/Diagnosis": "Clinical_Condition",
    "PatientIntroduction_Disease/ProblemHistory": "Clinical_Condition",
    "PatientIntroduction_ChronicCondition": "Clinical_Condition",
    # Symptoms / Observations
    "MyShift_Status": "Clinical_Observation",
    "MyShift_OtherObservation": "Clinical_Observation",
    "MyShift_Wounds/Skin": "Clinical_Observation",
    "MyShift_Output/Diuresis/BowelMovement": "Clinical_Observation",
    "MyShift_Input/Diet": "Clinical_Observation",
    "Future_Alert/Warning/AbnormalResult": "Clinical_Observation",
    # Medications
    "Medication_Medicine": "Medication",
    "Medication_Dosage": "Medication",
    "Medication_Status": "Medication",
    # Procedures / Investigations
    "Appointment/Procedure_Description": "Investigation_Procedure",
    "Appointment/Procedure_Status": "Investigation_Procedure",
    "Appointment/Procedure_Day": "Investigation_Procedure",
    "Appointment/Procedure_Time": "Investigation_Procedure",
    "Appointment/Procedure_City": "Investigation_Procedure",
    "Appointment/Procedure_Ward": "Investigation_Procedure",
    # Plans / Goals
    "Future_Goal/TaskToBeCompleted/ExpectedOutcome": "Plan_Goal",
    "Future_Discharge/TransferPlan": "Plan_Goal",
    "PatientIntroduction_CarePlan": "Plan_Goal",
    "PatientIntroduction_Allergy": "Plan_Goal",
    "MyShift_RiskManagement": "Plan_Goal",
    # Care / Activities
    "MyShift_ActivitiesOfDailyLiving": "Care_Activity",
    "MyShift_Contraption": "Care_Activity"
}

LABEL_LIST = ["O"]
for cat in MACRO_CATEGORIES:
    LABEL_LIST.append(f"B-{cat}")
    LABEL_LIST.append(f"I-{cat}")

ID2LABEL = {i: l for i, l in enumerate(LABEL_LIST)}
LABEL2ID = {l: i for i, l in enumerate(LABEL_LIST)}


def map_raw_label(raw_label: str) -> str:
    clean_l = raw_label.replace("B-", "").replace("I-", "")
    return CATEGORY_MAP.get(clean_l, "Other")


class NursingHandoverDataset(Dataset):
    """
    Tokenizes raw handover notes using Bio_ClinicalBERT tokenizer,
    aligning subwords with gold entity spans via character offsets.
    """
    def __init__(self, reports, doc_ids, tokenizer, max_length=256):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.samples = []

        for r_id in doc_ids:
            doc = reports[r_id]
            raw_text = doc["raw_text"]

            # Standardized gold entity spans
            gold_spans = []
            for sp in doc.get("entity_spans", []):
                h_cat = map_raw_label(sp["label"])
                if h_cat in MACRO_CATEGORIES and sp["start_char"] < sp["end_char"]:
                    gold_spans.append({
                        "start_char": sp["start_char"],
                        "end_char": sp["end_char"],
                        "category": h_cat
                    })

            # Tokenize with exact character offset mapping (unpadded for dynamic batch collation)
            encoding = tokenizer(
                raw_text,
                return_offsets_mapping=True,
                truncation=True,
                max_length=max_length,
                return_tensors="pt"
            )

            input_ids = encoding["input_ids"].squeeze(0)
            attention_mask = encoding["attention_mask"].squeeze(0)
            offset_mapping = encoding["offset_mapping"].squeeze(0)
            seq_len = input_ids.shape[0]

            # Assign labels to subwords
            labels = torch.full((seq_len,), -100, dtype=torch.long)
            current_entity = None

            for idx, (sub_start, sub_end) in enumerate(offset_mapping):
                sub_start, sub_end = int(sub_start), int(sub_end)
                if sub_start == 0 and sub_end == 0:
                    # Special tokens ([CLS], [SEP], [PAD])
                    labels[idx] = -100
                    continue

                # Find matching gold span
                matched_span = None
                for sp in gold_spans:
                    if sp["start_char"] <= sub_start < sp["end_char"]:
                        matched_span = sp
                        break

                if matched_span:
                    cat = matched_span["category"]
                    if sub_start == matched_span["start_char"]:
                        label_str = f"B-{cat}"
                    else:
                        label_str = f"I-{cat}"
                    labels[idx] = LABEL2ID.get(label_str, LABEL2ID["O"])
                else:
                    labels[idx] = LABEL2ID["O"]

            self.samples.append({
                "report_id": r_id,
                "raw_text": raw_text,
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "offset_mapping": offset_mapping,
                "labels": labels,
                "gold_spans": gold_spans
            })

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx]


def compute_span_eval(gold_spans, pred_spans):
    """
    Computes strict and lenient span-level precision, recall, and F1.
    Strict: exact start_char, exact end_char, and exact label.
    Lenient: overlapping characters and exact label.
    """
    strict_tp = 0
    strict_fp = 0
    gold_matched_strict = set()

    for pred in pred_spans:
        matched = False
        for g_idx, gold in enumerate(gold_spans):
            if g_idx not in gold_matched_strict:
                if pred["label"] == gold["label"] and pred["start_char"] == gold["start_char"] and pred["end_char"] == gold["end_char"]:
                    strict_tp += 1
                    gold_matched_strict.add(g_idx)
                    matched = True
                    break
        if not matched:
            strict_fp += 1
    strict_fn = len(gold_spans) - len(gold_matched_strict)

    lenient_tp = 0
    lenient_fp = 0
    gold_matched_lenient = set()

    for pred in pred_spans:
        matched = False
        for g_idx, gold in enumerate(gold_spans):
            if g_idx not in gold_matched_lenient:
                if pred["label"] == gold["label"]:
                    if max(pred["start_char"], gold["start_char"]) < min(pred["end_char"], gold["end_char"]):
                        lenient_tp += 1
                        gold_matched_lenient.add(g_idx)
                        matched = True
                        break
        if not matched:
            lenient_fp += 1
    lenient_fn = len(gold_spans) - len(gold_matched_lenient)

    def calc_prf(tp, fp, fn):
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        return round(p * 100, 2), round(r * 100, 2), round(f1 * 100, 2)

    s_p, s_r, s_f1 = calc_prf(strict_tp, strict_fp, strict_fn)
    l_p, l_r, l_f1 = calc_prf(lenient_tp, lenient_fp, lenient_fn)

    return {
        "strict": {"precision": s_p, "recall": s_r, "f1": s_f1, "tp": strict_tp, "fp": strict_fp, "fn": strict_fn},
        "lenient": {"precision": l_p, "recall": l_r, "f1": l_f1, "tp": lenient_tp, "fp": lenient_fp, "fn": lenient_fn}
    }


def predict_spans(model, dataset, device):
    """
    Runs model inference over dataset and reconstructs character-level entity spans.
    """
    model.eval()
    pred_spans_all = []
    gold_spans_all = []

    with torch.no_grad():
        for sample in dataset:
            input_ids = sample["input_ids"].unsqueeze(0).to(device)
            attention_mask = sample["attention_mask"].unsqueeze(0).to(device)
            offset_mapping = sample["offset_mapping"]
            raw_text = sample["raw_text"]
            r_id = sample["report_id"]

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits.squeeze(0)
            preds = torch.argmax(logits, dim=-1).cpu().numpy()

            # Record gold spans
            for g in sample["gold_spans"]:
                gold_spans_all.append({
                    "label": g["category"],
                    "start_char": g["start_char"],
                    "end_char": g["end_char"],
                    "report_id": r_id
                })

            # Reconstruct spans from predicted subwords
            current_span = None
            for idx, (sub_start, sub_end) in enumerate(offset_mapping):
                sub_start, sub_end = int(sub_start), int(sub_end)
                if sub_start == 0 and sub_end == 0:
                    continue

                pred_id = preds[idx]
                pred_label = ID2LABEL[pred_id]

                if pred_label.startswith("B-"):
                    if current_span:
                        pred_spans_all.append(current_span)
                    cat = pred_label[2:]
                    current_span = {
                        "label": cat,
                        "start_char": sub_start,
                        "end_char": sub_end,
                        "report_id": r_id
                    }
                elif pred_label.startswith("I-"):
                    cat = pred_label[2:]
                    if current_span and current_span["label"] == cat:
                        current_span["end_char"] = sub_end
                    else:
                        if current_span:
                            pred_spans_all.append(current_span)
                        current_span = {
                            "label": cat,
                            "start_char": sub_start,
                            "end_char": sub_end,
                            "report_id": r_id
                        }
                else:  # "O"
                    if current_span:
                        pred_spans_all.append(current_span)
                        current_span = None

            if current_span:
                pred_spans_all.append(current_span)

    return gold_spans_all, pred_spans_all


def train_fold(fold_name, train_dataset, test_dataset, device, epochs=4, lr=3e-5, batch_size=8):
    """
    Fine-tunes Bio_ClinicalBERT on a single cross-validation fold.
    """
    print(f"\n--- Training {fold_name.upper()} ({len(train_dataset)} train docs, {len(test_dataset)} test docs) ---")
    model = AutoModelForTokenClassification.from_pretrained(
        MODEL_CHECKPOINT,
        num_labels=len(LABEL_LIST),
        id2label=ID2LABEL,
        label2id=LABEL2ID
    ).to(device)

    def collate_train_batch(batch):
        max_len = max(len(b["input_ids"]) for b in batch)
        input_ids = []
        attention_mask = []
        labels = []
        for b in batch:
            pad_len = max_len - len(b["input_ids"])
            if pad_len > 0:
                input_ids.append(torch.cat([b["input_ids"], torch.zeros(pad_len, dtype=torch.long)]))
                attention_mask.append(torch.cat([b["attention_mask"], torch.zeros(pad_len, dtype=torch.long)]))
                labels.append(torch.cat([b["labels"], torch.full((pad_len,), -100, dtype=torch.long)]))
            else:
                input_ids.append(b["input_ids"])
                attention_mask.append(b["attention_mask"])
                labels.append(b["labels"])
        return {
            "input_ids": torch.stack(input_ids),
            "attention_mask": torch.stack(attention_mask),
            "labels": torch.stack(labels)
        }

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_train_batch)
    total_steps = len(train_loader) * epochs
    warmup_steps = int(0.1 * total_steps)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps)

    model.train()
    start_time = time.time()

    for epoch in range(1, epochs + 1):
        total_loss = 0.0
        for batch in train_loader:
            optimizer.zero_grad()
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()

            total_loss += loss.item()

        avg_loss = total_loss / max(1, len(train_loader))
        print(f"  Epoch {epoch}/{epochs} | Loss: {avg_loss:.4f}", flush=True)

    elapsed = time.time() - start_time
    print(f"  Training complete in {elapsed:.1f}s", flush=True)

    # Evaluate on test fold
    gold_spans, pred_spans = predict_spans(model, test_dataset, device)
    metrics = compute_span_eval(gold_spans, pred_spans)
    print(f"  Fold Results: Strict F1 = {metrics['strict']['f1']:.1f}% | Lenient F1 = {metrics['lenient']['f1']:.1f}%", flush=True)

    return model, metrics


def main():
    print("==========================================================================", flush=True)
    print("PULSE Phase C: Bio_ClinicalBERT Fine-Tuning & 5-Fold Cross-Validation", flush=True)
    print("==========================================================================", flush=True)

    # Optimize thread count on CPU
    num_threads = min(8, os.cpu_count() or 4)
    torch.set_num_threads(num_threads)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Execution Device: {device} (PyTorch {torch.__version__}, Threads: {num_threads})", flush=True)

    # 1. Load Data
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)
    with open(SPLITS_PATH, "r", encoding="utf-8") as f:
        splits = json.load(f)

    reports = {r["report_id"]: r for r in corpus["reports"]}
    print(f"Loaded {len(reports)} gold documents across 5 folds.", flush=True)

    # 2. Tokenizer
    tokenizer = BertTokenizerFast.from_pretrained(MODEL_CHECKPOINT)
    print(f"Initialized {MODEL_CHECKPOINT} tokenizer with {len(tokenizer)} vocabulary entries.\n", flush=True)

    fold_results = []
    best_f1 = -1.0
    best_model = None

    # 3. 5-Fold Cross-Validation Loop
    for fold_name, split in splits.items():
        train_ids = split["train"] + split["val"]
        test_ids = split["test"]

        train_dataset = NursingHandoverDataset(reports, train_ids, tokenizer, max_length=180)
        test_dataset = NursingHandoverDataset(reports, test_ids, tokenizer, max_length=180)

        model, metrics = train_fold(
            fold_name=fold_name,
            train_dataset=train_dataset,
            test_dataset=test_dataset,
            device=device,
            epochs=3,
            lr=3e-5,
            batch_size=8
        )

        fold_results.append(metrics)
        if metrics["strict"]["f1"] > best_f1:
            best_f1 = metrics["strict"]["f1"]
            best_model = model

    # 4. Save Best Model Checkpoint
    os.makedirs(MODEL_OUTPUT_DIR, exist_ok=True)
    print(f"\nSaving best model checkpoint (Strict F1: {best_f1:.1f}%) to {MODEL_OUTPUT_DIR}...")
    best_model.save_pretrained(MODEL_OUTPUT_DIR)
    tokenizer.save_pretrained(MODEL_OUTPUT_DIR)

    # 5. Aggregate 5-Fold Metrics
    def aggregate_metrics(fold_list, metric_type):
        p_vals = [f[metric_type]["precision"] for f in fold_list]
        r_vals = [f[metric_type]["recall"] for f in fold_list]
        f_vals = [f[metric_type]["f1"] for f in fold_list]
        return {
            "precision_mean": round(float(np.mean(p_vals)), 2),
            "precision_std": round(float(np.std(p_vals)), 2),
            "recall_mean": round(float(np.mean(r_vals)), 2),
            "recall_std": round(float(np.std(r_vals)), 2),
            "f1_mean": round(float(np.mean(f_vals)), 2),
            "f1_std": round(float(np.std(f_vals)), 2)
        }

    clinicalbert_summary = {
        "model": "Bio_ClinicalBERT (emilyalsentzer/Bio_ClinicalBERT)",
        "task": "Clinical Named Entity Recognition (Token Classification)",
        "evaluation_protocol": "Document-Level 5-Fold Cross-Validation (Identical to Phase B)",
        "strict_span_metrics": aggregate_metrics(fold_results, "strict"),
        "lenient_span_metrics": aggregate_metrics(fold_results, "lenient"),
        "per_fold": fold_results
    }

    # Load baseline results from Phase B for direct comparison
    baseline_summary = {}
    if os.path.exists(BASELINE_RESULTS_PATH):
        with open(BASELINE_RESULTS_PATH, "r", encoding="utf-8") as f:
            baseline_summary = json.load(f)

    full_evaluation = {
        "dataset": "PULSE Synthetic Nursing Handover (101 Documents)",
        "evaluation_protocol": "Stratified Document-Level 5-Fold Cross-Validation",
        "bio_clinicalbert": clinicalbert_summary,
        "baselines_comparison": {
            "rule_based_baseline": baseline_summary.get("rule_based_baseline", {}),
            "statistical_classifier_baseline": baseline_summary.get("statistical_classifier_baseline", {})
        }
    }

    with open(OUTPUT_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(full_evaluation, f, indent=2)

    print(f"\nSaved complete benchmark comparison to {OUTPUT_RESULTS_PATH}")
    print("\n==========================================================================")
    print("FINAL 5-FOLD BENCHMARK COMPARISON (STRICT SPAN F1)")
    print("==========================================================================")
    print(f"1. Rule Engine Baseline:            Strict F1 = {baseline_summary.get('rule_based_baseline', {}).get('strict_span_metrics', {}).get('f1_mean', 'N/A')}% ± {baseline_summary.get('rule_based_baseline', {}).get('strict_span_metrics', {}).get('f1_std', 'N/A')}%")
    print(f"2. Statistical Sequence Classifier: Strict F1 = {baseline_summary.get('statistical_classifier_baseline', {}).get('strict_span_metrics', {}).get('f1_mean', 'N/A')}% ± {baseline_summary.get('statistical_classifier_baseline', {}).get('strict_span_metrics', {}).get('f1_std', 'N/A')}%")
    print(f"3. Bio_ClinicalBERT (Fine-Tuned):   Strict F1 = {clinicalbert_summary['strict_span_metrics']['f1_mean']}% ± {clinicalbert_summary['strict_span_metrics']['f1_std']}%")
    print("==========================================================================")
    print(f"LENIENT SPAN F1: Bio_ClinicalBERT = {clinicalbert_summary['lenient_span_metrics']['f1_mean']}% ± {clinicalbert_summary['lenient_span_metrics']['f1_std']}%")
    print("==========================================================================")


if __name__ == "__main__":
    main()
