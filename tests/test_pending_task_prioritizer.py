"""
Tests for Pending Task Prioritizer.
"""

from backend.extraction.pending_task_prioritizer import prioritize_tasks

def test_prioritize_tasks():
    raw = [
        "Routine physio review tomorrow",
        "Stat repeat ECG for ongoing chest pain",
        "Chase pending INR result this afternoon"
    ]
    ranked = prioritize_tasks(raw)
    assert ranked[0]["priority"] == "URGENT"
    assert "Stat" in ranked[0]["task"]
    assert ranked[1]["priority"] == "HIGH"
    assert ranked[2]["priority"] == "ROUTINE"
