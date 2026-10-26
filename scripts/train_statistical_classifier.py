"""
PULSE — Reproducible Statistical Classifier Hyperparameter Tuning & Cross-Validation Harness
Phase 5 — Training Pipeline & Model Comparison

Performs rigorous, leak-free hyperparameter tuning for the statistical sequence classifier
across 5-fold document-level cross-validation on the 101-note gold standard corpus.

Key Integrity Constraints:
1. Document-Level Disjointness: Fold splits (train, val, test) are disjoint across documents.
2. Leak-Free Feature Vectorization: DictVectorizer is fitted strictly on the train fold and only transforms val/test.
3. Hyperparameter Selection on Validation Fold: Candidate models are tuned exclusively on 'val'
   using Strict Span F1 as the primary selection metric, preventing test set contamination.
4. Unbiased Final Evaluation: Selected models are evaluated on 'test' reporting Strict F1,
   Lenient F1, Token Accuracy, and Per-Class metrics.
5. Non-Destructive Export: Results saved to statistical_classifier_tuning_results.json.
"""

import os
import sys
import json
import time
import re
import platform
from collections import defaultdict, Counter
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score

CORPUS_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "gold_standard_corpus.json")
SPLITS_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "train_test_splits.json")
RESULTS_OUTPUT_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "statistical_classifier_tuning_results.json")

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
    "PatientIntroduction_CurrentBed": "Demographics_Bed",
    "PatientIntroduction_CurrentRoom": "Demographics_Bed",
    "PatientIntroduction_GivenNames/Initials": "Demographics_Name",
    "PatientIntroduction_Lastname": "Demographics_Name",
    "PatientIntroduction_Ageinyears": "Demographics_Age",
    "PatientIntroduction_Gender": "Demographics_Gender",
    "PatientIntroduction_UnderDr_Lastname": "Demographics_Doctor",
    "PatientIntroduction_UnderDr_GivenNames/Initials": "Demographics_Doctor",
    "Appointment/Procedure_ClinicianLastname": "Demographics_Doctor",
    "Appointment/Procedure_ClinicianGivenNames/Initials": "Demographics_Doctor",
    "PatientIntroduction_AdmissionReason/Diagnosis": "Clinical_Condition",
    "PatientIntroduction_Disease/ProblemHistory": "Clinical_Condition",
    "PatientIntroduction_ChronicCondition": "Clinical_Condition",
    "MyShift_Status": "Clinical_Observation",
    "MyShift_OtherObservation": "Clinical_Observation",
    "MyShift_Wounds/Skin": "Clinical_Observation",
    "MyShift_Output/Diuresis/BowelMovement": "Clinical_Observation",
    "MyShift_Input/Diet": "Clinical_Observation",
    "Future_Alert/Warning/AbnormalResult": "Clinical_Observation",
    "Medication_Medicine": "Medication",
    "Medication_Dosage": "Medication",
    "Medication_Status": "Medication",
    "Appointment/Procedure_Description": "Investigation_Procedure",
    "Appointment/Procedure_Status": "Investigation_Procedure",
    "Appointment/Procedure_Day": "Investigation_Procedure",
    "Appointment/Procedure_Time": "Investigation_Procedure",
    "Appointment/Procedure_City": "Investigation_Procedure",
    "Appointment/Procedure_Ward": "Investigation_Procedure",
    "Future_Goal/TaskToBeCompleted/ExpectedOutcome": "Plan_Goal",
    "Future_Discharge/TransferPlan": "Plan_Goal",
    "PatientIntroduction_CarePlan": "Plan_Goal",
    "PatientIntroduction_Allergy": "Plan_Goal",
    "MyShift_RiskManagement": "Plan_Goal",
    "MyShift_ActivitiesOfDailyLiving": "Care_Activity",
    "MyShift_Contraption": "Care_Activity"
}


def map_label(label: str) -> str:
    """Maps NICTA raw or BIO labels to harmonized macro categories."""
    if label in ["NA", "O", None]:
        return "O"
    clean = label.replace("B-", "").replace("I-", "")
    return CATEGORY_MAP.get(clean, "O")


