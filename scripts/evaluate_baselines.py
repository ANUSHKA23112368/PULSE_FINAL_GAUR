"""
PULSE Reproducible Baseline Evaluation Harness
Evaluates:
1. Rule-Based Baseline (HybridClinicalEntityExtractor)
2. Statistical Sequence Classifier (Linguistic Feature Linear Model / CRF-Equivalent)
Across 5-fold document-level cross-validation on the adjudicated gold standard corpus.
"""

import os
import sys
import json
import re
from collections import defaultdict, Counter
import numpy as np

# Prototype root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from backend.extraction.entity_extractor import clinical_entity_extractor
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, accuracy_score, f1_score

CORPUS_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "gold_standard_corpus.json")
SPLITS_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "train_test_splits.json")
RESULTS_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "baseline_evaluation_results.json")

# Category mapping to harmonized 10 clinical macro-categories for head-to-head benchmarking
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

def map_label(label):
    if label == "NA" or label == "O":
        return "O"
    clean_l = label.replace("B-", "").replace("I-", "")
    return CATEGORY_MAP.get(clean_l, "Other")

def extract_rule_spans(raw_text):
    """Runs HybridClinicalEntityExtractor and extracts standardized span tuples."""
    entities = clinical_entity_extractor.extract(raw_text)
    pred_spans = []

    # Patient Information
    for p in entities.get("patient_information", []):
        field = p.get("field", "")
        start_c = p.get("start_char", -1)
        end_c = p.get("end_char", -1)
        if start_c != -1 and end_c != -1 and start_c < end_c:
            if "Bed" in field or "Room" in field:
                cat = "Demographics_Bed"
            elif "Name" in field:
                cat = "Demographics_Name"
            elif "Age" in field:
                cat = "Demographics_Age"
            elif "Gender" in field or "Sex" in field:
                cat = "Demographics_Gender"
            elif "Consultant" in field or "Doctor" in field:
                cat = "Demographics_Doctor"
            else:
                cat = "Demographics_Other"
            pred_spans.append({
                "label": cat,
                "start_char": start_c,
                "end_char": end_c,
                "text": raw_text[start_c:end_c]
            })

    # Conditions
    for c in entities.get("conditions", []):
        for s, e in c.get("all_spans", [(c.get("start_char"), c.get("end_char"))]):
            if s is not None and e is not None and s < e:
                pred_spans.append({
                    "label": "Clinical_Condition",
                    "start_char": s,
                    "end_char": e,
                    "text": raw_text[s:e]
                })

    # Symptoms
    for sym in entities.get("symptoms", []):
        for s, e in sym.get("all_spans", [(sym.get("start_char"), sym.get("end_char"))]):
            if s is not None and e is not None and s < e:
                pred_spans.append({
                    "label": "Clinical_Observation",
                    "start_char": s,
                    "end_char": e,
                    "text": raw_text[s:e]
                })

    # Medications
    for med in entities.get("medications", []):
        for s, e in med.get("all_spans", [(med.get("start_char"), med.get("end_char"))]):
            if s is not None and e is not None and s < e:
                pred_spans.append({
                    "label": "Medication",
                    "start_char": s,
                    "end_char": e,
                    "text": raw_text[s:e]
                })

    # Investigations
    for inv in entities.get("investigations", []):
        for s, e in inv.get("all_spans", [(inv.get("start_char"), inv.get("end_char"))]):
            if s is not None and e is not None and s < e:
                pred_spans.append({
                    "label": "Investigation_Procedure",
                    "start_char": s,
                    "end_char": e,
                    "text": raw_text[s:e]
                })

    # Treatments
    for trt in entities.get("treatments", []):
        for s, e in trt.get("all_spans", [(trt.get("start_char"), trt.get("end_char"))]):
            if s is not None and e is not None and s < e:
                pred_spans.append({
                    "label": "Care_Activity",
                    "start_char": s,
                    "end_char": e,
                    "text": raw_text[s:e]
                })

    # Measurements
    for ms in entities.get("measurements", []):
        s = ms.get("start_char")
        e = ms.get("end_char")
        if s is not None and e is not None and s < e:
            pred_spans.append({
                "label": "Clinical_Observation",
                "start_char": s,
                "end_char": e,
                "text": raw_text[s:e]
            })

    return pred_spans

