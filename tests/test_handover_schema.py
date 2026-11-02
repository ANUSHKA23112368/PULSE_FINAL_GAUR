"""
Tests for Handover Pydantic Schemas.
"""

from backend.extraction.handover_schema import HandoverCategoryOutput, PatientDemographics

def test_handover_schema_defaults():
    ho = HandoverCategoryOutput()
    assert ho.patient_info.name is None
    assert len(ho.current_condition) == 0
    assert len(ho.pending_tasks) == 0

def test_handover_schema_population():
    ho = HandoverCategoryOutput(
        patient_info=PatientDemographics(bed="Bed 4B", age=74, gender="Female"),
        current_condition=["COPD exacerbation"],
        medications=["Salbutamol 2.5mg neb"]
    )
    assert ho.patient_info.bed == "Bed 4B"
    assert ho.patient_info.age == 74
    assert len(ho.medications) == 1
