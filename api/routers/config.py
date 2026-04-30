"""Config router for settings management."""
from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel

from ..config_manager import load_config, save_config, reset_config, get_config_value, set_config_value

router = APIRouter(prefix="/config", tags=["config"])


class ConfigUpdateRequest(BaseModel):
    path: str
    value: Any


class ConfigUpdateResponse(BaseModel):
    success: bool
    config: Dict[str, Any]


@router.get("/")
def get_full_config() -> Dict[str, Any]:
    """Get full configuration."""
    return load_config()


@router.post("/")
def update_config(req: ConfigUpdateRequest) -> ConfigUpdateResponse:
    """Update a config value by dot path."""
    set_config_value(req.path, req.value)
    return ConfigUpdateResponse(success=True, config=load_config())


@router.get("/{path:path}")
def get_config(path: str) -> Dict[str, Any]:
    """Get config value by dot path."""
    value = get_config_value(path)
    return {"path": path, "value": value}


@router.post("/reset")
def reset_full_config() -> Dict[str, Any]:
    """Reset config to defaults."""
    return reset_config()
