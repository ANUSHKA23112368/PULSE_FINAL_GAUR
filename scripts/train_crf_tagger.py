"""
PULSE — Reproducible Conditional Random Field (CRF) Sequence Tagger & Cross-Validation Harness
Phase 5 — Model Comparison & Evaluation

Performs rigorous, leak-free hyperparameter tuning for a linear-chain CRF tagger
across 5-fold document-level cross-validation on the 101-note gold standard corpus.

Key Integrity Constraints:
1. Document-Level Disjointness: Fold splits (train, val, test) are disjoint across documents.
2. Identical Linguistic Features: Reuses the exact feature representation as Logistic Regression.
3. Hyperparameter Selection on Validation Fold: Candidate models are tuned exclusively on 'val'
   using Strict Span F1 as the primary selection metric, preventing test set contamination.
4. Unbiased Final Evaluation: Selected models are evaluated on 'test' reporting Strict F1,
   Lenient F1, Token Accuracy, and Per-Class metrics.
5. Non-Destructive Export: Results saved to crf_tuning_results.json without altering baseline files.
"""

import os
import sys
import json
import time
import platform
from collections import defaultdict
import numpy as np
import sklearn_crfsuite
from sklearn.metrics import accuracy_score

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.train_statistical_classifier import (
    extract_token_features,
    reconstruct_spans_from_tokens,
    compute_span_metrics,
    map_label,
    MACRO_CATEGORIES,
    CORPUS_PATH,
    SPLITS_PATH,
)

RESULTS_OUTPUT_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "crf_tuning_results.json")
LR_RESULTS_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "statistical_classifier_tuning_results.json")


