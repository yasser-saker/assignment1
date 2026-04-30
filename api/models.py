"""Pydantic models for the API."""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ConfigValue(BaseModel):
    path: str
    value: Any


class ConfigResponse(BaseModel):
    success: bool
    config: Dict[str, Any]


class ProjectInfo(BaseModel):
    id: str
    name: str
    type: str
    path: str
    files_count: int = 0
    has_output: bool = False
    output_path: Optional[str] = None
    has_evaluation: bool = False


class PipelineRequest(BaseModel):
    project_id: str
    project_path: Optional[str] = None
    stages: List[str] = Field(default_factory=lambda: ["ingestion", "extraction", "output", "evaluation"])
    force: bool = False


class PipelineStatus(BaseModel):
    project_id: str
    status: str
    current_stage: Optional[str] = None
    progress: float = 0.0
    message: str = ""
    logs: List[str] = Field(default_factory=list)
    output_path: Optional[str] = None


class LineItemSummary(BaseModel):
    description: str
    trade: str
    quantity: Optional[float]
    unit: Optional[str]
    confidence: Union[str, float, int]


class ProjectOutputSummary(BaseModel):
    project_id: str
    project_name: str
    total_line_items: int
    trades: List[str]
    confidence_summary: Dict[str, int]
    line_items: List[LineItemSummary]


class EvaluationSummary(BaseModel):
    project_id: str
    total_predicted: int
    total_expected: int
    matched_count: int
    missing_count: int
    extra_count: int
    match_rate: float
    avg_qty_pct_diff: float


class JobInfo(BaseModel):
    id: str
    project_id: str
    project_path: str
    status: str
    stages: List[Dict[str, Any]]
    current_stage: Optional[str]
    progress: float
    message: str
    output_path: Optional[str]
    evaluation_path: Optional[str]
    created_at: str
    updated_at: str
    completed_at: Optional[str]
    error: Optional[str]


class FolderProjectRequest(BaseModel):
    folder_path: str


class EvaluateRequest(BaseModel):
    project_id: str
    project_path: str
