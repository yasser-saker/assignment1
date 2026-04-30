"""Configuration manager for dynamic settings via API."""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

# Config file path
CONFIG_FILE = Path(__file__).parent / "dynamic_config.json"


def _resolve_base_dir() -> Path:
    """Resolve base dir dynamically from the project root (where api/ lives)."""
    # api/config_manager.py -> api/ -> project root
    return Path(__file__).parent.parent.resolve()


def _build_default_config() -> dict:
    """Build default config using dynamically resolved base_dir."""
    base = _resolve_base_dir()
    return {
        "llm": {
            "provider": "kimi",
            "model": "kimi-k2.5",
            "temperature": 0.1,
            "max_tokens": 4000,
            "openai_model": "gpt-4o",
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            "kimi_api_key": os.getenv("KIMI_API_KEY", ""),
            "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        },
        "paths": {
            "base_dir": str(base),
            "data_dir": str(base / "data"),
            "outputs_dir": str(base / "outputs"),
            "sample_projects_dir": str(base / "data" / "sample_projects"),
            "challenge_projects_dir": str(base / "data" / "challenge_projects"),
        },
        "evaluation": {
            "fuzzy_match_threshold": 80,
            "qty_exact_threshold": 5.0,
            "qty_close_threshold": 10.0,
        },
        "ingestion": {
            "ocr_enabled": True,
            "ocr_confidence_threshold": 50,
            "extract_tables": True,
            "chunk_size": 4000,
            "chunk_overlap": 200,
        },
        "pipeline": {
            "max_retries": 3,
            "retry_delay": 2,
            "cache_enabled": True,
            "parallel_processing": False,
        },
        "output": {
            "format": "json",
            "include_confidence_summary": True,
            "include_processing_stats": True,
        }
    }


# Dynamic defaults rebuilt on import
DEFAULT_CONFIG = _build_default_config()


def load_config() -> Dict[str, Any]:
    """Load config from file or return defaults."""
    base = _resolve_base_dir()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # Merge with defaults to ensure all keys exist
            config = DEFAULT_CONFIG.copy()
            _deep_update(config, saved)
            # Always resolve paths dynamically to current location
            config["paths"]["base_dir"] = str(base)
            config["paths"]["data_dir"] = str(base / "data")
            config["paths"]["outputs_dir"] = str(base / "outputs")
            config["paths"]["sample_projects_dir"] = str(base / "data" / "sample_projects")
            config["paths"]["challenge_projects_dir"] = str(base / "data" / "challenge_projects")
            return config
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> None:
    """Save config to file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _deep_update(base: Dict[str, Any], updates: Dict[str, Any]) -> None:
    """Recursively update dict."""
    for key, value in updates.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_update(base[key], value)
        else:
            base[key] = value


def get_config_value(path: str, default: Any = None) -> Any:
    """Get a config value by dot path (e.g., 'llm.temperature')."""
    config = load_config()
    keys = path.split(".")
    current = config
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def set_config_value(path: str, value: Any) -> None:
    """Set a config value by dot path."""
    config = load_config()
    keys = path.split(".")
    current = config
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value
    save_config(config)


def reset_config() -> Dict[str, Any]:
    """Reset config to defaults."""
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()
