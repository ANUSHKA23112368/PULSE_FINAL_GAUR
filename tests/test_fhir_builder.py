"""
Tests for HL7 FHIR Builder.
"""

from backend.api.fhir_builder import build_fhir_bundle

def test_build_fhir_bundle():
    bundle = build_fhir_bundle({}, report_id="12")
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "document"
    assert bundle["id"] == "pulse-handover-12"
    assert bundle["entry"][0]["resource"]["resourceType"] == "Composition"
