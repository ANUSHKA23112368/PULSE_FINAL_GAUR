import torch
from transformers import BertTokenizerFast

def test_subword_alignment():
    tokenizer = BertTokenizerFast.from_pretrained("emilyalsentzer/Bio_ClinicalBERT")

    text = "Patient was given 50mg of Aspirin."
    # gold span: "50mg" (index 17 to 21)
    gold_spans = [{"start_char": 17, "end_char": 21, "category": "Medication_Dosage"}]

    encoding = tokenizer(
        text,
        return_offsets_mapping=True,
        return_tensors="pt"
    )

    offset_mapping = encoding["offset_mapping"].squeeze(0)
    input_ids = encoding["input_ids"].squeeze(0)
    labels = torch.full((input_ids.shape[0],), -100, dtype=torch.long)

    # Simulate the logic in train_production_clinicalbert.py
    for idx, (sub_start, sub_end) in enumerate(offset_mapping.tolist()):
        if sub_start == 0 and sub_end == 0:
            continue

        matched = None
        for span in gold_spans:
            if span["start_char"] <= sub_start < span["end_char"]:
                matched = span
                break

        if not matched:
            labels[idx] = 0 # O label
            continue

        # Current logic check:
        is_begin = sub_start == matched["start_char"] or (
            idx == 1 or int(offset_mapping[idx - 1][1]) <= matched["start_char"]
        )

        print(f"Token: {tokenizer.decode(input_ids[idx])}, Offset: ({sub_start}, {sub_end}), IsBegin: {is_begin}")

    print("Labels:", labels)

if __name__ == "__main__":
    test_subword_alignment()
