"""
PULSE — Benchmark Manifest & Annotation Validation CLI
Audits independent benchmark datasets, validates schema constraints, and evaluates
lifecycle stages without fabricating data, annotators, or regulatory approvals.

Usage:
    python scripts/validate_benchmark_manifest.py --manifest data/gold_standard/benchmark_manifest_template.json
    python scripts/validate_benchmark_manifest.py --annotations data/gold_standard/benchmark_annotation_example.json
    python scripts/validate_benchmark_manifest.py --check-all
"""

import argparse
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from backend.dataset.benchmark_validator import (
    BenchmarkAnnotationValidator,
    BenchmarkLifecycleEvaluator,
)


def validate_manifest_cli(manifest_path: str) -> int:
    print("=" * 80)
    print("PULSE BENCHMARK MANIFEST AUDIT & LIFECYCLE EVALUATION")
    print("=" * 80)
    print(f"Manifest File: {manifest_path}")

    if not os.path.exists(manifest_path):
        print(f"ERROR: Manifest file not found: {manifest_path}")
        return 1

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to parse JSON: {e}")
        return 1

    report = BenchmarkLifecycleEvaluator.evaluate_manifest_readiness(manifest, base_dir=BASE_DIR)

    print("\n[LIFECYCLE READINESS STAGES]")
    stages = [
        ("Stage 1: Protocol Created", report["protocol_created"]),
        ("Stage 2: Data Collected", report["data_collected"]),
        ("Stage 3: Annotations Completed", report["annotations_completed"]),
        ("Stage 4: Annotations Adjudicated", report["annotations_adjudicated"]),
        ("Stage 5: Ready for Evaluation", report["benchmark_ready_for_evaluation"]),
    ]

    for stage_name, status in stages:
        mark = "[PASS]" if status else "[PENDING]"
        print(f"  {mark:<9} {stage_name}")

    print(f"\nGovernance Status: {report['governance_status']}")

    if report["blocking_reasons"]:
        print("\n[BLOCKING PREREQUISITES / UNRESOLVED GATES]")
        for idx, reason in enumerate(report["blocking_reasons"], 1):
            print(f"  {idx}. {reason}")
    else:
        print("\nAll benchmark readiness criteria fulfilled.")

    print("\nEvidence:")
    for k, v in report["evidence"].items():
        print(f"  - {k}: {v}")

    print("=" * 80)
    return 0


def validate_annotations_cli(annotations_path: str) -> int:
    print("=" * 80)
    print("PULSE BENCHMARK ANNOTATION SCHEMA & RELATIONAL INTEGRITY VALIDATION")
    print("=" * 80)
    print(f"Annotations File: {annotations_path}")

    if not os.path.exists(annotations_path):
        print(f"ERROR: File not found: {annotations_path}")
        return 1

    try:
        with open(annotations_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to parse JSON: {e}")
        return 1

    validator = BenchmarkAnnotationValidator()
    result = validator.validate_corpus(data)

    print(f"\nValidation Status: {'PASS' if result.is_valid else 'FAIL'}")
    print(f"Documents Checked: {result.stats['documents_checked']}")
    print(f"Entities Checked:  {result.stats['entities_checked']}")
    print(f"Relationships Checked: {result.stats['relationships_checked']}")
    print(f"Conditional Directives Checked: {result.stats['conditional_directives_checked']}")
    print(f"Splits Checked: {result.stats['splits_checked']}")

    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        for w in result.warnings:
            print(f"  [WARN] {w}")

    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for e in result.errors:
            print(f"  [FAIL] {e}")
        print("=" * 80)
        return 1

    print("\nAll entity offsets, verbatim slices, relational endpoints, and enums verified.")
    print("=" * 80)
    return 0


def main():
    parser = argparse.ArgumentParser(description="PULSE Benchmark Manifest & Annotation Validation CLI")
    parser.add_argument("--manifest", type=str, help="Path to benchmark manifest JSON")
    parser.add_argument("--annotations", type=str, help="Path to benchmark annotations JSON")
    parser.add_argument("--check-all", action="store_true", help="Run validation on default template and example")

    args = parser.parse_args()

    exit_code = 0
    if args.check_all or (not args.manifest and not args.annotations):
        default_manifest = os.path.join(BASE_DIR, "data", "gold_standard", "benchmark_manifest_template.json")
        default_anno = os.path.join(BASE_DIR, "data", "gold_standard", "benchmark_annotation_example.json")

        code1 = validate_manifest_cli(default_manifest)
        print("\n")
        code2 = validate_annotations_cli(default_anno)
        exit_code = max(code1, code2)
    else:
        if args.manifest:
            code = validate_manifest_cli(args.manifest)
            exit_code = max(exit_code, code)
        if args.annotations:
            code = validate_annotations_cli(args.annotations)
            exit_code = max(exit_code, code)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
