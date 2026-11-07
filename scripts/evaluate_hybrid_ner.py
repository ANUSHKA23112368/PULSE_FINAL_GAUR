#!/usr/bin/env python3
"""Evaluate a gazetteer + BIO-consistent span tagger on held-out gold folds.

Reports strict (exact boundary) and lenient (overlap) span P/R/F1 overall and
per category, plus vocabulary coverage, so data changes are judged on evidence
instead of a single optimistic split.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

from backend.extraction.label_schema import CATEGORY_MAP, MACRO_CATEGORIES  # noqa: E402

GOLD_PATH = os.path.join(BASE, "data", "gold_standard", "gold_standard_corpus.json")
SPLITS_PATH = os.path.join(BASE, "data", "gold_standard", "train_test_splits.json")

STRIP_CHARS = " \t\r\n.,;:!?\"'()[]"
WORD_RE = re.compile(r"\S+")


def norm(surface: str) -> str:
    return re.sub(r"\s+", " ", surface).strip(STRIP_CHARS).lower()


def load_gold():
    with open(GOLD_PATH, encoding="utf-8") as fh:
        corpus = json.load(fh)
    reports = {}
    for report in corpus.get("reports", []):
        spans = []
        for sp in report.get("entity_spans", []):
            cat = CATEGORY_MAP.get(sp.get("label", ""), "Other")
            if cat not in MACRO_CATEGORIES:
                continue
            spans.append(
                {
                    "category": cat,
                    "start_char": int(sp["start_char"]),
                    "end_char": int(sp["end_char"]),
                    "text": sp.get("text") or report["raw_text"][sp["start_char"] : sp["end_char"]],
                }
            )
        reports[str(report["report_id"])] = {"raw_text": report["raw_text"], "spans": spans}
    return reports


def build_gazetteer(reports, train_ids):
    gaz = defaultdict(Counter)
    for rid in train_ids:
        for sp in reports[rid]["spans"]:
            key = norm(sp["text"])
            if key:
                gaz[key][sp["category"]] += 1
    return gaz


def predict_spans(text: str, gaz, max_words: int = 8):
    units = [(m.start(), m.end()) for m in WORD_RE.finditer(text)]
    candidates = []
    for i in range(len(units)):
        for n in range(1, max_words + 1):
            j = i + n - 1
            if j >= len(units):
                break
            raw = text[units[i][0] : units[j][1]]
            key = norm(raw)
            if key in gaz:
                lead = len(raw) - len(raw.lstrip(STRIP_CHARS))
                start = units[i][0] + lead
                end = units[i][0] + len(raw.rstrip(STRIP_CHARS))
                if end > start:
                    candidates.append((start, end, n, gaz[key].most_common(1)[0][0]))
    candidates.sort(key=lambda c: (c[0], -c[2]))

    accepted, last_end = [], -1
    for start, end, _n, cat in candidates:
        if start < last_end:
            continue
        accepted.append({"start_char": start, "end_char": end, "category": cat, "text": text[start:end]})
        last_end = end
    return accepted


def score(gold, pred, strict: bool):
    used = set()
    tp = 0
    for p in pred:
        for gi, g in enumerate(gold):
            if gi in used or p["category"] != g["category"]:
                continue
            if strict:
                ok = p["start_char"] == g["start_char"] and p["end_char"] == g["end_char"]
            else:
                ok = max(p["start_char"], g["start_char"]) < min(p["end_char"], g["end_char"])
            if ok:
                used.add(gi)
                tp += 1
                break
    return tp, len(pred) - tp, len(gold) - len(used)


def prf(tp, fp, fn):
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return round(p * 100, 2), round(r * 100, 2), round(f * 100, 2)


def evaluate_fold(reports, train_ids, test_ids, gaz, verbose=True):
    agg = {"strict": [0, 0, 0], "lenient": [0, 0, 0]}
    per_cat = defaultdict(lambda: {"strict": [0, 0, 0], "lenient": [0, 0, 0]})
    missed, spurious = [], []

    for rid in test_ids:
        text = reports[rid]["raw_text"]
        gold = reports[rid]["spans"]
        pred = predict_spans(text, gaz)
        for mode, strict in (("strict", True), ("lenient", False)):
            tp, fp, fn = score(gold, pred, strict)
            agg[mode][0] += tp
            agg[mode][1] += fp
            agg[mode][2] += fn
            for cat in MACRO_CATEGORIES:
                g_cat = [g for g in gold if g["category"] == cat]
                p_cat = [p for p in pred if p["category"] == cat]
                if not g_cat and not p_cat:
                    continue
                ctp, cfp, cfn = score(g_cat, p_cat, strict)
                per_cat[cat][mode][0] += ctp
                per_cat[cat][mode][1] += cfp
                per_cat[cat][mode][2] += cfn
        missed.extend(g for g in gold if not any(
            max(p["start_char"], g["start_char"]) < min(p["end_char"], g["end_char"]) for p in pred
        ))

    if verbose:
        print(f"  strict  P {prf(*agg['strict'])[0]:5.2f}  R {prf(*agg['strict'])[1]:5.2f}  F1 {prf(*agg['strict'])[2]:5.2f}")
        print(f"  lenient P {prf(*agg['lenient'])[0]:5.2f}  R {prf(*agg['lenient'])[1]:5.2f}  F1 {prf(*agg['lenient'])[2]:5.2f}")
        print("  per category (strict F1 / lenient F1):")
        for cat in MACRO_CATEGORIES:
            if cat not in per_cat:
                continue
            s = prf(*per_cat[cat]["strict"])
            l = prf(*per_cat[cat]["lenient"])
            support = sum(per_cat[cat]["strict"][0] + per_cat[cat]["strict"][2] for _ in [0])
            print(f"    {cat:26s} n={support:4d}  strict {s[2]:6.2f}  lenient {l[2]:6.2f}")
        if missed:
            counts = Counter((m["category"], norm(m["text"])) for m in missed)
            print("  most missed spans:")
            for (cat, text), n in counts.most_common(12):
                print(f"    {cat:26s} {text!r} x{n}")

    return agg, per_cat, missed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", default="fold_0")
    parser.add_argument("--all-folds", action="store_true")
    args = parser.parse_args()

    reports = load_gold()
    with open(SPLITS_PATH, encoding="utf-8") as fh:
        splits = json.load(fh)

    folds = list(splits.keys()) if args.all_folds else [args.fold]
    totals = {"strict": [0, 0, 0], "lenient": [0, 0, 0]}

    for fold in folds:
        train_ids = [str(i) for i in splits[fold]["train"]]
        test_ids = [str(i) for i in splits[fold]["test"]]
        gaz = build_gazetteer(reports, train_ids)

        total = hit = cat_hit = 0
        for rid in test_ids:
            for g in reports[rid]["spans"]:
                total += 1
                key = norm(g["text"])
                if key in gaz:
                    hit += 1
                    if gaz[key].most_common(1)[0][0] == g["category"]:
                        cat_hit += 1

        print(f"\n{fold}: train {len(train_ids)} docs / test {len(test_ids)} docs")
        print(
            f"  vocabulary coverage on test: {hit}/{total} spans seen in training "
            f"({100 * hit / max(1, total):.1f}%), correct-category {100 * cat_hit / max(1, total):.1f}%"
        )
        agg, _per_cat, _missed = evaluate_fold(reports, train_ids, test_ids, gaz, verbose=True)
        for mode in ("strict", "lenient"):
            for i in range(3):
                totals[mode][i] += agg[mode][i]

    if args.all_folds:
        print("\n=== micro average across folds ===")
        print(f"  strict  P {prf(*totals['strict'])[0]:5.2f}  R {prf(*totals['strict'])[1]:5.2f}  F1 {prf(*totals['strict'])[2]:5.2f}")
        print(f"  lenient P {prf(*totals['lenient'])[0]:5.2f}  R {prf(*totals['lenient'])[1]:5.2f}  F1 {prf(*totals['lenient'])[2]:5.2f}")


if __name__ == "__main__":
    main()