def extract_token_features(tokens: list, idx: int) -> dict:
    """Extracts linguistic and contextual window features for a single token."""
    t = tokens[idx]
    tok_str = t["token"]
    pos_tag = t.get("pos", "")
    lemma = t.get("lemma", "")
    ner = t.get("ner_coarse", "O")

    feats = {
        "bias": 1.0,
        "token": tok_str.lower(),
        "pos": pos_tag,
        "lemma": lemma.lower(),
        "ner": ner,
        "is_upper": tok_str.isupper(),
        "is_title": tok_str.istitle(),
        "is_digit": tok_str.isdigit(),
        "has_digit": bool(re.search(r'\d', tok_str)),
        "has_hyphen": "-" in tok_str,
        "prefix2": tok_str[:2].lower(),
        "prefix3": tok_str[:3].lower(),
        "suffix2": tok_str[-2:].lower(),
        "suffix3": tok_str[-3:].lower(),
    }

    # Preceding token
    if idx > 0:
        p = tokens[idx - 1]
        feats.update({
            "-1:token": p["token"].lower(),
            "-1:pos": p.get("pos", ""),
            "-1:lemma": p.get("lemma", "").lower(),
            "-1:ner": p.get("ner_coarse", "O"),
            "-1:title": p["token"].istitle(),
        })
    else:
        feats["BOS"] = True

    # Succeeding token
    if idx < len(tokens) - 1:
        n = tokens[idx + 1]
        feats.update({
            "+1:token": n["token"].lower(),
            "+1:pos": n.get("pos", ""),
            "+1:lemma": n.get("lemma", "").lower(),
            "+1:ner": n.get("ner_coarse", "O"),
            "+1:title": n["token"].istitle(),
        })
    else:
        feats["EOS"] = True

    return feats


def reconstruct_spans_from_tokens(preds: list, token_meta: list) -> list:
    """Reconstructs contiguous entity character spans from token label predictions."""
    spans = []
    current_span = None

    for p_label, meta in zip(preds, token_meta):
        if p_label != "O":
            if current_span and current_span["label"] == p_label and current_span["report_id"] == meta["report_id"]:
                current_span["end_char"] = meta["end_char"]
            else:
                if current_span:
                    spans.append(current_span)
                current_span = {
                    "label": p_label,
                    "report_id": meta["report_id"],
                    "start_char": meta["start_char"],
                    "end_char": meta["end_char"]
                }
        else:
            if current_span:
                spans.append(current_span)
                current_span = None

    if current_span:
        spans.append(current_span)

    return spans


def compute_span_metrics(gold_spans: list, pred_spans: list) -> dict:
    """Computes strict and lenient span-level precision, recall, and F1."""
    # 1. Strict Match (Exact label, exact [start_char, end_char))
    strict_tp = 0
    strict_fp = 0
    gold_matched_strict = set()
    per_class_strict = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})

    for pred in pred_spans:
        matched = False
        for g_idx, gold in enumerate(gold_spans):
            if g_idx not in gold_matched_strict:
                if (pred["label"] == gold["label"] and 
                    pred["start_char"] == gold["start_char"] and 
                    pred["end_char"] == gold["end_char"] and
                    pred["report_id"] == gold["report_id"]):
                    strict_tp += 1
                    per_class_strict[pred["label"]]["tp"] += 1
                    gold_matched_strict.add(g_idx)
                    matched = True
                    break
        if not matched:
            strict_fp += 1
            per_class_strict[pred["label"]]["fp"] += 1

    strict_fn = len(gold_spans) - len(gold_matched_strict)
    for g_idx, gold in enumerate(gold_spans):
        if g_idx not in gold_matched_strict:
            per_class_strict[gold["label"]]["fn"] += 1

    # 2. Lenient Match (Exact label, character overlap > 0)
    lenient_tp = 0
    lenient_fp = 0
    gold_matched_lenient = set()

    for pred in pred_spans:
        matched = False
        for g_idx, gold in enumerate(gold_spans):
            if g_idx not in gold_matched_lenient:
                if pred["label"] == gold["label"] and pred["report_id"] == gold["report_id"]:
                    if max(pred["start_char"], gold["start_char"]) < min(pred["end_char"], gold["end_char"]):
                        lenient_tp += 1
                        gold_matched_lenient.add(g_idx)
                        matched = True
                        break
        if not matched:
            lenient_fp += 1

    lenient_fn = len(gold_spans) - len(gold_matched_lenient)

    def calc_prf(tp, fp, fn):
        p = (tp / (tp + fp)) * 100 if (tp + fp) > 0 else 0.0
        r = (tp / (tp + fn)) * 100 if (tp + fn) > 0 else 0.0
        f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0
        return round(p, 2), round(r, 2), round(f1, 2)

    s_p, s_r, s_f1 = calc_prf(strict_tp, strict_fp, strict_fn)
    l_p, l_r, l_f1 = calc_prf(lenient_tp, lenient_fp, lenient_fn)

    per_class_out = {}
    for cat in MACRO_CATEGORIES:
        counts = per_class_strict[cat]
        cp, cr, cf1 = calc_prf(counts["tp"], counts["fp"], counts["fn"])
        per_class_out[cat] = {
            "precision": cp,
            "recall": cr,
            "f1": cf1,
            "tp": counts["tp"],
            "fp": counts["fp"],
            "fn": counts["fn"]
        }

    return {
        "strict": {"precision": s_p, "recall": s_r, "f1": s_f1, "tp": strict_tp, "fp": strict_fp, "fn": strict_fn},
        "lenient": {"precision": l_p, "recall": l_r, "f1": l_f1, "tp": lenient_tp, "fp": lenient_fp, "fn": lenient_fn},
        "per_class_strict": per_class_out
    }


