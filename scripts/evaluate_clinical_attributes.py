"""
PULSE — Clinical Attribute Accuracy & Structured Handover Evaluation Harness
Phase 5 — Step 5.7 Attribute Binding & Handover Integrity Audit

Audits and evaluates the correctness of structured clinical information:
1. Historical 101-Note Corpus: Reports metrics where gold annotations genuinely exist
   (Medication mentions, Investigation mentions, Source-offset validity).
   Explicitly marks relational and contextual attributes as NOT EVALUABLE where gold annotations are absent.
2. Deterministic Schema & Attribute-Binding Regression (7 Schema Fixtures):
   Evaluates attribute binding, assertion, temporality, and status on controlled fixtures.
   Explicitly disclaims this as schema regression testing, NOT independent clinical proof.
3. Controlled Medication Binding Error Analysis:
   Tests cross-medication attribute leakage, missing attribute preservation, PRN indication separation,
   negation handling, historical temporality, and distinct drug deduplication.
4. Investigation & Task Semantics:
   Audits investigation status classification and conditional instruction parsing.
"""

import os
import sys
import json
import time
import platform
from collections import defaultdict
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from backend.extraction.entity_extractor import clinical_entity_extractor
from backend.extraction.structured_generator import StructuredHandoverGenerator
from backend.extraction.context_extractor import clinical_context_extractor
from scripts.train_statistical_classifier import (
    compute_span_metrics,
    map_label,
    CORPUS_PATH,
    SPLITS_PATH,
)

FIXTURE_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "benchmark_schema_fixture.json")
RESULTS_OUTPUT_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "clinical_attribute_evaluation_results.json")


def evaluate_historical_corpus():
    """
    Evaluates historical 101-note corpus strictly against available gold annotations.
    Reports genuine metrics for mentions and explicitly marks missing relations as NOT EVALUABLE.
    """
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    reports = corpus["reports"]

    # 1. Source-Offset Integrity Check across all 101 reports
    offset_checks = 0
    offset_valid = 0
    for r in reports:
        raw_text = r["raw_text"]
        for sp in r.get("entity_spans", []):
            offset_checks += 1
            st, en = sp["start_char"], sp["end_char"]
            if raw_text[st:en] == sp["text"]:
                offset_valid += 1

    offset_accuracy = (offset_valid / offset_checks) * 100 if offset_checks > 0 else 0.0

    # 2. Extract entities using live extractor across all 101 notes
    gold_meds = []
    gold_invs = []
    pred_meds = []
    pred_invs = []

    for r in reports:
        rid = r["report_id"]
        raw_text = r["raw_text"]

        for sp in r.get("entity_spans", []):
            h_cat = map_label(sp["label"])
            if h_cat == "Medication":
                gold_meds.append({"label": "Medication", "report_id": rid, "start_char": sp["start_char"], "end_char": sp["end_char"], "text": sp["text"]})
            elif h_cat == "Investigation_Procedure":
                gold_invs.append({"label": "Investigation_Procedure", "report_id": rid, "start_char": sp["start_char"], "end_char": sp["end_char"], "text": sp["text"]})

        extracted = clinical_entity_extractor.extract(raw_text)
        for m in extracted.get("medications", []):
            for s, e in m.get("all_spans", [(m.get("start_char"), m.get("end_char"))]):
                if s is not None and e is not None and s < e:
                    pred_meds.append({"label": "Medication", "report_id": rid, "start_char": s, "end_char": e, "text": raw_text[s:e]})

        for inv in extracted.get("investigations", []):
            for s, e in inv.get("all_spans", [(inv.get("start_char"), inv.get("end_char"))]):
                if s is not None and e is not None and s < e:
                    pred_invs.append({"label": "Investigation_Procedure", "report_id": rid, "start_char": s, "end_char": e, "text": raw_text[s:e]})

    med_metrics = compute_span_metrics(gold_meds, pred_meds)
    inv_metrics = compute_span_metrics(gold_invs, pred_invs)

    return {
        "dataset_name": "PULSE 101 Synthetic Nursing Handover Corpus",
        "total_documents": len(reports),
        "source_offset_integrity": {
            "total_spans_checked": offset_checks,
            "valid_offsets": offset_valid,
            "offset_accuracy_pct": round(offset_accuracy, 2)
        },
        "mention_extraction_metrics": {
            "medication_mentions": {
                "gold_count": len(gold_meds),
                "predicted_count": len(pred_meds),
                "strict": med_metrics["strict"],
                "lenient": med_metrics["lenient"]
            },
            "investigation_mentions": {
                "gold_count": len(gold_invs),
                "predicted_count": len(pred_invs),
                "strict": inv_metrics["strict"],
                "lenient": inv_metrics["lenient"]
            }
        },
        "attribute_evaluation_status": {
            "medication_to_dose_binding": "NOT EVALUABLE — 0 gold relational link annotations in 101 corpus",
            "medication_to_route_binding": "NOT EVALUABLE — 0 gold relational link annotations in 101 corpus",
            "medication_to_frequency_binding": "NOT EVALUABLE — 0 gold relational link annotations in 101 corpus",
            "prn_indication_binding": "NOT EVALUABLE — 0 gold PRN indication annotations in 101 corpus",
            "investigation_status_classification": "NOT EVALUABLE — 0 gold linked status annotations in 101 corpus",
            "assertion_classification": "NOT EVALUABLE — 0 gold assertion labels in 101 corpus",
            "temporality_classification": "NOT EVALUABLE — 0 gold temporality labels in 101 corpus",
            "pending_task_extraction": "NOT EVALUABLE — 0 gold task labels in 101 corpus",
            "conditional_instruction_extraction": "NOT EVALUABLE — 0 gold conditional trigger/action labels in 101 corpus"
        }
    }


