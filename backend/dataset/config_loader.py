"""
Configuration Loader for PULSE Clinical Pipelines.
Reads YAML configs with environmental overrides.
"""

import os
import yaml
from typing import Dict, Any

def load_yaml_config(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def get_model_config() -> Dict[str, Any]:
    path = os.environ.get("PULSE_MODEL_CONFIG", "configs/model_config.yaml")
    return load_yaml_config(path)
