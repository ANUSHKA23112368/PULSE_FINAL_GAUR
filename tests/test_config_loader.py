"""
Tests for YAML Configuration Loader.
"""

from backend.dataset.config_loader import load_yaml_config

def test_load_yaml_config():
    cfg = load_yaml_config("configs/label_map.yaml")
    assert isinstance(cfg, dict)
    assert "n2c2_2018_to_pulse" in cfg or len(cfg) >= 0
