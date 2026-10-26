"""
PULSE — Category-Wise Hybrid Rule + CRF Extractor & Comparative Evaluation
Phase 5 — Step 5.6 Model Comparison & Hybrid Extraction

Implements a principled Category-Wise Hybrid Clinical Extractor that combines:
1. CRF Sequence Tagger for statistical entity span detection and boundary regularization.
2. Rule-Based Clinical Context Engine for:
   - Medication attribute binding (dosage, route, frequency)
   - Assertion classification (positive, negated, uncertain)
   - Temporality classification (current, historical, planned)
   - Investigation status classification (Awaiting Results, Sent, Completed, Pending)
   - Category-targeted rule injection for high-confidence lexical terms.

Evaluates Rule-Based Alone, CRF Alone, and Hybrid Extractor across the identical
5-fold document-level cross-validation splits.
"""

import os
import sys
import json
import time
import platform
from collections import defaultdict
import numpy as np
from scipy import stats

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import sklearn_crfsuite
from sklearn.metrics import accuracy_score

from scripts.train_statistical_classifier import (
    extract_token_features,
    reconstruct_spans_from_tokens,
    compute_span_metrics,
    map_label,
    MACRO_CATEGORIES,
    CORPUS_PATH,
    SPLITS_PATH,
)
from scripts.evaluate_baselines import extract_rule_spans
from backend.extraction.entity_extractor import clinical_entity_extractor
from backend.extraction.context_extractor import clinical_context_extractor

RESULTS_OUTPUT_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "hybrid_extractor_evaluation_results.json")
CRF_RESULTS_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "crf_tuning_results.json")
LR_RESULTS_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "statistical_classifier_tuning_results.json")