def run_hyperparameter_tuning_experiment():
    """Executes the full cross-validation and hyperparameter tuning experiment."""
    print("=" * 80)
    print("PULSE — Statistical Classifier Hyperparameter Tuning & Evaluation")
    print("=" * 80)

    start_time = time.time()

    # Load Corpus and Splits
    if not os.path.exists(CORPUS_PATH):
        raise FileNotFoundError(f"Corpus file not found: {CORPUS_PATH}")
    if not os.path.exists(SPLITS_PATH):
        raise FileNotFoundError(f"Splits file not found: {SPLITS_PATH}")

    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)
    with open(SPLITS_PATH, "r", encoding="utf-8") as f:
        splits = json.load(f)

    reports = {r["report_id"]: r for r in corpus["reports"]}
    print(f"Loaded {len(reports)} documents across 5 cross-validation folds.")

    # Search Grid
    param_grid = [
        {"C": 0.01, "class_weight": None},
        {"C": 0.01, "class_weight": "balanced"},
        {"C": 0.1, "class_weight": None},
        {"C": 0.1, "class_weight": "balanced"},
        {"C": 1.0, "class_weight": None},
        {"C": 1.0, "class_weight": "balanced"},
        {"C": 10.0, "class_weight": None},
        {"C": 10.0, "class_weight": "balanced"},
    ]

    print(f"Hyperparameter Grid: {len(param_grid)} configurations across C in [0.01, 0.1, 1.0, 10.0] and class_weight in [None, 'balanced']")

    fold_evaluations = []
    selected_configurations = []

    for fold_name, split in splits.items():
        print(f"\n--- Processing {fold_name.upper()} (Train: {len(split['train'])}, Val: {len(split['val'])}, Test: {len(split['test'])}) ---")

        # 1. Prepare Feature Dictionaries for Train
        train_feats = []
        train_labels = []
        for rid in split["train"]:
            doc = reports[rid]
            toks = doc["tokens"]
            for idx in range(len(toks)):
                train_feats.append(extract_token_features(toks, idx))
                train_labels.append(map_label(toks[idx]["adjudicated_label"]))

        # 2. Prepare Feature Dictionaries for Validation
        val_feats = []
        val_labels = []
        val_meta = []
        val_gold_spans = []
        for rid in split["val"]:
            doc = reports[rid]
            toks = doc["tokens"]
            for idx in range(len(toks)):
                val_feats.append(extract_token_features(toks, idx))
                val_labels.append(map_label(toks[idx]["adjudicated_label"]))
                val_meta.append({
                    "report_id": rid,
                    "start_char": toks[idx]["start_char"],
                    "end_char": toks[idx]["end_char"],
                    "token": toks[idx]["token"]
                })
            for sp in doc.get("entity_spans", []):
                h_cat = map_label(sp["label"])
                if h_cat != "O":
                    val_gold_spans.append({
                        "label": h_cat,
                        "report_id": rid,
                        "start_char": sp["start_char"],
                        "end_char": sp["end_char"],
                        "text": sp["text"]
                    })

        # 3. Fit Vectorizer STRICTLY on Train Fold
        vec = DictVectorizer(sparse=True)
        X_train = vec.fit_transform(train_feats)
        X_val = vec.transform(val_feats)

        # 4. Inner Validation Loop: Evaluate all hyperparameter candidates on Validation Fold
        best_val_f1 = -1.0
        best_param = None
        tuning_log = []

        for p in param_grid:
            clf = LogisticRegression(
                max_iter=1000,
                C=p["C"],
                class_weight=p["class_weight"],
                solver="lbfgs",
                random_state=42
            )
            clf.fit(X_train, train_labels)
            val_preds = clf.predict(X_val)

            # Reconstruct spans and evaluate Strict F1 on val fold
            val_pred_spans = reconstruct_spans_from_tokens(val_preds, val_meta)
            val_metrics = compute_span_metrics(val_gold_spans, val_pred_spans)
            val_strict_f1 = val_metrics["strict"]["f1"]
            val_acc = accuracy_score(val_labels, val_preds) * 100

            tuning_log.append({
                "params": p,
                "val_token_acc": round(val_acc, 2),
                "val_strict_f1": val_strict_f1,
                "val_lenient_f1": val_metrics["lenient"]["f1"]
            })

            if val_strict_f1 > best_val_f1:
                best_val_f1 = val_strict_f1
                best_param = p

        print(f"  Selected Optimal Config for {fold_name}: C={best_param['C']}, class_weight={best_param['class_weight']} (Val Strict F1 = {best_val_f1:.2f}%)")
        selected_configurations.append({"fold": fold_name, "best_param": best_param, "val_strict_f1": best_val_f1})

        # 5. Unbiased Evaluation on Test Fold
        # Fit model with selected hyperparameters on train+val to leverage full training partition
        train_val_feats = train_feats + val_feats
        train_val_labels = train_labels + val_labels

        vec_full = DictVectorizer(sparse=True)
        X_train_val = vec_full.fit_transform(train_val_feats)

        best_clf = LogisticRegression(
            max_iter=1000,
            C=best_param["C"],
            class_weight=best_param["class_weight"],
            solver="lbfgs",
            random_state=42
        )
        best_clf.fit(X_train_val, train_val_labels)

        # Prepare Test Fold Features
        test_feats = []
        test_labels = []
        test_meta = []
        test_gold_spans = []
        for rid in split["test"]:
            doc = reports[rid]
            toks = doc["tokens"]
            for idx in range(len(toks)):
                test_feats.append(extract_token_features(toks, idx))
                test_labels.append(map_label(toks[idx]["adjudicated_label"]))
                test_meta.append({
                    "report_id": rid,
                    "start_char": toks[idx]["start_char"],
                    "end_char": toks[idx]["end_char"],
                    "token": toks[idx]["token"]
                })
            for sp in doc.get("entity_spans", []):
                h_cat = map_label(sp["label"])
                if h_cat != "O":
                    test_gold_spans.append({
                        "label": h_cat,
                        "report_id": rid,
                        "start_char": sp["start_char"],
                        "end_char": sp["end_char"],
                        "text": sp["text"]
                    })

        X_test = vec_full.transform(test_feats)
        test_preds = best_clf.predict(X_test)
        test_acc = accuracy_score(test_labels, test_preds) * 100

        test_pred_spans = reconstruct_spans_from_tokens(test_preds, test_meta)
        test_metrics = compute_span_metrics(test_gold_spans, test_pred_spans)

        print(f"  Test Evaluation: Strict F1 = {test_metrics['strict']['f1']:.2f}% | Lenient F1 = {test_metrics['lenient']['f1']:.2f}% | Token Acc = {test_acc:.2f}%")

        fold_evaluations.append({
            "fold_name": fold_name,
            "selected_param": best_param,
            "tuning_history": tuning_log,
            "test_token_accuracy": round(test_acc, 2),
            "test_metrics": test_metrics
        })

    elapsed_time = time.time() - start_time

    # Aggregate 5-Fold Test Metrics
    def aggregate(field_getter):
        vals = [field_getter(f) for f in fold_evaluations]
        return round(float(np.mean(vals)), 2), round(float(np.std(vals)), 2)

    strict_p_mean, strict_p_std = aggregate(lambda f: f["test_metrics"]["strict"]["precision"])
    strict_r_mean, strict_r_std = aggregate(lambda f: f["test_metrics"]["strict"]["recall"])
    strict_f1_mean, strict_f1_std = aggregate(lambda f: f["test_metrics"]["strict"]["f1"])

    lenient_p_mean, lenient_p_std = aggregate(lambda f: f["test_metrics"]["lenient"]["precision"])
    lenient_r_mean, lenient_r_std = aggregate(lambda f: f["test_metrics"]["lenient"]["recall"])
    lenient_f1_mean, lenient_f1_std = aggregate(lambda f: f["test_metrics"]["lenient"]["f1"])

    acc_mean, acc_std = aggregate(lambda f: f["test_token_accuracy"])

    # Aggregate Per-Class Metrics across folds
    per_class_summary = {}
    for cat in MACRO_CATEGORIES:
        f1_vals = [f["test_metrics"]["per_class_strict"][cat]["f1"] for f in fold_evaluations]
        p_vals = [f["test_metrics"]["per_class_strict"][cat]["precision"] for f in fold_evaluations]
        r_vals = [f["test_metrics"]["per_class_strict"][cat]["recall"] for f in fold_evaluations]
        per_class_summary[cat] = {
            "f1_mean": round(float(np.mean(f1_vals)), 2),
            "f1_std": round(float(np.std(f1_vals)), 2),
            "precision_mean": round(float(np.mean(p_vals)), 2),
            "recall_mean": round(float(np.mean(r_vals)), 2),
        }

    summary = {
        "metadata": {
            "experiment_name": "Statistical Classifier Hyperparameter Tuning (L2 Logistic Regression)",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "dataset": "PULSE 101 Synthetic Handover Corpus",
            "total_documents": len(reports),
            "cross_validation_folds": 5,
            "partitioning_protocol": "Document-Level Stratified 3-Way Split (Train / Val / Test)",
            "leak_prevention": "DictVectorizer fitted exclusively on training data; Val fold used solely for hyperparameter selection; Test fold evaluated once per fold.",
            "primary_selection_metric": "Strict Span F1 on Validation Fold",
            "hardware_environment": {
                "platform": platform.platform(),
                "python_version": sys.version.split()[0],
                "cpu_count": os.cpu_count(),
                "cuda_available": False,
                "elapsed_seconds": round(elapsed_time, 2)
            }
        },
        "hyperparameter_search_space": {
            "C": [0.01, 0.1, 1.0, 10.0],
            "class_weight": [None, "balanced"],
            "solver": "lbfgs",
            "max_iter": 1000,
            "random_state": 42
        },
        "selected_configurations_per_fold": selected_configurations,
        "overall_test_metrics": {
            "token_accuracy": {"mean": acc_mean, "std": acc_std},
            "strict_span_metrics": {
                "precision": {"mean": strict_p_mean, "std": strict_p_std},
                "recall": {"mean": strict_r_mean, "std": strict_r_std},
                "f1": {"mean": strict_f1_mean, "std": strict_f1_std}
            },
            "lenient_span_metrics": {
                "precision": {"mean": lenient_p_mean, "std": lenient_p_std},
                "recall": {"mean": lenient_r_mean, "std": lenient_r_std},
                "f1": {"mean": lenient_f1_mean, "std": lenient_f1_std}
            }
        },
        "per_class_strict_metrics": per_class_summary,
        "per_fold_evaluations": fold_evaluations
    }

    with open(RESULTS_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 80)
    print("FINAL 5-FOLD TUNED TEST EVALUATION RESULTS")
    print("=" * 80)
    print(f"Token Accuracy:  {acc_mean:.2f}% ± {acc_std:.2f}%")
    print(f"Strict Span F1:  {strict_f1_mean:.2f}% ± {strict_f1_std:.2f}% (Precision: {strict_p_mean:.2f}%, Recall: {strict_r_mean:.2f}%)")
    print(f"Lenient Span F1: {lenient_f1_mean:.2f}% ± {lenient_f1_std:.2f}% (Precision: {lenient_p_mean:.2f}%, Recall: {lenient_r_mean:.2f}%)")
    print(f"Execution Time:  {elapsed_time:.2f}s")
    print(f"Results exported to: {RESULTS_OUTPUT_PATH}")
    print("=" * 80)

    return summary


if __name__ == "__main__":
    run_hyperparameter_tuning_experiment()
