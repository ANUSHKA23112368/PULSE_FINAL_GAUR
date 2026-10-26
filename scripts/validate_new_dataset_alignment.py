import os
import glob
import re
from collections import Counter

DOC_DIR = os.path.join(
    "data", "incoming_staging", "dataset",
    "100informationextraction-output-C=1", "documents"
)
TEXT_DIR = os.path.join(
    "data", "incoming_staging", "dataset",
    "100writtenfreetextreports-edited"
)

files = sorted(glob.glob(os.path.join(DOC_DIR, "*.xml.data")))
total_tokens = 0
exact_matches = 0
case_insensitive_matches = 0
missing_tokens = []
label_counts = Counter()
bad_columns = []

for path in files:
    stem = os.path.basename(path).replace(".xml.data", "")
    txt_path = os.path.join(TEXT_DIR, stem + ".txt")

    if not os.path.exists(txt_path):
        print(f"MISSING RAW REPORT: {stem}.txt")
        continue

    with open(txt_path, encoding="utf-8", errors="replace") as f:
        raw = f.read()

    with open(path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    # Locate tokens in order within the original report.
    cursor = 0
    for line_no, line in enumerate(lines, 1):
        cols = line.split()
        if not line.strip():
            continue
        if len(cols) != 19:
            bad_columns.append((stem, line_no, len(cols)))
            continue

        token = cols[0]
        gold = cols[17]  # 18th column: reference label
        total_tokens += 1
        label_counts[gold] += 1

        idx = raw.find(token, cursor)
        if idx >= 0:
            exact_matches += 1
            cursor = idx + len(token)
            continue

        idx = raw.lower().find(token.lower(), cursor)
        if idx >= 0:
            case_insensitive_matches += 1
            cursor = idx + len(token)
        else:
            missing_tokens.append((stem, line_no, token))

print(f"Annotation files: {len(files)}")
print(f"Tokens checked: {total_tokens}")
print(f"Exact sequential matches: {exact_matches}")
print(f"Case-insensitive sequential matches: {case_insensitive_matches}")
print(f"Tokens not located sequentially: {len(missing_tokens)}")
print(f"Unexpected column counts: {len(bad_columns)}")
print(f"Unique gold labels: {len(label_counts)}")

if missing_tokens:
    print("\nFirst 20 tokens not located:")
    for item in missing_tokens[:20]:
        print(item)

if bad_columns:
    print("\nFirst 10 malformed lines:")
    for item in bad_columns[:10]:
        print(item)

print("\nGold-label distribution:")
for label, count in sorted(label_counts.items()):
    print(f"{label}: {count}")