class CategoryWiseHybridExtractor:
    """
    Experimental Hybrid Extractor integrating CRF sequence predictions
    with deterministic clinical rules, attribute binding, and context resolution.
    """
    def __init__(self, crf_model=None, target_rule_categories=None):
        self.crf_model = crf_model
        # Categories where validated rule mentions can be admitted into unoccupied spans
        self.target_rule_categories = target_rule_categories or ["Medication", "Investigation_Procedure"]
        self.rule_extractor = clinical_entity_extractor

    def extract_hybrid_entities(self, raw_text: str, tokens: list, report_id: str = "0") -> dict:
        """
        Executes hybrid extraction on a single document:
        1. Generates CRF predictions (if model is available).
        2. Generates Rule predictions with full clinical context.
        3. Applies principled conflict resolution.
        4. Binds medication attributes, assertion, temporality, and investigation status.
        """
        # 1. CRF Span Extraction
        crf_spans = []
        if self.crf_model is not None and tokens:
            doc_feats = [extract_token_features(tokens, idx) for idx in range(len(tokens))]
            pred_labels = self.crf_model.predict_single(doc_feats)
            token_meta = [{
                "report_id": report_id,
                "start_char": t["start_char"],
                "end_char": t["end_char"],
                "token": t["token"]
            } for t in tokens]
            crf_spans = reconstruct_spans_from_tokens(pred_labels, token_meta)
            for s in crf_spans:
                s["extraction_source"] = "crf_sequence_tagger"
                s["confidence_type"] = "model_sequence"

        # 2. Rule Extraction with Attributes
        rule_extracted = self.rule_extractor.extract(raw_text)
        rule_spans = []

        # Convert structured rule output into standard spans with metadata
        for p in rule_extracted.get("patient_information", []):
            field = p.get("field", "")
            sc, ec = p.get("start_char", -1), p.get("end_char", -1)
            if sc != -1 and ec != -1 and sc < ec:
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
                rule_spans.append({
                    "label": cat,
                    "report_id": report_id,
                    "start_char": sc,
                    "end_char": ec,
                    "text": raw_text[sc:ec],
                    "extraction_source": "deterministic_rule",
                    "attributes": p
                })

        for cat_k, target_lbl in [
            ("conditions", "Clinical_Condition"),
            ("symptoms", "Clinical_Observation"),
            ("treatments", "Care_Activity")
        ]:
            for item in rule_extracted.get(cat_k, []):
                for s, e in item.get("all_spans", [(item.get("start_char"), item.get("end_char"))]):
                    if s is not None and e is not None and s < e:
                        rule_spans.append({
                            "label": target_lbl,
                            "report_id": report_id,
                            "start_char": s,
                            "end_char": e,
                            "text": raw_text[s:e],
                            "extraction_source": "deterministic_rule",
                            "attributes": {
                                "assertion": item.get("assertion", "Positive"),
                                "temporality": item.get("temporality", "Current"),
                                "is_negated": item.get("is_negated", False),
                                "is_uncertain": item.get("is_uncertain", False),
                                "is_historical": item.get("is_historical", False)
                            }
                        })

        for med in rule_extracted.get("medications", []):
            for s, e in med.get("all_spans", [(med.get("start_char"), med.get("end_char"))]):
                if s is not None and e is not None and s < e:
                    rule_spans.append({
                        "label": "Medication",
                        "report_id": report_id,
                        "start_char": s,
                        "end_char": e,
                        "text": raw_text[s:e],
                        "extraction_source": "deterministic_rule",
                        "attributes": {
                            "dosage": med.get("dosage"),
                            "frequency": med.get("frequency"),
                            "route": med.get("route"),
                            "assertion": med.get("assertion", "Positive"),
                            "temporality": med.get("temporality", "Current")
                        }
                    })

        for inv in rule_extracted.get("investigations", []):
            for s, e in inv.get("all_spans", [(inv.get("start_char"), inv.get("end_char"))]):
                if s is not None and e is not None and s < e:
                    rule_spans.append({
                        "label": "Investigation_Procedure",
                        "report_id": report_id,
                        "start_char": s,
                        "end_char": e,
                        "text": raw_text[s:e],
                        "extraction_source": "deterministic_rule",
                        "attributes": {
                            "status": inv.get("status", "Unspecified"),
                            "assertion": inv.get("assertion", "Positive"),
                            "temporality": inv.get("temporality", "Current")
                        }
                    })

        # 3. Conflict Resolution & Context Binding
        # Occupancy tracking: maps each character index to the admitting entity
        fused_spans = []
        occupied_chars = {}
        conflicts_resolved = []

        # Step 3a: CRF predictions take primary authority for span boundary & category
        for cs in crf_spans:
            c_start, c_end = cs["start_char"], cs["end_char"]
            # Look for overlapping rule entity to inherit contextual attributes
            matching_rule = None
            for rs in rule_spans:
                if max(c_start, rs["start_char"]) < min(c_end, rs["end_char"]):
                    matching_rule = rs
                    break

            enriched_entity = {
                "label": cs["label"],
                "report_id": report_id,
                "start_char": c_start,
                "end_char": c_end,
                "text": raw_text[c_start:c_end],
                "extraction_source": "crf_sequence_tagger",
                "attributes": {}
            }

            if matching_rule:
                enriched_entity["attributes"] = matching_rule.get("attributes", {})
                enriched_entity["context_inherited_from_rule"] = True
                if matching_rule["label"] != cs["label"]:
                    conflicts_resolved.append({
                        "span": [c_start, c_end],
                        "crf_label": cs["label"],
                        "rule_label": matching_rule["label"],
                        "resolution": "crf_precedence_with_context_binding"
                    })
            else:
                # If no direct rule overlap, extract local assertion context
                ctx = clinical_context_extractor.analyze_assertion(
                    raw_text[c_start:c_end], c_start, c_end, raw_text
                )
                enriched_entity["attributes"] = {
                    "assertion": ctx["assertion"],
                    "temporality": ctx["temporality"],
                    "is_negated": ctx["is_negated"],
                    "is_uncertain": ctx["is_uncertain"],
                    "is_historical": ctx["is_historical"]
                }
                enriched_entity["context_inherited_from_rule"] = False

            fused_spans.append(enriched_entity)
            for c_idx in range(c_start, c_end):
                occupied_chars[c_idx] = cs["label"]

        # Step 3b: Category-Targeted Rule Injection for unoccupied regions
        for rs in rule_spans:
            r_start, r_end = rs["start_char"], rs["end_char"]
            r_lbl = rs["label"]

            # If no CRF model is loaded, admit all valid rule spans; otherwise admit target categories into unoccupied regions
            admit_rule = (self.crf_model is None) or (r_lbl in self.target_rule_categories)
            if admit_rule:
                # Check for overlap with already admitted CRF spans
                has_overlap = any(c_idx in occupied_chars for c_idx in range(r_start, r_end))
                if not has_overlap:
                    injected_entity = {
                        "label": r_lbl,
                        "report_id": report_id,
                        "start_char": r_start,
                        "end_char": r_end,
                        "text": rs["text"],
                        "extraction_source": "rule_injected" if self.crf_model is not None else "deterministic_rule",
                        "attributes": rs.get("attributes", {})
                    }
                    fused_spans.append(injected_entity)
                    for c_idx in range(r_start, r_end):
                        occupied_chars[c_idx] = r_lbl

        return {
            "entities": fused_spans,
            "conflicts_resolved": conflicts_resolved,
            "total_entities": len(fused_spans),
            "crf_count": len(crf_spans),
            "rule_raw_count": len(rule_spans)
        }


