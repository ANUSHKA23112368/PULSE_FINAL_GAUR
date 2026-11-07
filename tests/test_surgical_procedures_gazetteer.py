from backend.extraction.gazetteers.surgical_procedures import is_surgical_procedure
def test_surgical_procedures():
    assert is_surgical_procedure("CABG") is True
    assert is_surgical_procedure("THR") is True
    assert is_surgical_procedure("Metformin") is False
