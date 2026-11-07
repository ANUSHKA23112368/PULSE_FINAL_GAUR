#!/usr/bin/env python3
"""Train and evaluate the PULSE CRF + lexicon span tagger.

Why this exists
---------------
A 110M-parameter BERT fine-tuned on 101 notes over-fits and reaches ~37 strict
F1. A conditional random field over token shape/word/character features plus a
train-only gazetteer generalises far better at this corpus size.

Every number printed here is measured on held-out gold folds.

    python scripts/train_hybrid_ner.py            # 5-fold evaluation
    python scripts/train_hybrid_ner.py --save     # evaluate, then fit on all gold
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "scripts"))

import sklearn_crfsuite  # noqa: E402

from evaluate_hybrid_ner import (  # noqa: E402
    build_gazetteer,
    load_gold,
    predict_spans,
    prf,
    score,
)
from backend.extraction.hybrid_ner_features import (  # noqa: E402
    clean_spans,
    normalize_surface,
    tags_to_spans,
    token_features,
    tokenize,
)

SPLITS_PATH = os.path.join(BASE, "data", "gold_standard", "train_test_splits.json")
MODEL_DIR = os.path.join(BASE, "backend", "models", "hybrid_ner")

METRIC_KEYS = (
    "crf_strict",
    "crf_lenient",
    "gaz_strict",
    "gaz_lenient",
    "merge_strict",
    "merge_lenient",
    "snap_strict",
    "snap_lenient",
)


def tags_for(tokens, spans):
    """Project gold character spans onto BIO token tags."""
    tags = ["O"] * len(tokens)
    for sp in spans:
        first = True
        for i, (s, e, _w) in enumerate(tokens):
            if s >= sp["start_char"] and e <= sp["end_char"]:
                tags[i] = ("B-" if first else "I-") + sp["category"]
                first = False
    return tags


def merge_spans(gaz_spans, crf_spans):
    """Union of both sources; longest span at a given start wins."""
    combined = sorted(
        list(gaz_spans) + list(crf_spans),
        key=lambda s: (s["start_char"], -(s["end_char"] - s["start_char"])),
    )
    out, last_end = [], -1
    for sp in combined:
        if sp["start_char"] < last_end:
            continue
        out.append(sp)
        last_end = sp["end_char"]
    return out


def snap_to_lexicon(crf_spans, gaz_spans):
    """Snap a prediction onto a longer, same-category lexicon phrase it overlaps."""
    out = []
    for sp in crf_spans:
        best = sp
        for g in gaz_spans:
            if g["category"] != sp["category"]:
                continue
            overlap = min(sp["end_char"], g["end_char"]) - max(sp["start_char"], g["start_char"])
            if overlap <= 0:
                continue
            shorter = min(sp["end_char"] - sp["start_char"], g["end_char"] - g["start_char"])
            longer = (g["end_char"] - g["start_char"]) > (sp["end_char"] - sp["start_char"])
            if shorter and overlap / shorter >= 0.6 and longer:
                best = g
        out.append(best)
    return out


def new_crf(c1=0.1, c2=0.1, max_iter=250):
    return sklearn_crfsuite.CRF(
        algorithm="lbfgs",
        c1=c1,
        c2=c2,
        max_iterations=max_iter,
        all_possible_transitions=True,
    )


def build_dataset(reports, ids, gaz):
    X, Y = [], []
    for rid in ids:
        text = reports[rid]["raw_text"]
        tokens = tokenize(text)
        if not tokens:
            continue
        X.append([token_features(tokens, i, gaz) for i in range(len(tokens))])
        Y.append(tags_for(tokens, reports[rid]["spans"]))
    return X, Y


def evaluate(reports, train_ids, test_ids, c1=0.1, c2=0.1, max_iter=250):
    gaz = build_gazetteer(reports, train_ids)
    X_train, Y_train = build_dataset(reports, train_ids, gaz)
    model = new_crf(c1=c1, c2=c2, max_iter=max_iter)
    model.fit(X_train, Y_train)

    agg = {k: [0, 0, 0] for k in METRIC_KEYS}

    for rid in test_ids:
        text = reports[rid]["raw_text"]
        tokens = tokenize(text)
        gold = reports[rid]["spans"]
        crf_spans = []
        if tokens:
            feats = [token_features(tokens, i, gaz) for i in range(len(tokens))]
            crf_spans = clean_spans(tags_to_spans(tokens, model.predict([feats])[0], text), text)
        gaz_spans = clean_spans(predict_spans(text, gaz), text)
        predictions = {
            "crf": crf_spans,
            "gaz": gaz_spans,
            "merge": merge_spans(gaz_spans, crf_spans),
            "snap": snap_to_lexicon(crf_spans, gaz_spans),
        }
        for name, pred in predictions.items():
            for strict, mode in ((True, "strict"), (False, "lenient")):
                tp, fp, fn = score(gold, pred, strict)
                agg[f"{name}_{mode}"][0] += tp
                agg[f"{name}_{mode}"][1] += fp
                agg[f"{name}_{mode}"][2] += fn

    return model, gaz, agg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", default=None, help="single fold name; default all folds")
    parser.add_argument("--save", action="store_true", help="fit on all gold and save the production model")
    parser.add_argument("--max-iter", type=int, default=250)
    parser.add_argument("--c1", type=float, default=0.1)
    parser.add_argument("--c2", type=float, default=0.1)
    args = parser.parse_args()

    reports = load_gold()
    with open(SPLITS_PATH, encoding="utf-8") as fh:
        splits = json.load(fh)

    folds = [args.fold] if args.fold else list(splits.keys())
    totals = {k: [0, 0, 0] for k in METRIC_KEYS}

    for fold in folds:
        train_ids = [str(i) for i in splits[fold]["train"]]
        test_ids = [str(i) for i in splits[fold]["test"]]
        _model, _gaz, agg = evaluate(reports, train_ids, test_ids, c1=args.c1, c2=args.c2, max_iter=args.max_iter)
        print(f"\n{fold}: train {len(train_ids)} / test {len(test_ids)}")
        for name in ("crf", "gaz", "merge", "snap"):
            s = prf(*agg[f"{name}_strict"])
            l = prf(*agg[f"{name}_lenient"])
            print(
                f"  {name:6s} strict P {s[0]:5.2f} R {s[1]:5.2f} F1 {s[2]:5.2f} | "
                f"lenient P {l[0]:5.2f} R {l[1]:5.2f} F1 {l[2]:5.2f}"
            )
        for k in totals:
            for i in range(3):
                totals[k][i] += agg[k][i]

    if len(folds) > 1:
        print("\n=== micro average across folds ===")
        for name in ("crf", "gaz", "merge", "snap"):
            s = prf(*totals[f"{name}_strict"])
            l = prf(*totals[f"{name}_lenient"])
            print(
                f"  {name:6s} strict F1 {s[2]:5.2f} (P {s[0]:.2f} R {s[1]:.2f}) | "
                f"lenient F1 {l[2]:5.2f} (P {l[0]:.2f} R {l[1]:.2f})"
            )

    if args.save:
        all_ids = [str(r) for r in reports]
        gaz = build_gazetteer(reports, all_ids)
        X, Y = build_dataset(reports, all_ids, gaz)
        model = new_crf(c1=args.c1, c2=args.c2, max_iter=args.max_iter)
        model.fit(X, Y)
        os.makedirs(MODEL_DIR, exist_ok=True)
        with open(os.path.join(MODEL_DIR, "crf_model.pkl"), "wb") as fh:
            pickle.dump(model, fh)
        with open(os.path.join(MODEL_DIR, "gazetteer.json"), "w", encoding="utf-8") as fh:
            json.dump(
                {
                    key: {"category": counts.most_common(1)[0][0], "counts": dict(counts)}
                    for key, counts in gaz.items()
                },
                fh,
                ensure_ascii=False,
            )
        metrics = {
            name: {m: prf(*totals[f"{name}_{m}"]) for m in ("strict", "lenient")}
            for name in ("crf", "gaz", "merge", "snap")
        }
        with open(os.path.join(MODEL_DIR, "metrics.json"), "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "folds": folds,
                    "micro": metrics,
                    "params": {"c1": args.c1, "c2": args.c2, "max_iter": args.max_iter},
                    "feature_module": "backend/extraction/hybrid_ner_features.py",
                },
                fh,
                indent=2,
            )
        print(f"\nSaved CRF + gazetteer to {MODEL_DIR}")


if __name__ == "__main__":
    main()
