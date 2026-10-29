import os
import sys
import shutil
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from backend.dataset.external_loader import ExternalDatasetLoader

def test_external_loader_synthetic():
    tmp_dir = tempfile.mkdtemp()
    try:
        # Create fake fixtures
        txt_file = os.path.join(tmp_dir, "sample1.txt")
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write("Patient presents with acute chest pain and receives aspirin.")

        ann_file = os.path.join(tmp_dir, "sample1.ann")
        with open(ann_file, "w", encoding="utf-8") as f:
            f.write("T1\tproblem 26 36\tchest pain\nT2\ttreatment 49 56\taspirin\nT3\tunknown_label 0 7\tPatient")

        loader = ExternalDatasetLoader(data_dir=tmp_dir)
        docs = loader.load_directory()

        assert len(docs) == 1
        doc = docs[0]
        assert doc["report_id"] == "sample1.txt"
        assert len(doc["entity_spans"]) == 2  # unknown_label dropped
        assert doc["entity_spans"][0]["category"] == "Clinical_Condition"
        assert doc["entity_spans"][1]["category"] == "Medication"
        assert loader.stats["mapped"] == 2
        assert loader.stats["dropped"] == 1
        print("External loader synthetic test passed!")
    finally:
        shutil.rmtree(tmp_dir)

if __name__ == "__main__":
    test_external_loader_synthetic()
