"""
Tests for Temporal Resolver.
"""

from backend.extraction.temporal_resolver import extract_clock_times

def test_extract_clock_times():
    text = "Reviewed at 14:00, medications given at 08:30 and 10 pm."
    times = extract_clock_times(text)
    assert len(times) == 3
    assert times[0]["expression"] == "14:00"
    assert times[1]["expression"] == "08:30"
