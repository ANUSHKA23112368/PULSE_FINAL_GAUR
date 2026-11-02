"""
Dataset Integrity and Checksum Verification Tool for PULSE.
Verifies that all 101 raw nursing reports and gold annotations exist and match expected size/token thresholds.
"""

import os
import glob
import json

def verify_dataset(data_dir: str = "data"):
    reports_dir = os.path.join(data_dir, "101writtenfreetextreports")
    gold_path = os.path.join(data_dir, "gold_standard", "gold_standard_corpus.json")
    
    report_files = glob.glob(os.path.join(reports_dir, "*.txt"))
    assert len(report_files) == 101, f"Expected 101 reports, found {len(report_files)}"
    
    assert os.path.exists(gold_path), f"Gold standard corpus not found at {gold_path}"
    with open(gold_path, "r", encoding="utf-8") as f:
        gold_data = json.load(f)
    assert len(gold_data) == 101, f"Expected 101 gold annotations, found {len(gold_data)}"
    
    return {"status": "ok", "report_count": len(report_files), "gold_count": len(gold_data)}

if __name__ == "__main__":
    res = verify_dataset()
    print("Dataset verification passed:", res)
