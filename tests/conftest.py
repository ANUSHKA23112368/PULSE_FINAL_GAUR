from pathlib import Path

import pytest


@pytest.fixture
def raw_text():
    """Provide a real corpus note for the legacy preprocessing smoke test."""
    project_root = Path(__file__).resolve().parents[1]
    return (project_root / "data" / "101writtenfreetextreports" / "0.txt").read_text(
        encoding="utf-8-sig"
    )
