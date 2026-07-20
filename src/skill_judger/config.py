"""Loads model_config.yaml (tracked template with safe placeholders) merged
with model_config.local.yaml (gitignored, real values) if present. Local
values win. Never touched by git pulls since the local file is untracked."""
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "model_config.yaml"
LOCAL_CONFIG_PATH = PROJECT_ROOT / "config" / "model_config.local.yaml"


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_model_config(
    config_path: Path = CONFIG_PATH, local_path: Path = LOCAL_CONFIG_PATH
) -> dict:
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}

    if local_path.exists():
        with open(local_path) as f:
            local_config = yaml.safe_load(f) or {}
        config = _deep_merge(config, local_config)

    return config
