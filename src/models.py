"""Pydantic models for AI Takeoff Builder."""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class Page(BaseModel):
    """Represents a single page from a PDF."""
    page_number: int
    text: str = ""
    is_scanned: bool = False
    ocr_used: bool = False
    ocr_confidence: Optional[float] = None
    ocr_text: Optional[str] = None


class IngestedFile(BaseModel):
    """Represents an ingested PDF file."""
    file_id: str
    project_id: str
    file_name: str
    file_path: str = ""
    file_type: str  # drawing, spec, sow, addendum, rules, breakout, other
    pages: List[Page] = Field(default_factory=list)
    extracted_at: datetime = Field(default_factory=datetime.now)


class LineItem(BaseModel):
    """Represents a single takeoff line item."""
    description: str
    trade: str = ""
    quantity: Optional[float] = None
    unit: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    source_reference: str = ""


class AIRun(BaseModel):
    """Metadata about the AI extraction run."""
    run_id: str
    tools_or_models_used: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class QuantityDifference(BaseModel):
    """Represents a quantity difference for a matched item."""
    description: str
    predicted: float
    expected: float
    pct_diff: float


class EvaluationReport(BaseModel):
    """Evaluation report comparing predictions to expected output."""
    matched_items: int = 0
    missing_items: List[str] = Field(default_factory=list)
    extra_items: List[str] = Field(default_factory=list)
    quantity_differences: List[QuantityDifference] = Field(default_factory=list)
    overall_notes: str = ""


class ProjectOutput(BaseModel):
    """Final output for a project."""
    project_id: str
    trade_scope: str = ""
    input_files_used: List[str] = Field(default_factory=list)
    ai_run: AIRun
    line_items: List[LineItem] = Field(default_factory=list)
    evaluation_when_gold_available: Optional[EvaluationReport] = None

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return self.model_dump_json(indent=2)

    def save(self, path: str) -> None:
        """Save to JSON file."""
        import json
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.model_dump(), f, indent=2, ensure_ascii=False)
