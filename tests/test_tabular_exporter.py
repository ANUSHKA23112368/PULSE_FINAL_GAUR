"""
Tests for Tabular Exporter.
"""

from backend.api.tabular_exporter import export_handover_to_csv

def test_export_handover_to_csv():
    data = {
        "current_condition": ["Condition A", "Condition B"],
        "medications": ["Med C"]
    }
    csv_str = export_handover_to_csv(data)
    assert "Category,Item Index,Description" in csv_str
    assert "current_condition,1,Condition A" in csv_str