def run_crf_tuning_experiment():
    """Executes the full 5-fold cross-validation and hyperparameter tuning experiment for CRF."""
    print("=" * 80)
    print("PULSE — Conditional Random Field (CRF) Hyperparameter Tuning & Evaluation")
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

    # Search Grid for CRF: c1 (L1) and c2 (L2)
    param_grid = [
        {"c1": 0.0, "c2": 0.0},
        {"c1": 0.0, "c2": 0.01},
        {"c1": 0.0, "c2": 0.1},
        {"c1": 0.01, "c2": 0.0},
        {"c1": 0.01, "c2": 0.01},
        {"c1": 0.01, "c2": 0.1},
        {"c1": 0.1, "c2": 0.0},
        {"c1": 0.1, "c2": 0.01},
        {"c1": 0.1, "c2": 0.1},
    ]

    print(f"Hyperparameter Grid: {len(param_grid)} configurations across c1 in [0.0, 0.01, 0.1] and c2 in [0.0, 0.01, 0.1]")

    fold_evaluations = []
    selected_configurations = []

    for fold_name, split in splits.items():
        print(f"\n--- Processing {fold_name.upper()} (Train: {len(split['train'])}, Val: {len(split['val'])}, Test: {len(split['test'])}) ---")

        # 1. Prepare Document Sequences for Train
        X_train = []
        y_train = []
        for rid in split["train"]:
            doc = reports[rid]
            toks = doc["tokens"]
            doc_feats = [extract_token_features(toks, idx) for idx in range(len(toks))]
            doc_labels = [map_label(toks[idx]["adjudicated_label"]) for idx in range(len(toks))]
            X_train.append(doc_feats)
            y_train.append(doc_labels)

        # 2. Prepare Document Sequences & Metadata for Validation
        X_val = []
        val_meta = []
        val_gold_spans = []
        val_flat_labels = []
        for rid in split["val"]:
            doc = reports[rid]
            toks = doc["tokens"]
            doc_feats = [extract_token_features(toks, idx) for idx in range(len(toks))]
            doc_labels = [map_label(toks[idx]["adjudicated_label"]) for idx in range(len(toks))]
            X_val.append(doc_feats)
            val_flat_labels.extend(doc_labels)

            for idx in range(len(toks)):
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

        # 3. Inner Validation Loop: Evaluate all hyperparameter candidates on Validation Fold
        best_val_f1 = -1.0
        best_param = None
        tuning_log = []

        for p in param_grid:
            crf = sklearn_crfsuite.CRF(
                algorithm="lbfgs",
                c1=p["c1"],
                c2=p["c2"],
                max_iterations=100,
                all_possible_transitions=True,
                verbose=False
            )
            t_fit_start = time.time()
            crf.fit(X_train, y_train)
            t_fit = time.time() - t_fit_start

            val_preds_seq = crf.predict(X_val)
            val_flat_preds = [lbl for doc_p in val_preds_seq for lbl in doc_p]

            # Reconstruct spans and evaluate Strict F1 on val fold
            val_pred_spans = reconstruct_spans_from_tokens(val_flat_preds, val_meta)
            val_metrics = compute_span_metrics(val_gold_spans, val_pred_spans)
            val_strict_f1 = val_metrics["strict"]["f1"]
            val_acc = accuracy_score(val_flat_labels, val_flat_preds) * 100

            tuning_log.append({
                "params": p,
                "fit_time_seconds": round(t_fit, 3),
                "val_token_acc": round(val_acc, 2),
                "val_strict_f1": val_strict_f1,
                "val_lenient_f1": val_metrics["lenient"]["f1"]
            })

            if val_strict_f1 > best_val_f1:
                best_val_f1 = val_strict_f1
                best_param = p

        print(f"  Selected Optimal Config for {fold_name}: c1={best_param['c1']}, c2={best_param['c2']} (Val Strict F1 = {best_val_f1:.2f}%)")
        selected_configurations.append({"fold": fold_name, "best_param": best_param, "val_strict_f1": best_val_f1})

        # 4. Unbiased Evaluation on Test Fold
        # Fit selected model on train + val combined
        X_train_val = X_train + X_val
        y_train_val = y_train + [[map_label(reports[rid]["tokens"][i]["adjudicated_label"]) for i in range(len(reports[rid]["tokens"]))] for rid in split["val"]]

        best_crf = sklearn_crfsuite.CRF(
            algorithm="lbfgs",
            c1=best_param["c1"],
            c2=best_param["c2"],
            max_iterations=100,
            all_possible_transitions=True,
            verbose=False
        )
        t_final_train_start = time.time()
        best_crf.fit(X_train_val, y_train_val)
        final_train_time = time.time() - t_final_train_start

        # Prepare Test Fold Sequences
        X_test = []
        test_flat_labels = []
        test_meta = []
        test_gold_spans = []
        for rid in split["test"]:
            doc = reports[rid]
            toks = doc["tokens"]
            doc_feats = [extract_token_features(toks, idx) for idx in range(len(toks))]
            doc_labels = [map_label(toks[idx]["adjudicated_label"]) for idx in range(len(toks))]
            X_test.append(doc_feats)
            test_flat_labels.extend(doc_labels)

            for idx in range(len(toks)):
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

        # Predict on Test
        t_infer_start = time.time()
        test_preds_seq = best_crf.predict(X_test)
        total_infer_time = time.time() - t_infer_start
        latency_per_doc_ms = (total_infer_time / len(X_test)) * 1000

        test_flat_preds = [lbl for doc_p in test_preds_seq for lbl in doc_p]
        test_acc = accuracy_score(test_flat_labels, test_flat_preds) * 100

        test_pred_spans = reconstruct_spans_from_tokens(test_flat_preds, test_meta)
        test_metrics = compute_span_metrics(test_gold_spans, test_pred_spans)

        print(f"  Test Evaluation: Strict F1 = {test_metrics['strict']['f1']:.2f}% | Lenient F1 = {test_metrics['lenient']['f1']:.2f}% | Token Acc = {test_acc:.2f}% | Latency = {latency_per_doc_ms:.2f} ms/doc")

        fold_evaluations.append({
            "fold_name": fold_name,
            "selected_param": best_param,
            "training_time_seconds": round(final_train_time, 3),
            "inference_time_seconds": round(total_infer_time, 4),
            "latency_per_doc_ms": round(latency_per_doc_ms, 2),
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
    latency_mean, latency_std = aggregate(lambda f: f["latency_per_doc_ms"])
    train_time_mean, train_time_std = aggregate(lambda f: f["training_time_seconds"])

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

    # Load Logistic Regression Results for Direct Comparison if Available
    lr_comparison = None
    if os.path.exists(LR_RESULTS_PATH):
        try:
            with open(LR_RESULTS_PATH, "r", encoding="utf-8") as f:
                lr_data = json.load(f)
            lr_test = lr_data.get("overall_test_metrics", {})
            lr_comparison = {
                "logistic_regression": {
                    "token_accuracy": lr_test.get("token_accuracy", {}).get("mean"),
                    "strict_f1": lr_test.get("strict_span_metrics", {}).get("f1", {}).get("mean"),
                    "strict_precision": lr_test.get("strict_span_metrics", {}).get("precision", {}).get("mean"),
                    "strict_recall": lr_test.get("strict_span_metrics", {}).get("recall", {}).get("mean"),
                    "lenient_f1": lr_test.get("lenient_span_metrics", {}).get("f1", {}).get("mean"),
                },
                "crf": {
                    "token_accuracy": acc_mean,
                    "strict_f1": strict_f1_mean,
                    "strict_precision": strict_p_mean,
                    "strict_recall": strict_r_mean,
                    "lenient_f1": lenient_f1_mean,
                },
                "delta_strict_f1": round(strict_f1_mean - (lr_test.get("strict_span_metrics", {}).get("f1", {}).get("mean") or 0.0), 2),
                "delta_lenient_f1": round(lenient_f1_mean - (lr_test.get("lenient_span_metrics", {}).get("f1", {}).get("mean") or 0.0), 2),
                "delta_token_acc": round(acc_mean - (lr_test.get("token_accuracy", {}).get("mean") or 0.0), 2)
            }
        except Exception as e:
            print(f"Warning: could not parse Logistic Regression comparison: {e}")

    summary = {
        "metadata": {
            "experiment_name": "Conditional Random Field (CRF) Sequence Tagger Tuning & Evaluation",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "dataset": "PULSE 101 Synthetic Handover Corpus",
            "total_documents": len(reports),
            "cross_validation_folds": 5,
            "partitioning_protocol": "Document-Level Stratified 3-Way Split (Train / Val / Test)",
            "leak_prevention": "CRF trained strictly on Train fold during tuning; Val fold used solely for hyperparameter selection; Test fold evaluated once per fold.",
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
            "c1": [0.0, 0.01, 0.1],
            "c2": [0.0, 0.01, 0.1],
            "algorithm": "lbfgs",
            "max_iterations": 100,
            "all_possible_transitions": True
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
            },
            "computational_efficiency": {
                "training_time_seconds": {"mean": train_time_mean, "std": train_time_std},
                "inference_latency_ms_per_doc": {"mean": latency_mean, "std": latency_std}
            }
        },
        "per_class_strict_metrics": per_class_summary,
        "direct_comparison_with_logistic_regression": lr_comparison,
        "per_fold_evaluations": fold_evaluations
    }

    with open(RESULTS_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 80)
    print("FINAL 5-FOLD TUNED CRF TEST EVALUATION RESULTS")
    print("=" * 80)
    print(f"Token Accuracy:  {acc_mean:.2f}% ± {acc_std:.2f}%")
    print(f"Strict Span F1:  {strict_f1_mean:.2f}% ± {strict_f1_std:.2f}% (Precision: {strict_p_mean:.2f}%, Recall: {strict_r_mean:.2f}%)")
    print(f"Lenient Span F1: {lenient_f1_mean:.2f}% ± {lenient_f1_std:.2f}% (Precision: {lenient_p_mean:.2f}%, Recall: {lenient_r_mean:.2f}%)")
    print(f"Avg Train Time:  {train_time_mean:.2f}s | Latency: {latency_mean:.2f} ms/doc")
    print(f"Total Run Time:  {elapsed_time:.2f}s")
    if lr_comparison:
        print(f"Comparison vs Logistic Regression: Strict F1 Delta = {lr_comparison['delta_strict_f1']:+.2f}%, Lenient F1 Delta = {lr_comparison['delta_lenient_f1']:+.2f}%")
    print(f"Results exported to: {RESULTS_OUTPUT_PATH}")
    print("=" * 80)

    return summary


if __name__ == "__main__":
    run_crf_tuning_experiment()
