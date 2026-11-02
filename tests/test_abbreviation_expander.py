"""
Tests for Clinical Abbreviation Normalizer.
"""

from backend.extraction.abbreviation_expander import expand_abbreviation

def test_known_abbreviations():
    assert expand_abbreviation("COPD") == "Chronic Obstructive Pulmonary Disease"
    assert expand_abbreviation("bgl") == "Blood Glucose Level"
    assert expand_abbreviation("iv") == "Intravenous"

def test_unknown_abbreviation():
    assert expand_abbreviation("XYZ123") is None