def evaluate_schema_fixtures():
    """
    Evaluates attribute binding and classification against the 7 synthetic schema fixtures.
    Strictly marked as deterministic schema regression testing.
    """
    if not os.path.exists(FIXTURE_PATH):
        return {"status": "FIXTURE FILE NOT FOUND"}

    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        fixture_data = json.load(f)

    docs = fixture_data["documents"]

    # Attribute evaluation counters on fixtures
    dose_tp, dose_fp, dose_fn = 0, 0, 0
    route_tp, route_fp, route_fn = 0, 0, 0
    freq_tp, freq_fp, freq_fn = 0, 0, 0
    prn_tp, prn_fp, prn_fn = 0, 0, 0

    inv_status_total = 0
    inv_status_correct = 0

    assert_total = 0
    assert_correct = 0

    temp_total = 0
    temp_correct = 0

    offset_checks = 0
    offset_valid = 0

    for doc in docs:
        raw_text = doc["raw_text"]
        extracted = clinical_entity_extractor.extract(raw_text)

        # Index extracted meds by character overlap
        ext_meds = extracted.get("medications", [])
        ext_invs = extracted.get("investigations", [])
        ext_all = extracted.get("all_entities", [])

        for gold_ent in doc.get("entities", []):
            st, en = gold_ent["start_char"], gold_ent["end_char"]
            offset_checks += 1
            if raw_text[st:en] == gold_ent["source_text"]:
                offset_valid += 1

            # 1. Assertion and Temporality
            matching_ext = None
            for e in ext_all:
                e_st = e.get("start_char", e.get("source_start"))
                e_en = e.get("end_char", e.get("source_end"))
                if e_st is not None and e_en is not None:
                    if max(st, e_st) < min(en, e_en):
                        matching_ext = e
                        break

            if matching_ext:
                gold_assert = gold_ent.get("assertion")
                if gold_assert:
                    assert_total += 1
                    pred_assert = matching_ext.get("assertion")
                    # Map 'Affirmative' <-> 'Positive'
                    if (pred_assert == gold_assert) or (pred_assert == "Affirmative" and gold_assert == "Positive"):
                        assert_correct += 1

                gold_temp = gold_ent.get("temporality")
                if gold_temp:
                    temp_total += 1
                    pred_temp = matching_ext.get("temporality")
                    if pred_temp == gold_temp:
                        temp_correct += 1

            # 2. Medication Attributes
            if gold_ent["macro_category"] == "Medication":
                gold_attrs = gold_ent.get("medication_attributes") or {}
                # Find matching extracted med
                matched_med = None
                for em in ext_meds:
                    em_st = em.get("start_char", em.get("source_start"))
                    em_en = em.get("end_char", em.get("source_end"))
                    if em_st is not None and em_en is not None:
                        if max(st, em_st) < min(en, em_en):
                            matched_med = em
                            break

                if matched_med:
                    # Dose
                    g_dose = gold_attrs.get("dosage")
                    p_dose = matched_med.get("dosage")
                    if g_dose:
                        if p_dose and g_dose.lower() in p_dose.lower():
                            dose_tp += 1
                        else:
                            dose_fn += 1
                    elif p_dose and p_dose != "Unspecified dose in text":
                        dose_fp += 1

                    # Route
                    g_route = gold_attrs.get("route")
                    p_route = matched_med.get("route")
                    if g_route:
                        if p_route and g_route.upper() in p_route.upper():
                            route_tp += 1
                        else:
                            route_fn += 1
                    elif p_route and p_route != "Unspecified route":
                        route_fp += 1

                    # Frequency
                    g_freq = gold_attrs.get("frequency")
                    p_freq = matched_med.get("frequency")
                    if g_freq:
                        if p_freq and g_freq.lower() in p_freq.lower():
                            freq_tp += 1
                        else:
                            freq_fn += 1
                    elif p_freq and p_freq != "Unspecified frequency":
                        freq_fp += 1

                    # PRN Indication
                    g_prn = gold_attrs.get("prn_indication")
                    p_prn = matched_med.get("prn_indication")
                    if g_prn:
                        if p_prn and g_prn.lower() in p_prn.lower():
                            prn_tp += 1
                        else:
                            prn_fn += 1
                    elif p_prn:
                        prn_fp += 1

            # 3. Investigation Status
            if gold_ent["macro_category"] == "Investigation_Procedure":
                gold_stat = gold_ent.get("investigation_status")
                if gold_stat:
                    inv_status_total += 1
                    matched_inv = None
                    for ei in ext_invs:
                        ei_st = ei.get("start_char", ei.get("source_start"))
                        ei_en = ei.get("end_char", ei.get("source_end"))
                        if ei_st is not None and ei_en is not None:
                            if max(st, ei_st) < min(en, ei_en):
                                matched_inv = ei
                                break
                    if matched_inv:
                        p_stat = matched_inv.get("status")
                        if p_stat == gold_stat:
                            inv_status_correct += 1

    def calc_acc(c, t):
        return round((c / t) * 100, 2) if t > 0 else 0.0

    def calc_f1(tp, fp, fn):
        p = (tp / (tp + fp)) * 100 if (tp + fp) > 0 else 0.0
        r = (tp / (tp + fn)) * 100 if (tp + fn) > 0 else 0.0
        f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0
        return round(p, 2), round(r, 2), round(f1, 2)

    dose_p, dose_r, dose_f1 = calc_f1(dose_tp, dose_fp, dose_fn)
    route_p, route_r, route_f1 = calc_f1(route_tp, route_fp, route_fn)
    freq_p, freq_r, freq_f1 = calc_f1(freq_tp, freq_fp, freq_fn)

    return {
        "dataset_name": "PULSE Benchmark Annotation Schema Fixtures (7 Notes)",
        "disclaimer": "SYNTHETIC SCHEMA REGRESSION TEST ONLY — NOT GENERAL CLINICAL EVIDENCE",
        "total_documents": len(docs),
        "total_entities_checked": len([e for d in docs for e in d.get("entities", [])]),
        "source_offset_integrity_pct": calc_acc(offset_valid, offset_checks),
        "attribute_binding_accuracy": {
            "dose_binding": {"tp": dose_tp, "fp": dose_fp, "fn": dose_fn, "precision": dose_p, "recall": dose_r, "f1": dose_f1},
            "route_binding": {"tp": route_tp, "fp": route_fp, "fn": route_fn, "precision": route_p, "recall": route_r, "f1": route_f1},
            "frequency_binding": {"tp": freq_tp, "fp": freq_fp, "fn": freq_fn, "precision": freq_p, "recall": freq_r, "f1": freq_f1},
            "prn_indication_binding": {"tp": prn_tp, "fp": prn_fp, "fn": prn_fn}
        },
        "classification_accuracy": {
            "investigation_status_accuracy": calc_acc(inv_status_correct, inv_status_total),
            "assertion_classification_accuracy": calc_acc(assert_correct, assert_total),
            "temporality_classification_accuracy": calc_acc(temp_correct, temp_total)
        }
    }


