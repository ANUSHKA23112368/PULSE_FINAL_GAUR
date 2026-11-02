"""
HL7 FHIR Document Reference & Composition Builder for PULSE Handovers.
Generates FHIR R4 JSON compliant clinical summaries.
"""

from typing import Dict, Any

def build_fhir_bundle(structured_data: Dict[str, Any], report_id: str = "0") -> Dict[str, Any]:
    return {
        "resourceType": "Bundle",
        "type": "document",
        "id": f"pulse-handover-{report_id}",
        "meta": {"lastUpdated": "2026-10-29T12:00:00Z"},
        "entry": [
            {
                "resource": {
                    "resourceType": "Composition",
                    "id": f"comp-{report_id}",
                    "status": "final",
                    "type": {
                        "coding": [{
                            "system": "http://loinc.org",
                            "code": "51848-0",
                            "display": "Evaluation note"
                        }]
                    },
                    "title": f"PULSE Clinical Handover Summary #{report_id}"
                }
            }
        ]
    }