def token_features(tokens, idx):
    """Extracts linguistic features for a token based on the CRF++ template."""
    t = tokens[idx]
    tok_str = t["token"]
    pos_tag = t["pos"]
    lemma = t["lemma"]
    ner = t["ner_coarse"]

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

    # Previous token
    if idx > 0:
        p = tokens[idx - 1]
        feats.update({
            "-1:token": p["token"].lower(),
            "-1:pos": p["pos"],
            "-1:lemma": p["lemma"].lower(),
            "-1:ner": p["ner_coarse"],
            "-1:title": p["token"].istitle(),
        })
    else:
        feats["BOS"] = True

    # Next token
    if idx < len(tokens) - 1:
        n = tokens[idx + 1]
        feats.update({
            "+1:token": n["token"].lower(),
            "+1:pos": n["pos"],
            "+1:lemma": n["lemma"].lower(),
            "+1:ner": n["ner_coarse"],
            "+1:title": n["token"].istitle(),
        })
    else:
        feats["EOS"] = True

    return feats

def compute_span_eval(gold_spans, pred_spans):
    """
    Computes strict and lenient span-level precision, recall, and F1.
    Strict: same label AND exact (start_char, end_char) match.
    Lenient: same label AND overlap > 0.
    """
    # Strict
    strict_tp = 0
    strict_fp = 0
    strict_fn = 0

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

    # Lenient
    lenient_tp = 0
    lenient_fp = 0
    gold_matched_lenient = set()
    for pred in pred_spans:
        matched = False
        for g_idx, gold in enumerate(gold_spans):
            if g_idx not in gold_matched_lenient:
                if pred["label"] == gold["label"]:
                    # Overlap check
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