def run_controlled_error_analysis():
    """
    Executes controlled tests for specific medication binding, negation, and semantic edge cases.
    """
    generator = StructuredHandoverGenerator()

    cases = [
        {
            "test_id": "TC_MED_01",
            "name": "Multi-Drug Attribute Boundary Separation",
            "text": "Prescribed Tab Furosemide 40 mg PO daily and Metoprolol 12.5 mg BD.",
            "checks": [
                ("Furosemide dose is 40 mg", lambda r: any(m["text"] == "Furosemide" and "40 mg" in m.get("dosage", "") for m in r["medications"])),
                ("Furosemide route is PO", lambda r: any(m["text"] == "Furosemide" and "PO" in m.get("route", "") for m in r["medications"])),
                ("Metoprolol dose is 12.5 mg", lambda r: any(m["text"] == "Metoprolol" and "12.5 mg" in m.get("dosage", "") for m in r["medications"])),
                ("Metoprolol route does NOT leak PO", lambda r: any(m["text"] == "Metoprolol" and m.get("route") == "Unspecified route" for m in r["medications"]))
            ]
        },
        {
            "test_id": "TC_MED_02",
            "name": "Distinct Drug Pharmacological Deduplication",
            "text": "Ceased Warfarin; commenced Heparin 5000 units subcut.",
            "checks": [
                ("Both Warfarin and Heparin extracted as separate entities", lambda r: len(r["medications"]) == 2 and any(m["text"] == "Warfarin" for m in r["medications"]) and any(m["text"] == "Heparin" for m in r["medications"])),
                ("Warfarin has unspecified dose", lambda r: any(m["text"] == "Warfarin" and m.get("dosage") == "Unspecified dose in text" for m in r["medications"])),
                ("Heparin has 5000 units subcut", lambda r: any(m["text"] == "Heparin" and "5000 units" in m.get("dosage", "") and "SUBCUT" in m.get("route", "") for m in r["medications"]))
            ]
        },
        {
            "test_id": "TC_MED_03",
            "name": "PRN Indication and Frequency Extraction",
            "text": "Paracetamol 1g PO QID PRN for headache.",
            "checks": [
                ("Paracetamol extracted with 1g and PO", lambda r: any(m["text"] == "Paracetamol" and "1g" in m.get("dosage", "") and "PO" in m.get("route", "") for m in r["medications"])),
                ("PRN indication extracted as headache", lambda r: any(m["text"] == "Paracetamol" and m.get("prn_indication") == "headache" for m in r["medications"])),
                ("PRN indication not mistaken for drug name", lambda r: not any(m["text"] == "headache" for m in r["medications"]))
            ]
        },
        {
            "test_id": "TC_MED_04",
            "name": "Negated Medication Exclusion from Active Orders",
            "text": "Patient denies taking any Aspirin or blood thinners.",
            "checks": [
                ("Aspirin marked as Negated", lambda r: any(m["text"] == "Aspirin" and m.get("is_negated") is True for m in r["medications"]))
            ]
        },
        {
            "test_id": "TC_MED_05",
            "name": "Historical Temporality Preservation",
            "text": "Prior history of Digoxin 125mcg daily, ceased last year.",
            "checks": [
                ("Digoxin marked as Historical", lambda r: any(m["text"] == "Digoxin" and m.get("temporality") == "Historical" for m in r["medications"]))
            ]
        },
        {
            "test_id": "TC_SEM_06",
            "name": "Investigation Status Distinctions",
            "text": "Chest X-Ray is completed. Blood cultures sent off to lab. Renal biopsy is pending.",
            "checks": [
                ("CXR marked as Completed", lambda r: any("x-ray" in m["text"].lower() and m.get("status") == "Completed" for m in r["investigations"])),
                ("Blood cultures marked as Sent", lambda r: any("culture" in m["text"].lower() and m.get("status") == "Sent" for m in r["investigations"])),
                ("Renal biopsy marked as Pending", lambda r: any("biopsy" in m["text"].lower() and m.get("status") == "Pending" for m in r["investigations"]))
            ]
        },
        {
            "test_id": "TC_COND_07",
            "name": "Conditional Trigger and Action Separation",
            "text": "If BP < 90, inform MO. Hold Metoprolol if SBP < 100.",
            "checks": [
                ("First trigger condition separated", lambda r: any("BP < 90" in c["trigger_condition"] and "inform MO" in c["resulting_action"] for c in generator.extract_conditional_instructions("If BP < 90, inform MO. Hold Metoprolol if SBP < 100."))),
                ("Second trigger condition separated", lambda r: any("SBP < 100" in c["trigger_condition"] and "Hold Metoprolol" in c["resulting_action"] for c in generator.extract_conditional_instructions("If BP < 90, inform MO. Hold Metoprolol if SBP < 100.")))
            ]
        }
    ]

    results = []
    all_passed = True
    for case in cases:
        extracted = clinical_entity_extractor.extract(case["text"])
        case_passed = True
        sub_results = []
        for desc, check_fn in case["checks"]:
            passed = bool(check_fn(extracted))
            if not passed:
                case_passed = False
                all_passed = False
            sub_results.append({"check": desc, "passed": passed})

        results.append({
            "test_id": case["test_id"],
            "name": case["name"],
            "passed": case_passed,
            "checks": sub_results
        })

    return {
        "total_test_cases": len(cases),
        "all_passed": all_passed,
        "cases": results
    }


