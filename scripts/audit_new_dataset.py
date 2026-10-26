import os
import glob
from collections import Counter

import runpy
_module = runpy.run_path(os.path.join('scripts', 'train_statistical_classifier.py'))
CATEGORY_MAP = _module['CATEGORY_MAP']
map_label = _module['map_label']

base = os.path.join(
    "data", "incoming_staging", "dataset",
    "100informationextraction-output-C=1", "documents"
)

files = sorted(glob.glob(os.path.join(base, "*.data")))

if not files:
    raise SystemExit(f"No .data files found in: {os.path.abspath(base)}")

label_counts = Counter()
column_errors = []

for path in files:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            cols = line.split()

            if len(cols) != 19:
                column_errors.append((os.path.basename(path), line_no, len(cols)))
                continue

            # Column 18 (1-based): reference/gold label.
            # Column 19 (1-based): prediction; NOT used as gold.
            label_counts[cols[17]] += 1

print(f"Annotation files found: {len(files)}")
print(f"Unique reference labels: {len(label_counts)}")
print("\nReference labels and their macro-category mapping:")

for label, count in sorted(label_counts.items()):
    print(f"{label:65} {count:6} -> {map_label(label)}")

print("\nLabels mapped to O (excluding explicit NA/O):")
for label, count in sorted(label_counts.items()):
    if label not in ("NA", "O") and map_label(label) == "O":
        print(f"{label:65} {count:6}")

print(f"\nUnexpected column counts: {len(column_errors)}")
for error in column_errors[:10]:
    print(error)

print("\nMacro categories:")
for category in sorted(set(CATEGORY_MAP.values())):
    print(category)