def main():
    print("==========================================================================")
    print("PULSE Phase B: Reproducible 5-Fold Cross-Validation Baseline Evaluation")
    print("==========================================================================")

    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    with open(SPLITS_PATH, "r", encoding="utf-8") as f:
        splits = json.load(f)

    reports = {r["report_id"]: r for r in corpus["reports"]}
    print(f"Loaded {len(reports)} documents across 5 cross-validation folds.\n")

    # Storage for fold metrics
    rule_fold_results = []
    stat_fold_results = []
    stat_token_accuracies = []

    for fold_name, split in splits.items():
        train_ids = split["train"] + split["val"]
        test_ids = split["test"]
        print(f"Evaluating {fold_name.upper()} (Train: {len(train_ids)} docs, Test: {len(test_ids)} docs)...")

        # ----------------------------------------------------
        # 1. EVALUATE RULE-BASED EXTRACTOR ON TEST FOLD
        # ----------------------------------------------------
        gold_spans_fold = []
        rule_spans_fold = []

        for r_id in test_ids:
            doc = reports[r_id]
            raw_text = doc["raw_text"]

            # Map gold spans to harmonized categories
            for sp in doc["entity_spans"]:
                h_label = map_label(sp["label"])
                if h_label != "O":
                    gold_spans_fold.append({
                        "label": h_label,
                        "start_char": sp["start_char"],
                        "end_char": sp["end_char"],
                        "text": sp["text"]
                    })

            # Extract rule spans
            r_spans = extract_rule_spans(raw_text)
            rule_spans_fold.extend(r_spans)

        rule_eval = compute_span_eval(gold_spans_fold, rule_spans_fold)
        rule_fold_results.append(rule_eval)

        # ----------------------------------------------------
        # 2. TRAIN & EVALUATE STATISTICAL CLASSIFIER (CRF EQUIVALENT)
        # ----------------------------------------------------
        X_train_feats = []
        y_train_labels = []

        for r_id in train_ids:
            doc = reports[r_id]
            toks = doc["tokens"]
            for idx in range(len(toks)):
                X_train_feats.append(token_features(toks, idx))
                y_train_labels.append(map_label(toks[idx]["adjudicated_label"]))

        X_test_feats = []
        y_test_labels = []
        test_token_meta = []

        for r_id in test_ids:
            doc = reports[r_id]
            toks = doc["tokens"]
            for idx in range(len(toks)):
                X_test_feats.append(token_features(toks, idx))
                y_test_labels.append(map_label(toks[idx]["adjudicated_label"]))
                test_token_meta.append({
                    "report_id": r_id,
                    "start_char": toks[idx]["start_char"],
                    "end_char": toks[idx]["end_char"],
                    "token": toks[idx]["token"]
                })

        # Vectorize features
        vec = DictVectorizer(sparse=True)
        X_train = vec.fit_transform(X_train_feats)
        X_test = vec.transform(X_test_feats)

        # Train linear sequence classifier (L2 regularized logistic model)
        clf = LogisticRegression(max_iter=1000, C=1.0, solver="lbfgs")
        clf.fit(X_train, y_train_labels)

        preds = clf.predict(X_test)
        acc = accuracy_score(y_test_labels, preds) * 100
        stat_token_accuracies.append(acc)

        # Reconstruct predicted spans from token predictions
        stat_spans_fold = []
        current_span = None
        for p_label, meta in zip(preds, test_token_meta):
            if p_label != "O":
                if current_span and current_span["label"] == p_label and current_span["report_id"] == meta["report_id"]:
                    current_span["end_char"] = meta["end_char"]
                else:
                    if current_span:
                        stat_spans_fold.append(current_span)
                    current_span = {
                        "label": p_label,
                        "report_id": meta["report_id"],
                        "start_char": meta["start_char"],
                        "end_char": meta["end_char"]
                    }
            else:
                if current_span:
                    stat_spans_fold.append(current_span)
                    current_span = None
        if current_span:
            stat_spans_fold.append(current_span)

        stat_eval = compute_span_eval(gold_spans_fold, stat_spans_fold)
        stat_fold_results.append(stat_eval)

        print(f"  • Rule-Based:  Strict F1 = {rule_eval['strict']['f1']:.1f}% | Lenient F1 = {rule_eval['lenient']['f1']:.1f}%")
        print(f"  • Statistical: Strict F1 = {stat_eval['strict']['f1']:.1f}% | Lenient F1 = {stat_eval['lenient']['f1']:.1f}% (Token Acc: {acc:.1f}%)")

    # ----------------------------------------------------
    # COMPUTE CROSS-VALIDATION SUMMARY STATISTICS
    # ----------------------------------------------------
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

    summary = {
        "dataset": "PULSE Synthetic Nursing Handover (101 Documents)",
        "evaluation_protocol": "Stratified Document-Level 5-Fold Cross-Validation",
        "rule_based_baseline": {
            "strict_span_metrics": aggregate_metrics(rule_fold_results, "strict"),
            "lenient_span_metrics": aggregate_metrics(rule_fold_results, "lenient"),
            "per_fold": rule_fold_results
        },
        "statistical_classifier_baseline": {
            "token_accuracy_mean": round(float(np.mean(stat_token_accuracies)), 2),
            "token_accuracy_std": round(float(np.std(stat_token_accuracies)), 2),
            "strict_span_metrics": aggregate_metrics(stat_fold_results, "strict"),
            "lenient_span_metrics": aggregate_metrics(stat_fold_results, "lenient"),
            "per_fold": stat_fold_results
        }
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as out_fp:
        json.dump(summary, out_fp, indent=2)

    print("\n==========================================================================")
    print("FINAL 5-FOLD CROSS-VALIDATION BENCHMARK RESULTS")
    print("==========================================================================")
    print(f"{'Model':<30} | {'Strict Precision':<18} | {'Strict Recall':<18} | {'Strict F1':<18} | {'Lenient F1':<18}")
    print("-" * 110)

    rb_s = summary["rule_based_baseline"]["strict_span_metrics"]
    rb_l = summary["rule_based_baseline"]["lenient_span_metrics"]
    print(f"{'Rule Engine (Hybrid)':<30} | {rb_s['precision_mean']:>5.1f}% ± {rb_s['precision_std']:<4.1f} | {rb_s['recall_mean']:>5.1f}% ± {rb_s['recall_std']:<4.1f} | {rb_s['f1_mean']:>5.1f}% ± {rb_s['f1_std']:<4.1f} | {rb_l['f1_mean']:>5.1f}% ± {rb_l['f1_std']:<4.1f}")

    st_s = summary["statistical_classifier_baseline"]["strict_span_metrics"]
    st_l = summary["statistical_classifier_baseline"]["lenient_span_metrics"]
    print(f"{'Statistical Classifier (CRF eq)':<30} | {st_s['precision_mean']:>5.1f}% ± {st_s['precision_std']:<4.1f} | {st_s['recall_mean']:>5.1f}% ± {st_s['recall_std']:<4.1f} | {st_s['f1_mean']:>5.1f}% ± {st_s['f1_std']:<4.1f} | {st_l['f1_mean']:>5.1f}% ± {st_l['f1_std']:<4.1f}")

    print("==========================================================================")
    print(f"Results saved to: {RESULTS_PATH}")

if __name__ == "__main__":
    main()
