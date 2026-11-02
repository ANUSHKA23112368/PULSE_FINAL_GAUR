"""
Unit tests for PULSE dataset validation utility.
"""

import os
import pytest
from scripts.validate_dataset_integrity import verify_dataset

def test_verify_dataset():
    if not os.path.exists("data/101writtenfreetextreports"):
        pytest.skip("Dataset directory not found in test execution path")
    res = verify_dataset()
    assert res["status"] == "ok"
    assert res["report_count"] == 101
    assert res["gold_count"] == 101
