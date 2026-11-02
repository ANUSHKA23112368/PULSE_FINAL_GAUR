# PULSE Model Benchmark Card

## Official Evaluation Results (101 Synthetic Nursing Handovers)

| Paradigm | Strict Precision | Strict Recall | Strict F1 | Lenient F1 |
|---|---|---|---|---|
| Rule Engine Baseline | 44.48% | 17.26% | 24.84% | 47.72% |
| Statistical Sequence Classifier | 47.48% | 58.09% | 52.20% | 80.19% |
| Bio_ClinicalBERT (Unaligned) | 12.56% | 10.64% | 11.38% | 47.72% |
| **Bio_ClinicalBERT (Production - Fold 0)** | **58.42%** | **61.20%** | **59.78%** | **84.50%** |

- Evaluated with exact character-level verbatim offsets.
- Fold 0 test split: 20 held-out notes.
