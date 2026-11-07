#!/usr/bin/env python3
"""Leak-free BERT+CRF evaluation for one fold.

The deployed checkpoint cannot be used to generate features for held-out notes:
it was retrained on all 101 gold documents, so its probabilities encode the test
labels (fold_0 test strict F1 rises from 55.76 at evaluation time to 72.62 after
the retrain). This script retrains Bio_ClinicalBERT from the public checkpoint
on the fold's training documents only, then uses its probabilities as CRF
features.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import torch
from transformers import BertTokenizerFast

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "scripts"))

import scripts.train_production_clinicalbert as tpc  # noqa: E402
from backend.dataset.hospital_training_corpus import load_hospital_training_documents  # noqa: E402
from backend.extraction.hybrid_ner_features import tags_to_spans, tokenize  # noqa: E402
from evaluate_hybrid_ner import build_gazetteer, load_gold, prf, score  # noqa: E402
from train_bert_crf_ner import bert_probs_for_doc, features_with_bert, word_level_probs  # noqa: E402
from train_hybrid_ner import new_crf, tags_for  # noqa: E402

SPLITS_PATH = os.path.join(BASE, "data", "gold_standard", "train_test_splits.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", default="fold_0")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--lr", type=float, default=3e-5)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--trainable-last-n", type=int, default=2)
    args = parser.parse_args()

    reports = load_gold()
    with open(SPLITS_PATH, encoding="utf-8") as fh:
        splits = json.load(fh)
    train_ids = [str(i) for i in splits[args.fold]["train"]]
    test_ids = [str(i) for i in splits[args.fold]["test"]]

    docs = load_hospital_training_documents(include_synthetic=True, n_synthetic=160)
    gold_train = [
        d for d in docs
        if d["source"] == "nicta_suominen_nursing_handover" and str(d["report_id"]) in train_ids
    ]
    synthetic = [d for d in docs if d["source"] != "nicta_suominen_nursing_handover"]
    train_docs = gold_train + synthetic

    # Force the public checkpoint so no contaminated local weights are reused.
    tpc.LOCAL_BACKBONE = os.path.join(BASE, "backend", "models", "_absent_by_design")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.set_num_threads(min(8, os.cpu_count() or 4))
    tokenizer = BertTokenizerFast.from_pretrained(tpc.MODEL_CHECKPOINT)
    print(
        f"Training fold-specific BERT on {len(train_docs)} docs "
        f"({len(gold_train)} gold + {len(synthetic)} synthetic), {args.epochs} epochs on {device}",
        flush=True,
    )
    dataset = tpc.HospitalNERDataset(train_docs, tokenizer, max_length=256)
    model, loss = tpc.train_model(
        dataset,
        device,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
        trainable_last_n=args.trainable_last_n,
    )
    print(f"Fold BERT trained, final weighted loss {loss:.4f}", flush=True)

    cache = {}
    for rid in train_ids + test_ids:
        text = reports[rid]["raw_text"]
        tokens = tokenize(text)
        offsets, probs = bert_probs_for_doc(text, tokenizer, model, device)
        cache[rid] = {"tokens": tokens, "probs": word_level_probs(tokens, offsets, probs)}
    print(f"Scored {len(cache)} fold documents with the fold-specific model", flush=True)

    def bert_spans(rid):
        tags = [max(p.items(), key=lambda kv: kv[1])[0] if p else "O" for p in cache[rid]["probs"]]
        return tags_to_spans(cache[rid]["tokens"], tags, reports[rid]["raw_text"])

    def collect(pred_fn):
        agg = {"strict": [0, 0, 0], "lenient": [0, 0, 0]}
        for rid in test_ids:
            spans = pred_fn(rid)
            for mode, strict in (("strict", True), ("lenient", False)):
                tp, fp, fn = score(reports[rid]["spans"], spans, strict)
                for i, value in enumerate((tp, fp, fn)):
                    agg[mode][i] += value
        return agg

    agg = collect(bert_spans)
    s, l = prf(*agg["strict"]), prf(*agg["lenient"])
    print(f"BERT alone  ({args.fold}): strict F1 {s[2]:5.2f} | lenient F1 {l[2]:5.2f}")

    gaz = build_gazetteer(reports, train_ids)

    def dataset_for(ids):
        X, Y = [], []
        for rid in ids:
            tokens = cache[rid]["tokens"]
            word_probs = cache[rid]["probs"]
            tops = [(max(p.items(), key=lambda kv: kv[1]) if p else ("O", 0.0)) for p in word_probs]
            X.append([features_with_bert(tokens, i, gaz, word_probs, tops) for i in range(len(tokens))])
            Y.append(tags_for(tokens, reports[rid]["spans"]))
        return X, Y

    X_train, Y_train = dataset_for(train_ids)
    crf = new_crf()
    crf.fit(X_train, Y_train)
    predictions = crf.predict(dataset_for(test_ids)[0])

    spans_by_id = {
        rid: tags_to_spans(cache[rid]["tokens"], tags, reports[rid]["raw_text"])
        for rid, tags in zip(test_ids, predictions)
    }
    agg = collect(lambda rid: spans_by_id[rid])
    s, l = prf(*agg["strict"]), prf(*agg["lenient"])
    print(
        f"BERT+CRF    ({args.fold}): strict P {s[0]:5.2f} R {s[1]:5.2f} F1 {s[2]:5.2f} | "
        f"lenient P {l[0]:5.2f} R {l[1]:5.2f} F1 {l[2]:5.2f}"
    )


if __name__ == "__main__":
    main()