def run_full_attribute_audit():
    """Executes full clinical attribute evaluation and serializes the report."""
    print("=" * 80)
    print("PULSE — Clinical Attribute Accuracy & Structured Handover Evaluation")
    print("=" * 80)

    start_time = time.time()

    print("\n1. Auditing Historical 101-Note Corpus...")
    hist_eval = evaluate_historical_corpus()

    print("2. Auditing Benchmark Schema Fixtures (7 Notes)...")
    fixture_eval = evaluate_schema_fixtures()

    print("3. Executing Controlled Clinical Error Analysis...")
    error_analysis = run_controlled_error_analysis()

    elapsed = time.time() - start_time

    summary = {
        "metadata": {
            "audit_name": "PULSE Clinical Attribute Accuracy and Structured Handover Evaluation",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "environment": {
                "platform": platform.platform(),
                "python_version": sys.version.split()[0],
                "elapsed_seconds": round(elapsed, 2)
            }
        },
        "section_a_historical_corpus": hist_eval,
        "section_b_schema_fixtures_regression": fixture_eval,
        "section_c_controlled_error_analysis": error_analysis
    }

    with open(RESULTS_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 80)
    print("EVALUATION SUMMARY")
    print("=" * 80)
    print(f"Historical 101-Corpus Offset Accuracy:  {hist_eval['source_offset_integrity']['offset_accuracy_pct']}%")
    print(f"Historical Medication Mentions F1:      Strict: {hist_eval['mention_extraction_metrics']['medication_mentions']['strict']['f1']}%, Lenient: {hist_eval['mention_extraction_metrics']['medication_mentions']['lenient']['f1']}%")
    print(f"Historical Investigation Mentions F1:   Strict: {hist_eval['mention_extraction_metrics']['investigation_mentions']['strict']['f1']}%, Lenient: {hist_eval['mention_extraction_metrics']['investigation_mentions']['lenient']['f1']}%")
    print("Historical Attribute Binding Status:    All 7 Relational Attributes marked NOT EVALUABLE (0 gold links)")
    print(f"Controlled Error Analysis:             {error_analysis['total_test_cases']} Test Cases | All Passed: {error_analysis['all_passed']}")
    print(f"Results exported to: {RESULTS_OUTPUT_PATH}")
    print("=" * 80)

    return summary


if __name__ == "__main__":
    run_full_attribute_audit()
