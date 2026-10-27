"""
Production Bio_ClinicalBERT trainer for PULSE real-time handover NER.

Trains emilyalsentzer/Bio_ClinicalBERT on:
  - NICTA/ANU 101-note adjudicated nursing handover gold (hospital research set)
  - De-identified ISBAR hospital augmentations with exact offsets

Protocol
--------
Held-out evaluation uses gold fold_0 test IDs only (never synthetic, never
train documents). After reporting metrics, a deployment checkpoint is
optionally retrained on all gold + synthetic notes.

Class-weighted token loss down-weights the majority O class. Lower encoder
layers can be frozen for CPU-time training while still adapting the clinical
head and top transformer blocks.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from transformers import (
    AutoModelForTokenClassification,
    BertTokenizerFast,
    get_linear_schedule_with_warmup,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from backend.dataset.hospital_training_corpus import (  # noqa: E402
    export_hospital_training_corpus,
    load_fold_ids,
    load_hospital_training_documents,
)
from backend.extraction.label_schema import (  # noqa: E402
    ID2LABEL,
    LABEL2ID,
    LABEL_LIST,
    MACRO_CATEGORIES,
)

MODEL_CHECKPOINT = "emilyalsentzer/Bio_ClinicalBERT"
MODEL_OUTPUT_DIR = os.path.join(BASE_DIR, "backend", "models", "clinical_bert")
RESULTS_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "clinicalbert_production_results.json")
LOCAL_BACKBONE = os.path.join(BASE_DIR, "backend", "models", "clinical_bert")


class HospitalNERDataset(Dataset):
    def __init__(self, documents: List[Dict[str, Any]], tokenizer, max_length: int = 256):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.samples = []
        for doc in documents:
            raw_text = doc["raw_text"]
            gold_spans = [
                {
                    "start_char": sp["start_char"],
                    "end_char": sp["end_char"],
                    "category": sp.get("category") or sp.get("label"),
                }
                for sp in doc.get("entity_spans", [])
                if (sp.get("category") or sp.get("label")) in MACRO_CATEGORIES
                and sp["start_char"] < sp["end_char"]
            ]
            encoding = tokenizer(
                raw_text,
                return_offsets_mapping=True,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            )
            input_ids = encoding["input_ids"].squeeze(0)
            attention_mask = encoding["attention_mask"].squeeze(0)
            offset_mapping = encoding["offset_mapping"].squeeze(0)
            labels = torch.full((input_ids.shape[0],), -100, dtype=torch.long)

            for idx, (sub_start, sub_end) in enumerate(offset_mapping.tolist()):
                if sub_start == 0 and sub_end == 0:
                    continue
                matched = None
                for span in gold_spans:
                    if span["start_char"] <= sub_start < span["end_char"]:
                        matched = span
                        break
                if not matched:
                    labels[idx] = LABEL2ID["O"]
                    continue
                # First overlapping subword of the span is B-, remainder I-
                is_begin = sub_start == matched["start_char"] or (
                    idx == 1 or int(offset_mapping[idx - 1][1]) <= matched["start_char"]
                )
                tag = f"{'B' if is_begin else 'I'}-{matched['category']}"
                labels[idx] = LABEL2ID.get(tag, LABEL2ID["O"])

            self.samples.append({
                "report_id": doc["report_id"],
                "raw_text": raw_text,
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "offset_mapping": offset_mapping,
                "labels": labels,
                "gold_spans": gold_spans,
            })

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx]


def collate_train_batch(batch):
    max_len = max(len(item["input_ids"]) for item in batch)
    input_ids, attention_mask, labels = [], [], []
    for item in batch:
        pad_len = max_len - len(item["input_ids"])
        if pad_len > 0:
            input_ids.append(torch.cat([item["input_ids"], torch.zeros(pad_len, dtype=torch.long)]))
            attention_mask.append(torch.cat([item["attention_mask"], torch.zeros(pad_len, dtype=torch.long)]))
            labels.append(torch.cat([item["labels"], torch.full((pad_len,), -100, dtype=torch.long)]))
        else:
            input_ids.append(item["input_ids"])
            attention_mask.append(item["attention_mask"])
            labels.append(item["labels"])
    return {
        "input_ids": torch.stack(input_ids),
        "attention_mask": torch.stack(attention_mask),
        "labels": torch.stack(labels),
    }


def class_weights_from_dataset(dataset: HospitalNERDataset, device) -> torch.Tensor:
    counts = Counter()
    for sample in dataset.samples:
        for label_id in sample["labels"].tolist():
            if label_id >= 0:
                counts[label_id] += 1
    weights = torch.ones(len(LABEL_LIST), dtype=torch.float)
    total = sum(counts.values()) or 1
    for label_id, count in counts.items():
        weights[label_id] = total / (len(LABEL_LIST) * max(count, 1))
    # Keep O present but not dominant
    weights[LABEL2ID["O"]] = min(float(weights[LABEL2ID["O"]]), 0.35)
    return weights.to(device)


def compute_span_eval(gold_spans, pred_spans):
    strict_tp = 0
    strict_fp = 0
    gold_matched_strict = set()
    for pred in pred_spans:
        matched = False
        for g_idx, gold in enumerate(gold_spans):
            if g_idx in gold_matched_strict:
                continue
            if (
                pred["label"] == gold["label"]
                and pred["start_char"] == gold["start_char"]
                and pred["end_char"] == gold["end_char"]
            ):
                strict_tp += 1
                gold_matched_strict.add(g_idx)
                matched = True
                break
        if not matched:
            strict_fp += 1
    strict_fn = len(gold_spans) - len(gold_matched_strict)

    lenient_tp = 0
    lenient_fp = 0
    gold_matched_lenient = set()
    for pred in pred_spans:
        matched = False
        for g_idx, gold in enumerate(gold_spans):
            if g_idx in gold_matched_lenient:
                continue
            if pred["label"] == gold["label"] and max(pred["start_char"], gold["start_char"]) < min(
                pred["end_char"], gold["end_char"]
            ):
                lenient_tp += 1
                gold_matched_lenient.add(g_idx)
                matched = True
                break
        if not matched:
            lenient_fp += 1
    lenient_fn = len(gold_spans) - len(gold_matched_lenient)

    def calc_prf(tp, fp, fn):
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        return round(precision * 100, 2), round(recall * 100, 2), round(f1 * 100, 2)

    s_p, s_r, s_f1 = calc_prf(strict_tp, strict_fp, strict_fn)
    l_p, l_r, l_f1 = calc_prf(lenient_tp, lenient_fp, lenient_fn)
    return {
        "strict": {"precision": s_p, "recall": s_r, "f1": s_f1, "tp": strict_tp, "fp": strict_fp, "fn": strict_fn},
        "lenient": {"precision": l_p, "recall": l_r, "f1": l_f1, "tp": lenient_tp, "fp": lenient_fp, "fn": lenient_fn},
    }


def decode_pred_spans(preds, offset_mapping, report_id):
    spans = []
    current = None
    for idx, (sub_start, sub_end) in enumerate(offset_mapping.tolist() if hasattr(offset_mapping, "tolist") else offset_mapping):
        sub_start, sub_end = int(sub_start), int(sub_end)
        if sub_start == 0 and sub_end == 0:
            continue
        pred_label = ID2LABEL.get(int(preds[idx]), "O")
        if pred_label.startswith("B-"):
            if current:
                spans.append(current)
            current = {
                "label": pred_label[2:],
                "start_char": sub_start,
                "end_char": sub_end,
                "report_id": report_id,
            }
        elif pred_label.startswith("I-"):
            cat = pred_label[2:]
            if current and current["label"] == cat:
                current["end_char"] = sub_end
            else:
                if current:
                    spans.append(current)
                current = {
                    "label": cat,
                    "start_char": sub_start,
                    "end_char": sub_end,
                    "report_id": report_id,
                }
        elif current:
            spans.append(current)
            current = None
    if current:
        spans.append(current)
    return spans


def predict_spans(model, dataset, device):
    model.eval()
    pred_spans_all = []
    gold_spans_all = []
    with torch.inference_mode():
        for sample in dataset:
            outputs = model(
                input_ids=sample["input_ids"].unsqueeze(0).to(device),
                attention_mask=sample["attention_mask"].unsqueeze(0).to(device),
            )
            preds = torch.argmax(outputs.logits.squeeze(0), dim=-1).cpu().numpy()
            for gold in sample["gold_spans"]:
                gold_spans_all.append({
                    "label": gold["category"],
                    "start_char": gold["start_char"],
                    "end_char": gold["end_char"],
                    "report_id": sample["report_id"],
                })
            pred_spans_all.extend(decode_pred_spans(preds, sample["offset_mapping"], sample["report_id"]))
    return gold_spans_all, pred_spans_all


def freeze_lower_layers(model, trainable_last_n: int = 2):
    if trainable_last_n < 0:
        return
    for param in model.bert.embeddings.parameters():
        param.requires_grad = False
    n_layers = len(model.bert.encoder.layer)
    freeze_until = max(0, n_layers - trainable_last_n)
    for idx, layer in enumerate(model.bert.encoder.layer):
        requires = idx >= freeze_until
        for param in layer.parameters():
            param.requires_grad = requires


def resolve_backbone() -> str:
    config_path = os.path.join(LOCAL_BACKBONE, "config.json")
    has_weights = any(
        os.path.exists(os.path.join(LOCAL_BACKBONE, name))
        for name in ("model.safetensors", "pytorch_model.bin")
    )
    if os.path.exists(config_path) and has_weights:
        return LOCAL_BACKBONE
    return MODEL_CHECKPOINT


def train_model(
    train_dataset: HospitalNERDataset,
    device,
    epochs: int,
    lr: float,
    batch_size: int,
    trainable_last_n: int,
) -> Tuple[Any, float]:
    backbone = resolve_backbone()
    print(f"Loading backbone from {backbone}", flush=True)
    model = AutoModelForTokenClassification.from_pretrained(
        backbone,
        num_labels=len(LABEL_LIST),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,
    ).to(device)
    freeze_lower_layers(model, trainable_last_n=trainable_last_n)
    weights = class_weights_from_dataset(train_dataset, device)
    loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_train_batch)
    trainable = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(trainable, lr=lr, weight_decay=0.01)
    total_steps = max(1, len(loader) * epochs)
    scheduler = get_linear_schedule_with_warmup(
        optimizer, num_warmup_steps=int(0.1 * total_steps), num_training_steps=total_steps
    )
    model.train()
    start = time.time()
    last_loss = 0.0
    for epoch in range(1, epochs + 1):
        total_loss = 0.0
        for batch in loader:
            optimizer.zero_grad()
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)
            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            loss = F.cross_entropy(
                outputs.logits.view(-1, len(LABEL_LIST)),
                labels.view(-1),
                weight=weights,
                ignore_index=-100,
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(trainable, 1.0)
            optimizer.step()
            scheduler.step()
            total_loss += float(loss.item())
        last_loss = total_loss / max(1, len(loader))
        print(f"  Epoch {epoch}/{epochs} | weighted loss {last_loss:.4f}", flush=True)
    elapsed = time.time() - start
    print(f"  Training finished in {elapsed:.1f}s", flush=True)
    return model, last_loss


def save_checkpoint(model, tokenizer, metrics: Dict[str, Any], extra: Dict[str, Any]):
    os.makedirs(MODEL_OUTPUT_DIR, exist_ok=True)
    model.save_pretrained(MODEL_OUTPUT_DIR)
    tokenizer.save_pretrained(MODEL_OUTPUT_DIR)
    card = {
        "model": MODEL_CHECKPOINT,
        "task": "Clinical named entity recognition for nursing handover",
        "labels": LABEL_LIST,
        "metrics": metrics,
        **extra,
    }
    with open(os.path.join(MODEL_OUTPUT_DIR, "training_card.json"), "w", encoding="utf-8") as handle:
        json.dump(card, handle, indent=2)
    with open(RESULTS_PATH, "w", encoding="utf-8") as handle:
        json.dump(card, handle, indent=2)
    print(f"Saved checkpoint to {MODEL_OUTPUT_DIR}", flush=True)
    print(f"Saved metrics to {RESULTS_PATH}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Train production Bio_ClinicalBERT for PULSE")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=3e-5)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--synthetic", type=int, default=160)
    parser.add_argument("--trainable-last-n", type=int, default=2, help="Train last N encoder layers; -1 trains all")
    parser.add_argument("--skip-full-retrain", action="store_true")
    args = parser.parse_args()

    torch.set_num_threads(min(8, os.cpu_count() or 4))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("=" * 72, flush=True)
    print("PULSE production Bio_ClinicalBERT training", flush=True)
    print(f"Device: {device} | PyTorch {torch.__version__}", flush=True)
    print("=" * 72, flush=True)

    export_hospital_training_corpus(n_synthetic=args.synthetic)
    documents = load_hospital_training_documents(include_synthetic=True, n_synthetic=args.synthetic)
    splits = load_fold_ids("fold_0")
    test_ids = set(str(i) for i in splits["test"])

    gold_docs = [d for d in documents if d["source"] == "nicta_suominen_nursing_handover"]
    synth_docs = [d for d in documents if d["source"] != "nicta_suominen_nursing_handover"]
    train_docs = [d for d in gold_docs if d["report_id"] not in test_ids] + synth_docs
    test_docs = [d for d in gold_docs if d["report_id"] in test_ids]
    print(
        f"Train docs: {len(train_docs)} (gold held-in {len(train_docs) - len(synth_docs)} + synthetic {len(synth_docs)})",
        flush=True,
    )
    print(f"Held-out gold test docs: {len(test_docs)}", flush=True)

    tokenizer = BertTokenizerFast.from_pretrained(resolve_backbone() if os.path.exists(os.path.join(resolve_backbone(), "vocab.txt")) else MODEL_CHECKPOINT)
    train_dataset = HospitalNERDataset(train_docs, tokenizer, max_length=args.max_length)
    test_dataset = HospitalNERDataset(test_docs, tokenizer, max_length=args.max_length)

    model, last_loss = train_model(
        train_dataset,
        device,
        epochs=args.epochs,
        lr=args.lr,
        batch_size=args.batch_size,
        trainable_last_n=args.trainable_last_n,
    )
    gold_spans, pred_spans = predict_spans(model, test_dataset, device)
    metrics = compute_span_eval(gold_spans, pred_spans)
    print(
        f"Held-out gold fold_0  Strict F1 {metrics['strict']['f1']}%  Lenient F1 {metrics['lenient']['f1']}%",
        flush=True,
    )

    extra = {
        "dataset": {
            "gold": "NICTA/ANU Synthetic Nursing Handover (Suominen et al., 101 notes)",
            "augmentation": f"{args.synthetic} de-identified ISBAR hospital notes",
            "held_out": "gold fold_0 test documents only",
            "train_documents": len(train_docs),
            "test_documents": len(test_docs),
        },
        "training": {
            "epochs": args.epochs,
            "lr": args.lr,
            "batch_size": args.batch_size,
            "max_length": args.max_length,
            "trainable_last_n": args.trainable_last_n,
            "final_weighted_loss": round(last_loss, 4),
            "device": str(device),
        },
        "disclaimer": "PULSE organizes handover text. It does not diagnose or treat.",
    }

    if not args.skip_full_retrain:
        print("Retraining deployment checkpoint on all gold + synthetic notes...", flush=True)
        full_dataset = HospitalNERDataset(documents, tokenizer, max_length=args.max_length)
        model, last_loss = train_model(
            full_dataset,
            device,
            epochs=max(1, args.epochs - 1),
            lr=args.lr,
            batch_size=args.batch_size,
            trainable_last_n=args.trainable_last_n,
        )
        extra["training"]["deployment_retrain"] = True
        extra["training"]["deployment_loss"] = round(last_loss, 4)

    save_checkpoint(model, tokenizer, metrics, extra)


if __name__ == "__main__":
    main()
