#!/usr/bin/env python3
"""Diagnose train/test contamination in the deployed BERT probability cache.

The deployment checkpoint was retrained on every gold note, so predictions on a
fold's test documents are no longer held out. Comparing per-fold train and test
span F1 exposes the gap.
"""

from __future__ import annotations

import json
import os
import pickle
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "scripts"))

from evaluate_hybrid_ner import load_gold, prf, score  # noqa: E402
from backend.extraction.hybrid_ner_features import tags_to_spans  # noqa: E402

CACHE_PATH = os.path.join(BASE, "backend", "models", "hybrid_ner", "bert_token_probs.pkl")
SPLITS_PATH = os.path.join(BASE, "data", "gold_standard", "train_test_splits.json")


def spans_from_cache(entry, text):
    tags = [max(p.items(), key=lambda kv: kv[1])[0] if p else "O" for p in entry["probs"]]
    return tags_to_spans(entry["tokens"], tags, text)


def group_score(cache, reports, ids):
    agg = [0, 0, 0]
    for rid in ids:
        entry = cache.get(rid)
        if not entry:
            continue
        tp, fp, fn = score(reports[rid]["spans"], spans_from_cache(entry, reports[rid]["raw_text"]), strict=True)
        agg[0] += tp
        agg[1] += fp
        agg[2] += fn
    return prf(*agg), len(ids)


def main():
    reports = load_gold()
    with open(CACHE_PATH, "rb") as fh:
        cache = pickle.load(fh)
    with open(SPLITS_PATH, encoding="utf-8") as fh:
        splits = json.load(fh)

    for fold in ("fold_0", "fold_1", "fold_2", "fold_3", "fold_4"):
        train_ids = [str(i) for i in splits[fold]["train"]]
        test_ids = [str(i) for i in splits[fold]["test"]]
        (tp, tr, tf), n_train = group_score(cache, reports, train_ids)
        (ep, er, ef), n_test = group_score(cache, reports, test_ids)
        print(
            f"{fold}: train docs n={n_train:2d} strict F1 {tf:6.2f} | "
            f"test docs n={n_test:2d} strict F1 {ef:6.2f} | gap {tf - ef:6.2f}"
        )

    (p, r, f), n = group_score(cache, reports, list(reports))
    print(f"\nall 101 gold docs (all seen in the deployment retrain): strict P {p:.2f} R {r:.2f} F1 {f:.2f}")


if __name__ == "__main__":
    main()
