from backend.extraction.gazetteers.lab_panels import is_lab_panel
def test_lab_panels():
    assert is_lab_panel("FBC") is True
    assert is_lab_panel("ABG") is True
    assert is_lab_panel("Aspirin") is False
