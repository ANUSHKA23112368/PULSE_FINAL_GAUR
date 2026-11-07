#!/usr/bin/env python3
"""Stack Bio_ClinicalBERT token probabilities as features for the CRF tagger.

The deployed BERT is a high-recall span proposer (lenient recall ~96%) with weak
boundaries; the CRF is boundary-disciplined but vocabulary-limited. Feeding
BERT's per-token label distribution into the CRF gives the sequence model the
encoder's generalisation while keeping BIO-consistent decoding.

    python scripts/train_bert_crf_ner.py            # 5-fold evaluation
    python scripts/train_bert_crf_ner.py --rebuild  # ignore cached BERT probs
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys

import numpy as np
import torch
from transformers import AutoModelForTokenClassification, BertTokenizerFast

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "scripts"))

from evaluate_hybrid_ner import build_gazetteer, load_gold, prf, score  # noqa: E402
from backend.extraction.hybrid_ner_features import (  # noqa: E402
    token_features,
    tokenize,
)
from backend.extraction.label_schema import ID2LABEL  # noqa: E402
from train_hybrid_ner import new_crf, tags_for  # noqa: E402

BERT_DIR = os.path.join(BASE, "backend", "models", "clinical_bert")
SPLITS_PATH = os.path.join(BASE, "data", "gold_standard", "train_test_splits.json")
CACHE_PATH = os.path.join(BASE, "backend", "models", "hybrid_ner", "bert_token_probs.pkl")


def bucket(prob: float) -> str:
    for edge in (0.3, 0.5, 0.7, 0.9):
        if prob < edge:
            return f"lt{int(edge * 100)}"
    return "ge90"


def load_bert():
    tokenizer = BertTokenizerFast.from_pretrained(BERT_DIR)
    model = AutoModelForTokenClassification.from_pretrained(BERT_DIR)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device).eval()
    if device.type == "cpu":
        torch.set_num_threads(min(8, os.cpu_count() or 4))
    return tokenizer, model, device


def bert_probs_for_doc(text, tokenizer, model, device):
    encoding = tokenizer(
        text,
        return_offsets_mapping=True,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    )
    offsets = encoding["offset_mapping"][0].tolist()
    with torch.inference_mode():
        logits = model(
            input_ids=encoding["input_ids"].to(device),
            attention_mask=encoding["attention_mask"].to(device),
        ).logits[0]
    return offsets, torch.softmax(logits, dim=-1).cpu().numpy()


def word_level_probs(tokens, offsets, probs):
    """Average subword distributions onto each word token."""
    out = []
    for (start, end, _word) in tokens:
        idxs = [j for j, (a, b) in enumerate(offsets) if b > a and a < end and b > start]
        if not idxs:
            out.append(None)
            continue
        averaged = probs[idxs].mean(axis=0)
        out.append({ID2LABEL[k]: float(averaged[k]) for k in range(len(averaged))})
    return out


def build_cache(reports, rebuild=False):
    if os.path.exists(CACHE_PATH) and not rebuild:
        older = os.path.getmtime(CACHE_PATH) > os.path.getmtime(os.path.join(BERT_DIR, "model.safetensors"))
        if older:
            with open(CACHE_PATH, "rb") as fh:
                cached = pickle.load(fh)
            if set(cached) == set(reports):
                print(f"Using cached BERT probabilities ({len(cached)} documents)")
                return cached

    print("Scoring corpus with the deployed Bio_ClinicalBERT checkpoint...")
    tokenizer, model, device = load_bert()
    cache = {}
    for n, (rid, rep) in enumerate(reports.items(), 1):
        text = rep["raw_text"]
        tokens = tokenize(text)
        offsets, probs = bert_probs_for_doc(text, tokenizer, model, device)
        cache[rid] = {"tokens": tokens, "probs": word_level_probs(tokens, offsets, probs)}
        if n % 25 == 0:
            print(f"  {n}/{len(reports)} documents", flush=True)
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "wb") as fh:
        pickle.dump(cache, fh)
    print(f"Cached BERT probabilities to {CACHE_PATH}")
    return cache


def features_with_bert(tokens, i, gaz, word_probs, tops):
    feats = token_features(tokens, i, gaz)
    probs = word_probs[i]
    if probs:
        top, top_prob = tops[i]
        feats["bert_top=" + top] = 1.0
        feats["bert_p=" + bucket(top_prob)] = 1.0
        feats["bert_top_prob"] = round(top_prob, 2)
        if i > 0 and tops[i - 1][0] != top and top != "O":
            feats["bert_start=" + top] = 1.0
        if i + 1 < len(tokens) and tops[i + 1][0] != top and top != "O":
            feats["bert_end=" + top] = 1.0
        ranked = sorted(probs.items(), key=lambda kv: -kv[1])
        if len(ranked) > 1 and ranked[1][1] >= 0.2:
            feats["bert_alt=" + ranked[1][0]] = 1.0
    return feats


def dataset_for(ids, cache, gaz, reports):
    X, Y = [], []
    for rid in ids:
        tokens = cache[rid]["tokens"]
        if not tokens:
            continue
        word_probs = cache[rid]["probs"]
        tops = [
            (max(p.items(), key=lambda kv: kv[1]) if p else ("O", 0.0))
            for p in word_probs
        ]
        X.append([features_with_bert(tokens, i, gaz, word_probs, tops) for i in range(len(tokens))])
        Y.append(tags_for(tokens, reports[rid]["spans"]))
    return X, Y


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true", help="recompute cached BERT probabilities")
    parser.add_argument("--fold", default=None)
    parser.add_argument("--c1", type=float, default=0.1)
    parser.add_argument("--c2", type=float, default=0.1)
    parser.add_argument("--max-iter", type=int, default=250)
    args = parser.parse_args()

    reports = load_gold()
    print(
        "WARNING: the deployed checkpoint was retrained on all 101 gold notes, so these\n"
        "BERT features leak the held-out labels. Use scripts/eval_bert_crf_fold.py for a\n"
        "leak-free measurement; this script only shows the optimistic upper bound.",
        flush=True,
    )
    with open(SPLITS_PATH, encoding="utf-8") as fh:
        splits = json.load(fh)
    cache = build_cache(reports, rebuild=args.rebuild)

    folds = [args.fold] if args.fold else list(splits.keys())
    totals = {"strict": [0, 0, 0], "lenient": [0, 0, 0]}

    for fold in folds:
        train_ids = [str(i) for i in splits[fold]["train"]]
        test_ids = [str(i) for i in splits[fold]["test"]]
        gaz = build_gazetteer(reports, train_ids)
        X_train, Y_train = dataset_for(train_ids, cache, gaz, reports)
        model = new_crf(c1=args.c1, c2=args.c2, max_iter=args.max_iter)
        model.fit(X_train, Y_train)

        X_test, _ = dataset_for(test_ids, cache, gaz, reports)
        predictions = model.predict(X_test)

        agg = {"strict": [0, 0, 0], "lenient": [0, 0, 0]}
        for rid, tags in zip(test_ids, predictions):
            tokens = cache[rid]["tokens"]
            text = reports[rid]["raw_text"]
            spans, current = [], None
            for (s, e, _w), tag in zip(tokens, tags):
                if tag == "O":
                    if current:
                        spans.append(current)
                        current = None
                    continue
                bio, cat = tag.split("-", 1)
                if bio == "B" or current is None or current["category"] != cat:
                    if current:
                        spans.append(current)
                    current = {"category": cat, "start_char": s, "end_char": e, "text": text[s:e]}
                else:
                    current["end_char"] = e
                    current["text"] = text[current["start_char"] : e]
            if current:
                spans.append(current)

            for mode, strict in (("strict", True), ("lenient", False)):
                tp, fp, fn = score(reports[rid]["spans"], spans, strict)
                agg[mode][0] += tp
                agg[mode][1] += fp
                agg[mode][2] += fn

        s = prf(*agg["strict"])
        l = prf(*agg["lenient"])
        print(
            f"{fold}: strict P {s[0]:5.2f} R {s[1]:5.2f} F1 {s[2]:5.2f} | "
            f"lenient P {l[0]:5.2f} R {l[1]:5.2f} F1 {l[2]:5.2f}"
        )
        for mode in totals:
            for i in range(3):
                totals[mode][i] += agg[mode][i]

    if len(folds) > 1:
        s = prf(*totals["strict"])
        l = prf(*totals["lenient"])
        print("\n=== BERT+CRF micro average across folds ===")
        print(f"  strict  P {s[0]:5.2f} R {s[1]:5.2f} F1 {s[2]:5.2f}")
        print(f"  lenient P {l[0]:5.2f} R {l[1]:5.2f} F1 {l[2]:5.2f}")


if __name__ == "__main__":
    main()
