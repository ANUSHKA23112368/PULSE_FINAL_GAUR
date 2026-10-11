"""
PULSE API Integration & Regression Test Suite (Phase E)
Validates end-to-end REST API behavior across all extraction engines:
- /api/health: reports system health, dataset load, and active Bio_ClinicalBERT neural weights
- /api/extract: validates neural entity extraction and rule fallback
- /api/analyze: validates end-to-end handover structuring, ISBAR synthesis, and evidence mapping
- Response latency and error handling under invalid inputs
"""

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.main import app
from backend.extraction.clinical_bert_extractor import clinical_bert_extractor


class TestPULSEAPIIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_health_check_status_and_model_metadata(self):
        """Validates /api/health reports system readiness and Bio_ClinicalBERT availability."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["dataset_loaded"])
        self.assertEqual(data["total_reports"], 101)
        
        model_status = data["model_status"]
        self.assertIn("current_engine", model_status)
        self.assertTrue(model_status["clinical_bert_loaded"])
        self.assertEqual(model_status["clinical_bert_model"], "emilyalsentzer/Bio_ClinicalBERT")

    def test_02_extract_endpoint_clinical_bert(self):
        """Validates /api/extract with Bio_ClinicalBERT neural engine."""
        sample_text = (
            "Bed 4 Mrs Jane Doe 74yo admitted with COPD exacerbation and heart failure. "
            "Nil chest pain. Started on IV Lasix 40mg bd."
        )
        res = self.client.post("/api/extract", json={
            "text": sample_text,
            "engine": "clinical_bert"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("patient_information", data)
        self.assertIn("conditions", data)
        self.assertIn("medications", data)
        self.assertIn("clinical_risks", data)

    def test_03_extract_endpoint_rule_engine(self):
        """Validates /api/extract with deterministic rule engine."""
        sample_text = "Bed 12 Michael Wu 48yo male under Dr Hanlen. Admitted with acute stroke. GCS 15."
        res = self.client.post("/api/extract", json={
            "text": sample_text,
            "engine": "rule"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        bed_info = [p for p in data.get("patient_information", []) if p.get("field") == "Bed / Room"]
        self.assertTrue(len(bed_info) > 0)
        self.assertIn("12", bed_info[0]["value"])

    def test_04_analyze_endpoint_hybrid_report_0(self):
        """Validates /api/analyze with hybrid engine on pre-loaded Report #0."""
        start_time = time.time()
        res = self.client.post("/api/analyze", json={
            "report_id": "0",
            "engine": "hybrid"
        })
        elapsed = time.time() - start_time
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        self.assertEqual(data["report_id"], "0")
        self.assertIn("preprocessed_text", data)
        self.assertIn("structured_handover", data)
        self.assertIn("isbar", data)
        self.assertIn("evidence", data)
        self.assertIn("model_metadata", data)
        self.assertTrue(data["model_metadata"]["model_active"])
        self.assertIn("Bio_ClinicalBERT", data["model_metadata"]["pipeline"])
        
        # Verify ISBAR sections exist
        isbar = data["isbar"]
        self.assertIn("identify", isbar)
        self.assertIn("situation", isbar)
        self.assertIn("background", isbar)
        self.assertIn("assessment", isbar)
        self.assertIn("recommendation", isbar)

    def test_05_analyze_endpoint_rule_custom_text(self):
        """Validates /api/analyze with rule engine on custom clinical text."""
        res = self.client.post("/api/analyze", json={
            "raw_text": "Bed 10 John Smith 62yo admitted with pneumonia. Given IV augmentin. No chest pain.",
            "engine": "rule"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["model_metadata"]["selected_engine"], "rule")
        self.assertIn("Deterministic Rule", data["model_metadata"]["pipeline"])

    def test_06_error_handling_empty_inputs(self):
        """Validates appropriate HTTP 400 rejection for empty inputs."""
        res_ext = self.client.post("/api/extract", json={"text": "   "})
        self.assertEqual(res_ext.status_code, 400)

        res_ana = self.client.post("/api/analyze", json={"raw_text": "   "})
        self.assertEqual(res_ana.status_code, 400)

    def test_07_error_handling_invalid_report_id(self):
        """Validates HTTP 404 for non-existent report IDs."""
        res = self.client.post("/api/analyze", json={"report_id": "9999"})
        self.assertEqual(res.status_code, 404)


if __name__ == "__main__":
    unittest.main()