def run_hybrid_evaluation_experiment():
    """Executes fair 3-way evaluation: Rule-Based Alone vs CRF Alone vs Hybrid."""
    print("=" * 80)
    print("PULSE — Category-Wise Hybrid Rule + CRF Comparative Evaluation")
    print("=" * 80)

    start_time = time.time()

    if not os.path.exists(CORPUS_PATH):
        raise FileNotFoundError(f"Corpus not found: {CORPUS_PATH}")
    if not os.path.exists(SPLITS_PATH):
        raise FileNotFoundError(f"Splits not found: {SPLITS_PATH}")

    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)
    with open(SPLITS_PATH, "r", encoding="utf-8") as f:
        splits = json.load(f)

    reports = {r["report_id"]: r for r in corpus["reports"]}
    print(f"Loaded {len(reports)} documents across 5 cross-validation folds.")

    fold_evaluations = []

    # Containers for 5-fold aggregations
    metrics_rule_alone = []
    metrics_crf_alone = []
    metrics_hybrid = []

    latencies_rule = []
    latencies_crf = []
    latencies_hybrid = []

    for fold_name, split in splits.items():
        print(f"\n--- Processing {fold_name.upper()} (Train: {len(split['train'])}, Val: {len(split['val'])}, Test: {len(split['test'])}) ---")

        # 1. Train CRF Model on Train + Val partition
        train_val_rids = split["train"] + split["val"]
        X_train_val = [[extract_token_features(reports[rid]["tokens"], i) for i in range(len(reports[rid]["tokens"]))] for rid in train_val_rids]
        y_train_val = [[map_label(reports[rid]["tokens"][i]["adjudicated_label"]) for i in range(len(reports[rid]["tokens"]))] for rid in train_val_rids]

        # Use verified optimal hyperparameters from Step 5.5
        crf = sklearn_crfsuite.CRF(
            algorithm="lbfgs",
            c1=0.1,
            c2=0.01,
            max_iterations=100,
            all_possible_transitions=True,
            verbose=False
        )
        crf.fit(X_train_val, y_train_val)

        # 2. Prepare Gold Test Spans
        test_gold_spans = []
        for rid in split["test"]:
            doc = reports[rid]
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

        # 3. Model 1: Rule-Based Extractor Alone
        t_rule_0 = time.time()
        rule_spans_fold = []
        for rid in split["test"]:
            doc = reports[rid]
            r_sp = extract_rule_spans(doc["raw_text"])
            for s in r_sp:
                s["report_id"] = rid
            rule_spans_fold.extend(r_sp)
        t_rule = time.time() - t_rule_0
        lat_rule = (t_rule / len(split["test"])) * 1000
        latencies_rule.append(lat_rule)
        m_rule = compute_span_metrics(test_gold_spans, rule_spans_fold)
        metrics_rule_alone.append(m_rule)

        # 4. Model 2: CRF Alone
        t_crf_0 = time.time()
        X_test = [[extract_token_features(reports[rid]["tokens"], i) for i in range(len(reports[rid]["tokens"]))] for rid in split["test"]]
        test_meta = [{
            "report_id": rid,
            "start_char": reports[rid]["tokens"][i]["start_char"],
            "end_char": reports[rid]["tokens"][i]["end_char"],
            "token": reports[rid]["tokens"][i]["token"]
        } for rid in split["test"] for i in range(len(reports[rid]["tokens"]))]

        crf_preds_seq = crf.predict(X_test)
        t_crf = time.time() - t_crf_0
        lat_crf = (t_crf / len(split["test"])) * 1000
        latencies_crf.append(lat_crf)

        flat_crf_preds = [l for dp in crf_preds_seq for l in dp]
        crf_spans_fold = reconstruct_spans_from_tokens(flat_crf_preds, test_meta)
        m_crf = compute_span_metrics(test_gold_spans, crf_spans_fold)
        metrics_crf_alone.append(m_crf)

        # 5. Model 3: Category-Wise Hybrid Extractor
        hybrid_extractor = CategoryWiseHybridExtractor(
            crf_model=crf,
            target_rule_categories=["Medication", "Investigation_Procedure"]
        )

        t_hyb_0 = time.time()
        hybrid_spans_fold = []
        all_conflicts = []
        attributes_bound_count = 0

        for rid in split["test"]:
            doc = reports[rid]
            doc_result = hybrid_extractor.extract_hybrid_entities(
                raw_text=doc["raw_text"],
                tokens=doc["tokens"],
                report_id=rid
            )
            for ent in doc_result["entities"]:
                hybrid_spans_fold.append(ent)
                if ent.get("attributes"):
                    attributes_bound_count += 1
            all_conflicts.extend(doc_result["conflicts_resolved"])

        t_hyb = time.time() - t_hyb_0
        lat_hyb = (t_hyb / len(split["test"])) * 1000
        latencies_hybrid.append(lat_hyb)

        m_hyb = compute_span_metrics(test_gold_spans, hybrid_spans_fold)
        metrics_hybrid.append(m_hyb)

        print(f"  Rule Alone Strict F1:   {m_rule['strict']['f1']:.2f}% (Lenient: {m_rule['lenient']['f1']:.2f}%)")
        print(f"  CRF Alone Strict F1:    {m_crf['strict']['f1']:.2f}% (Lenient: {m_crf['lenient']['f1']:.2f}%)")
        print(f"  Hybrid Strict F1:       {m_hyb['strict']['f1']:.2f}% (Lenient: {m_hyb['lenient']['f1']:.2f}%)")
        print(f"  Attributes Bound:       {attributes_bound_count} entities | Conflicts Resolved: {len(all_conflicts)}")

        fold_evaluations.append({
            "fold_name": fold_name,
            "rule_alone_metrics": m_rule,
            "crf_alone_metrics": m_crf,
            "hybrid_metrics": m_hyb,
            "attributes_bound_count": attributes_bound_count,
            "conflicts_resolved_count": len(all_conflicts),
            "latencies_ms": {
                "rule": round(lat_rule, 2),
                "crf": round(lat_crf, 2),
                "hybrid": round(lat_hyb, 2)
            }
        })

    elapsed_total = time.time() - start_time

    # Compute Statistical Aggregations
    def aggregate_metric(metric_list, path_tuple):
        vals = []
        for m in metric_list:
            v = m
            for p in path_tuple:
                v = v[p]
            vals.append(v)
        return round(float(np.mean(vals)), 2), round(float(np.std(vals)), 2), vals

    # Strict F1
    r_sf1_mean, r_sf1_std, r_sf1_vals = aggregate_metric(metrics_rule_alone, ("strict", "f1"))
    c_sf1_mean, c_sf1_std, c_sf1_vals = aggregate_metric(metrics_crf_alone, ("strict", "f1"))
    h_sf1_mean, h_sf1_std, h_sf1_vals = aggregate_metric(metrics_hybrid, ("strict", "f1"))

    # Strict Precision
    r_sp_mean, r_sp_std, _ = aggregate_metric(metrics_rule_alone, ("strict", "precision"))
    c_sp_mean, c_sp_std, _ = aggregate_metric(metrics_crf_alone, ("strict", "precision"))
    h_sp_mean, h_sp_std, _ = aggregate_metric(metrics_hybrid, ("strict", "precision"))

    # Strict Recall
    r_sr_mean, r_sr_std, _ = aggregate_metric(metrics_rule_alone, ("strict", "recall"))
    c_sr_mean, c_sr_std, _ = aggregate_metric(metrics_crf_alone, ("strict", "recall"))
    h_sr_mean, h_sr_std, _ = aggregate_metric(metrics_hybrid, ("strict", "recall"))

    # Lenient F1
    r_lf1_mean, r_lf1_std, _ = aggregate_metric(metrics_rule_alone, ("lenient", "f1"))
    c_lf1_mean, c_lf1_std, _ = aggregate_metric(metrics_crf_alone, ("lenient", "f1"))
    h_lf1_mean, h_lf1_std, _ = aggregate_metric(metrics_hybrid, ("lenient", "f1"))

    # Latencies
    lat_r_mean, lat_r_std = round(float(np.mean(latencies_rule)), 2), round(float(np.std(latencies_rule)), 2)
    lat_c_mean, lat_c_std = round(float(np.mean(latencies_crf)), 2), round(float(np.std(latencies_crf)), 2)
    lat_h_mean, lat_h_std = round(float(np.mean(latencies_hybrid)), 2), round(float(np.std(latencies_hybrid)), 2)

    # Statistical Significance Testing (Paired t-test across 5 folds)
    t_stat_hyb_vs_crf, p_val_hyb_vs_crf = stats.ttest_rel(h_sf1_vals, c_sf1_vals)
    t_stat_hyb_vs_rule, p_val_hyb_vs_rule = stats.ttest_rel(h_sf1_vals, r_sf1_vals)

    # Per-Class Strict F1 Summary
    per_class_comparison = {}
    for cat in MACRO_CATEGORIES:
        r_cat = [m["per_class_strict"][cat]["f1"] for m in metrics_rule_alone]
        c_cat = [m["per_class_strict"][cat]["f1"] for m in metrics_crf_alone]
        h_cat = [m["per_class_strict"][cat]["f1"] for m in metrics_hybrid]
        per_class_comparison[cat] = {
            "rule_f1_mean": round(float(np.mean(r_cat)), 2),
            "crf_f1_mean": round(float(np.mean(c_cat)), 2),
            "hybrid_f1_mean": round(float(np.mean(h_cat)), 2),
            "hybrid_vs_crf_delta": round(float(np.mean(h_cat) - np.mean(c_cat)), 2),
            "hybrid_vs_rule_delta": round(float(np.mean(h_cat) - np.mean(r_cat)), 2)
        }

    summary = {
        "metadata": {
            "experiment_name": "Category-Wise Hybrid Rule + CRF Comparative Evaluation",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "dataset": "PULSE 101 Synthetic Handover Corpus",
            "total_documents": len(reports),
            "cross_validation_folds": 5,
            "partitioning_protocol": "Document-Level Stratified 3-Way Split (Train / Val / Test)",
            "primary_selection_metric": "Strict Span F1",
            "hardware_environment": {
                "platform": platform.platform(),
                "python_version": sys.version.split()[0],
                "cpu_count": os.cpu_count(),
                "elapsed_seconds": round(elapsed_total, 2)
            }
        },
        "model_comparison_overall": {
            "rule_alone": {
                "strict_span_metrics": {"precision": r_sp_mean, "recall": r_sr_mean, "f1": r_sf1_mean, "std": r_sf1_std},
                "lenient_span_metrics": {"f1": r_lf1_mean, "std": r_lf1_std},
                "latency_ms_per_doc": {"mean": lat_r_mean, "std": lat_r_std}
            },
            "crf_alone": {
                "strict_span_metrics": {"precision": c_sp_mean, "recall": c_sr_mean, "f1": c_sf1_mean, "std": c_sf1_std},
                "lenient_span_metrics": {"f1": c_lf1_mean, "std": c_lf1_std},
                "latency_ms_per_doc": {"mean": lat_c_mean, "std": lat_c_std}
            },
            "hybrid_extractor": {
                "strict_span_metrics": {"precision": h_sp_mean, "recall": h_sr_mean, "f1": h_sf1_mean, "std": h_sf1_std},
                "lenient_span_metrics": {"f1": h_lf1_mean, "std": h_lf1_std},
                "latency_ms_per_doc": {"mean": lat_h_mean, "std": lat_h_std}
            },
            "deltas_hybrid_vs_crf": {
                "strict_f1_delta": round(h_sf1_mean - c_sf1_mean, 2),
                "lenient_f1_delta": round(h_lf1_mean - c_lf1_mean, 2),
                "paired_t_statistic": round(float(t_stat_hyb_vs_crf), 4),
                "p_value": round(float(p_val_hyb_vs_crf), 4),
                "statistically_significant": bool(p_val_hyb_vs_crf < 0.05)
            },
            "deltas_hybrid_vs_rule": {
                "strict_f1_delta": round(h_sf1_mean - r_sf1_mean, 2),
                "lenient_f1_delta": round(h_lf1_mean - r_lf1_mean, 2),
                "paired_t_statistic": round(float(t_stat_hyb_vs_rule), 4),
                "p_value": round(float(p_val_hyb_vs_rule), 4),
                "statistically_significant": bool(p_val_hyb_vs_rule < 0.05)
            }
        },
        "per_class_strict_f1_comparison": per_class_comparison,
        "fold_evaluations": fold_evaluations
    }

    with open(RESULTS_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 80)
    print("FINAL 3-WAY COMPARATIVE EVALUATION SUMMARY (5-Fold Means)")
    print("=" * 80)
    print(f"1. Rule Alone: Strict F1 = {r_sf1_mean:.2f}% ± {r_sf1_std:.2f}% | Lenient F1 = {r_lf1_mean:.2f}% | Latency = {lat_r_mean:.2f} ms")
    print(f"2. CRF Alone:  Strict F1 = {c_sf1_mean:.2f}% ± {c_sf1_std:.2f}% | Lenient F1 = {c_lf1_mean:.2f}% | Latency = {lat_c_mean:.2f} ms")
    print(f"3. Hybrid:     Strict F1 = {h_sf1_mean:.2f}% ± {h_sf1_std:.2f}% | Lenient F1 = {h_lf1_mean:.2f}% | Latency = {lat_h_mean:.2f} ms")
    print(f"Hybrid vs CRF:  Strict F1 Delta = {h_sf1_mean - c_sf1_mean:+.2f}%, Lenient F1 Delta = {h_lf1_mean - c_lf1_mean:+.2f}% (p = {p_val_hyb_vs_crf:.4f})")
    print(f"Hybrid vs Rule: Strict F1 Delta = {h_sf1_mean - r_sf1_mean:+.2f}%, Lenient F1 Delta = {h_lf1_mean - r_lf1_mean:+.2f}% (p = {p_val_hyb_vs_rule:.4f})")
    print(f"Results exported to: {RESULTS_OUTPUT_PATH}")
    print("=" * 80)

    return summary


if __name__ == "__main__":
    run_hybrid_evaluation_experiment()
