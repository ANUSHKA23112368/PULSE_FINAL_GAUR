"""
External Dataset Loader & Normalizer for PULSE
Supports parsing n2c2/i2b2 XML/ConLL formats from a configurable local directory path (PULSE_EXTERNAL_DATA_DIR).
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("pulse.dataset.loader")

class ExternalDatasetLoader:
    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or os.environ.get("PULSE_EXTERNAL_DATA_DIR", "./data/external")
        self.stats = {"mapped": 0, "dropped": 0, "unknown": 0}

    def load_i2b2_txt_annotations(self, txt_path: str, ann_path: str) -> Dict[str, Any]:
        """
        Parses standard i2b2/n2c2 span annotation files (.ann) paired with raw text (.txt).
        Format: c="problem..." 10 15|t="..."
        """
        if not os.path.exists(txt_path):
            raise FileNotFoundError(f"Raw text file not found: {txt_path}")

        with open(txt_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        spans = []
        if os.path.exists(ann_path):
            with open(ann_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # Example i2b2 format: T1	Problem 10 15	headache
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        tag_info = parts[1].split()
                        label = tag_info[0]
                        try:
                            start = int(tag_info[1])
                            end = int(tag_info[2])
                            text_snippet = parts[2]

                            mapped_label = self._map_external_label(label)
                            if mapped_label:
                                spans.append({
                                    "start_char": start,
                                    "end_char": end,
                                    "category": mapped_label,
                                    "text": text_snippet,
                                    "source_label": label
                                })
                                self.stats["mapped"] += 1
                            else:
                                self.stats["dropped"] += 1
                        except (ValueError, IndexError):
                            self.stats["unknown"] += 1

        return {
            "report_id": os.path.basename(txt_path),
            "raw_text": raw_text,
            "entity_spans": spans,
            "source": "external_i2b2_n2c2"
        }

    def _map_external_label(self, label: str) -> Optional[str]:
        l_lower = label.lower()
        if "problem" in l_lower or "disease" in l_lower or "condition" in l_lower:
            return "Clinical_Condition"
        elif "treatment" in l_lower or "drug" in l_lower or "medication" in l_lower:
            return "Medication"
        elif "test" in l_lower or "investigation" in l_lower or "procedure" in l_lower:
            return "Investigation_Procedure"
        elif "observation" in l_lower or "symptom" in l_lower:
            return "Clinical_Observation"
        else:
            self.stats["unknown"] += 1
            return None

    def load_directory(self) -> List[Dict[str, Any]]:
        """Scans the external data directory for pairs of .txt and .ann files."""
        documents = []
        if not os.path.exists(self.data_dir):
            logger.warning(f"External data directory {self.data_dir} does not exist. Returning empty list.")
            return documents

        for fname in os.listdir(self.data_dir):
            if fname.endswith(".txt"):
                base_name = os.path.splitext(fname)[0]
                txt_path = os.path.join(self.data_dir, fname)
                ann_path = os.path.join(self.data_dir, f"{base_name}.ann")
                try:
                    doc = self.load_i2b2_txt_annotations(txt_path, ann_path)
                    documents.append(doc)
                except Exception as e:
                    logger.error(f"Error loading external document {fname}: {e}")

        logger.info(f"Loaded {len(documents)} external documents. Stats: {self.stats}")
        return documents
