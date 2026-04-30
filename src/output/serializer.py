"""Output serialization."""
from pathlib import Path
from typing import List, Optional

from src.models import ProjectOutput, LineItem, AIRun, EvaluationReport


class OutputSerializer:
    """Serializes project output to JSON."""

    def create_output(
        self,
        project_id: str,
        trade_scope: str,
        input_files: List[str],
        line_items: List[LineItem],
        ai_run: AIRun,
        evaluation: Optional[EvaluationReport] = None
    ) -> ProjectOutput:
        """Create project output object."""
        return ProjectOutput(
            project_id=project_id,
            trade_scope=trade_scope,
            input_files_used=input_files,
            ai_run=ai_run,
            line_items=line_items,
            evaluation_when_gold_available=evaluation
        )

    def save(self, output: ProjectOutput, directory: str) -> str:
        """Save output to JSON file."""
        out_dir = Path(directory)
        out_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = out_dir / "prediction.json"
        output.save(str(file_path))
        
        return str(file_path)
