"""
Tests for Vital Signs Normalizer.
"""

from backend.extraction.vitals_normalizer import parse_vital_measurement

def test_parse_bp():
    res = parse_vital_measurement("Patient BP: 145/95 on admission")
    assert res is not None
    assert res["metric"] == "blood_pressure"
    assert res["systolic"] == 145
    assert res["diastolic"] == 95
    assert res["abnormal"] is True

def test_parse_hr():
    res = parse_vital_measurement("HR 72 bpm regular")
    assert res is not None
    assert res["value"] == 72
    assert res["abnormal"] is False

def test_parse_spo2():
    res = parse_vital_measurement("SpO2 91% on room air")
    assert res is not None
    assert res["value"] == 91
    assert res["abnormal"] is True
