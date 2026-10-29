import os
import sys
import json
import torch
import pytest
from transformers import BertTokenizerFast

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from backend.extraction.label_schema import CATEGORY_MAP, ID2LABEL, LABEL2ID

CORPUS_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "gold_standard_corpus.json")

def map_label(label):
    if label == "NA" or label == "O":
        return "O"
    clean_l = label.replace("B-", "").replace("I-", "")
    return CATEGORY_MAP.get(clean_l, "Other")

def extract_gold_spans_from_tokens(tokens):
    spans = []
    current_span = None

    for tok in tokens:
        raw_label = tok["adjudicated_label"]
        mapped_cat = map_label(raw_label)

        if mapped_cat != "O":
            if current_span and current_span["category"] == mapped_cat:
                current_span["end_char"] = tok["end_char"]
            else:
                if current_span:
                    spans.append(current_span)
                current_span = {
                    "category": mapped_cat,
                    "start_char": tok["start_char"],
                    "end_char": tok["end_char"]
                }
        else:
            if current_span:
                spans.append(current_span)
                current_span = None

    if current_span:
        spans.append(current_span)

    return spans

def create_labels_and_round_trip(raw_text, gold_spans, tokenizer):
    encoding = tokenizer(
        raw_text,
        return_offsets_mapping=True,
        truncation=True,
        max_length=512,
        return_tensors="pt"
    )

    input_ids = encoding["input_ids"].squeeze(0)
    offset_mapping = encoding["offset_mapping"].squeeze(0)

    labels = torch.full((input_ids.shape[0],), -100, dtype=torch.long)

    # Label assignment
    for idx, (sub_start, sub_end) in enumerate(offset_mapping.tolist()):
        if sub_start == 0 and sub_end == 0:
            continue

        matched_span = None
        for span in gold_spans:
            # Overlap check (start < sub_end and end > sub_start)
            if span["start_char"] < sub_end and span["end_char"] > sub_start:
                matched_span = span
                break

        if not matched_span:
            labels[idx] = LABEL2ID["O"]
        else:
            cat = matched_span["category"]
            is_start_of_span = (sub_start == matched_span["start_char"]) or \
                               (idx > 0 and (offset_mapping[idx-1][1] <= matched_span["start_char"]))

            tag = f"B-{cat}" if is_start_of_span else f"I-{cat}"
            labels[idx] = LABEL2ID.get(tag, LABEL2ID["O"])

    # Decoding spans back
    decoded_spans = []
    current_span = None

    for idx, (sub_start, sub_end) in enumerate(offset_mapping.tolist()):
        if sub_start == 0 and sub_end == 0: continue
        tag = ID2LABEL.get(labels[idx].item(), "O")

        if tag.startswith("B-"):
            if current_span: decoded_spans.append(current_span)
            current_span = {"category": tag[2:], "start_char": sub_start, "end_char": sub_end}
        elif tag.startswith("I-"):
            cat = tag[2:]
            if current_span and current_span["category"] == cat:
                current_span["end_char"] = sub_end
            else:
                if current_span: decoded_spans.append(current_span)
                current_span = {"category": cat, "start_char": sub_start, "end_char": sub_end}
        else:
            if current_span:
                decoded_spans.append(current_span)
                current_span = None
    if current_span: decoded_spans.append(current_span)
    return decoded_spans

def test_gold_roundtrip():
    tokenizer = BertTokenizerFast.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")
    with open(CORPUS_PATH, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    passed = 0
    total = 0

    for report in corpus["reports"]:
        raw_text = report["raw_text"]
        tokens = report["tokens"]

        gold_spans = extract_gold_spans_from_tokens(tokens)

        decoded = create_labels_and_round_trip(raw_text, gold_spans, tokenizer)

        total += len(gold_spans)
        for g in gold_spans:
            # Match strict: category + offsets (adjusted for tokenization)
            match = any(d["category"] == g["category"] and d["start_char"] == g["start_char"] and d["end_char"] == g["end_char"] for d in decoded)
            if match: passed += 1

    print(f"Roundtrip Recall across 101 notes: {passed}/{total} ({passed/total*100:.2f}%)")
    assert total > 0, "No spans found!"
    assert passed / total > 0.90, "Round-trip recall too low"

if __name__ == "__main__":
    test_gold_roundtrip()
