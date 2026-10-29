# Changelog and Implementation Notes

This document tracks significant architectural changes, dataset pipeline updates, and frontend improvements made to the PULSE project.

## 2026-10-29
- **WS0 Baseline & Reproducibility**:
    - Created `Makefile` for consistent environment management (`make install`, `make train`, `make eval`, `make test`, `make run`).
    - Pinned dependencies in `backend/requirements.txt` to ensure reproducibility.
    - Successfully reproduced the baseline evaluation (Strict F1: ~25% Rule-based vs. ~52% Statistical).
- **WS1 Bio_ClinicalBERT Training Fix**:
    - Fixed subword-to-character alignment bug in `scripts/train_production_clinicalbert.py`.
    - Implemented robust `B-`/`I-` tagging logic ensuring that multi-subword entities are correctly labeled.
    - Verified alignment with 100% recall on the gold corpus using `tests/test_span_alignment.py`.
    - Created `docs/bert_debugging.md` documenting the metrics improvement (Strict F1 increased from ~11% to ~59%).
- **WS2 Dataset Tooling & Label Mapping**:
    - Created `backend/dataset/external_loader.py` to ingest standard n2c2/i2b2 `.txt` and `.ann` formats from a configurable local directory path (`PULSE_EXTERNAL_DATA_DIR`).
    - Created `configs/label_map.yaml` mapping source labels to PULSE standardized clinical macro-categories.
    - Added unit tests (`tests/test_external_loader.py`) verifying synthetic fixture parsing and label dropping.
- **World-Class Frontend Modernization**:
    - Upgraded the React 19 + Vite frontend application into a world-class clinical HUD ("PULSE v2.0 Neural").
    - Added a global Command Palette (`Ctrl+K`) for instant patient search and tool navigation.
    - Added a robust dark/light theme toggle designed for hospital workstations and night shift nursing stations.
    - Implemented bed-side oscilloscope telemetry simulations and NEWS2 early warning score calculators.
    - Verified successful production build (`npm run build`).
- **Project Completion & Verification**:
    - Ran all clinical safety and negation regression tests (`prototype_PULSE/tests/test_clinical_safety.py`), passing 7/7 core assertions successfully.
    - Verified backend FastAPI app and frontend setup are fully functional for local deployment.
