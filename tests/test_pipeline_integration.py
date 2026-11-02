"""
PULSE Pipeline Integration Test (Stub)
Tests the end-to-end flow from raw text input through NLP pipeline to structured handover output.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


SAMPLE_HANDOVER_TEXTS = [
    "Patient Mary Jones, 68F, Bed 3B. Admitted with acute exacerbation of COPD. "
    "On salbutamol 2.5mg nebulised QID and prednisolone 50mg PO OD. "
    "SpO2 92% on 2L O2 via nasal prongs. Chest X-ray ordered this morning. "
    "Follow up with respiratory team for review at 14:00.",

    "John Smith 45M Bed 7. Post-op day 2 right hip replacement. "
    "Pain 6/10, given oxycodone 5mg PO PRN at 02:00. IV fluids ceased. "
    "Physio to review for mobility assessment. "
    "INR result pending - repeat at 06:00.",

    "Mrs Chen 82F ICU Bed 2. Septic shock secondary to UTI. "
    "Noradrenaline 0.1 mcg/kg/min, weaning. Piperacillin-tazobactam 4.5g IV Q8H Day 3. "
    "Urine output 35ml/h last 4 hours. Lactate trending down 2.1 → 1.4. "
    "BSL 9.2 - insulin infusion titrated per protocol.",
]


class TestPipelineIntegration:
    """Integration stub tests for the full PULSE NLP pipeline."""

    def test_sample_texts_are_non_empty(self):
        """Ensure all sample handover texts are non-empty and sufficiently long."""
        for text in SAMPLE_HANDOVER_TEXTS:
            assert len(text) > 50, f"Sample text too short: {text[:40]}..."
            assert isinstance(text, str), "All samples must be strings"

    def test_sample_texts_contain_clinical_tokens(self):
        """Check that sample texts contain expected clinical tokens."""
        clinical_tokens = ["mg", "IV", "PO", "PRN", "QID", "SpO2", "ICU", "Bed"]
        for text in SAMPLE_HANDOVER_TEXTS:
            found = any(token in text for token in clinical_tokens)
            assert found, f"No clinical tokens found in sample: {text[:50]}..."

    def test_medication_patterns_present(self):
        """Verify at least one sample contains a medication with dosage."""
        dose_patterns = ["mg", "mcg", "ml", "g IV", "g PO", "units"]
        for text in SAMPLE_HANDOVER_TEXTS:
            if any(p in text for p in dose_patterns):
                return
        pytest.fail("No medication dosage patterns found across all samples")

    def test_temporal_tokens_present(self):
        """Verify temporal expressions appear in sample handovers."""
        temporal_tokens = ["00:00", "morning", "today", "Day", ":00", "last"]
        found_temporal = False
        for text in SAMPLE_HANDOVER_TEXTS:
            if any(t in text for t in temporal_tokens):
                found_temporal = True
                break
        assert found_temporal, "No temporal expressions found in sample data"

    def test_pending_task_language_present(self):
        """Verify 'pending', 'follow up', 'review', or 'ordered' language is present."""
        task_tokens = ["pending", "follow up", "review", "ordered", "to review"]
        found_task = False
        for text in SAMPLE_HANDOVER_TEXTS:
            if any(t.lower() in text.lower() for t in task_tokens):
                found_task = True
                break
        assert found_task, "No pending task language found in sample data"

    def test_no_pii_in_samples(self):
        """Ensure sample texts use synthetic names, not real patient PII indicators."""
        pii_red_flags = ["NHS", "Medicare", "SSN", "passport", "DOB:"]
        for text in SAMPLE_HANDOVER_TEXTS:
            for flag in pii_red_flags:
                assert flag not in text, f"Potential PII indicator '{flag}' found in sample"

    @pytest.mark.skip(reason="Requires running backend — integration test, not unit test")
    def test_analyze_endpoint_round_trip(self):
        """
        Full round-trip test: POST /api/analyze and verify structured output.
        Skipped in CI; requires live backend at http://127.0.0.1:8000.
        """
        import httpx
        for text in SAMPLE_HANDOVER_TEXTS[:1]:
            response = httpx.post(
                "http://127.0.0.1:8000/api/analyze",
                json={"text": text, "report_id": "test"},
                timeout=30.0,
            )
            assert response.status_code == 200
            data = response.json()
            assert "structured_handover" in data
