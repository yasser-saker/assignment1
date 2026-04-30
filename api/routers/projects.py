"""Projects router for listing and managing projects."""
import json
from pathlib import Path
from typing import List
from fastapi import APIRouter

from ..models import ProjectInfo, ProjectOutputSummary, LineItemSummary, FolderProjectRequest
from ..config_manager import get_config_value

router = APIRouter(prefix="/projects", tags=["projects"])


def _scan_client_projects() -> List[ProjectInfo]:
    """Scan client_files for projects. Handles nested duplicate folder names."""
    base = Path(get_config_value("paths.base_dir", "."))
    results = []
    seen = set()
    
    mappings = [
        ("01_Sample_Projects_With_Expected_Output", "sample"),
        ("02_Challenge_Projects_Project_Files_Only", "challenge"),
    ]
    
    for prefix, ptype in mappings:
        directory = base / "client_files" / prefix
        if not directory.exists():
            continue
        
        # Handle nested duplicate folder names (e.g. prefix/prefix/actual-projects)
        candidates = list(directory.iterdir())
        if len(candidates) == 1 and candidates[0].is_dir() and candidates[0].name == prefix:
            directory = candidates[0]
            candidates = list(directory.iterdir())
        
        for proj_dir in sorted(candidates):
            if not proj_dir.is_dir():
                continue
            
            proj_id = proj_dir.name.split()[0] if " " in proj_dir.name else proj_dir.name
            if proj_id in seen:
                continue
            seen.add(proj_id)
            
            files_dir = proj_dir / "Project Files"
            files_count = 0
            if files_dir.exists():
                files_count = len([f for f in files_dir.iterdir() if f.is_file()])
            
            outputs_dir = base / "outputs" / proj_id
            has_output = (outputs_dir / "prediction.json").exists()
            has_eval = (outputs_dir / "evaluation_report.json").exists()
            
            results.append(ProjectInfo(
                id=proj_id,
                name=proj_dir.name,
                type=ptype,
                path=str(proj_dir),
                files_count=files_count,
                has_output=has_output,
                output_path=str(outputs_dir / "prediction.json") if has_output else None,
                has_evaluation=has_eval,
            ))
    
    return results


@router.get("/")
def list_projects() -> List[ProjectInfo]:
    """List all projects."""
    return _scan_client_projects()


@router.post("/from-folder")
def project_from_folder(req: FolderProjectRequest) -> ProjectInfo:
    """Register a project from a custom folder path."""
    folder = Path(req.folder_path)
    if not folder.exists():
        return ProjectInfo(id="", name="", type="unknown", path=str(folder), files_count=0)
    
    proj_id = folder.name.split()[0] if " " in folder.name else folder.name
    proj_id = proj_id.replace("TAKEOFF-", "").strip()
    proj_id = f"TAKEOFF-{proj_id}" if not proj_id.startswith("TAKEOFF-") else proj_id
    
    # Count files recursively
    files_count = len([f for f in folder.rglob("*") if f.is_file()])
    
    base = Path(get_config_value("paths.base_dir", "."))
    outputs_dir = base / "outputs" / proj_id
    has_output = (outputs_dir / "prediction.json").exists()
    has_eval = (outputs_dir / "evaluation_report.json").exists()
    
    return ProjectInfo(
        id=proj_id,
        name=folder.name,
        type="custom",
        path=str(folder),
        files_count=files_count,
        has_output=has_output,
        output_path=str(outputs_dir / "prediction.json") if has_output else None,
        has_evaluation=has_eval,
    )


@router.get("/{project_id}")
def get_project(project_id: str) -> ProjectInfo:
    """Get project details."""
    projects = _scan_client_projects()
    for p in projects:
        if p.id == project_id:
            return p
    return ProjectInfo(id=project_id, name=project_id, type="unknown", path="", files_count=0)


@router.get("/{project_id}/output")
def get_project_output(project_id: str) -> ProjectOutputSummary:
    """Get project output/prediction."""
    base = Path(get_config_value("paths.base_dir", "."))
    output_file = base / "outputs" / project_id / "prediction.json"
    
    if not output_file.exists():
        return ProjectOutputSummary(
            project_id=project_id,
            project_name=project_id,
            total_line_items=0,
            trades=[],
            confidence_summary={},
            line_items=[],
        )
    
    with open(output_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    line_items_data = data.get("line_items", [])
    trades = sorted(set(li.get("trade", "Unknown") for li in line_items_data))
    
    confidence_summary = {}
    for li in line_items_data:
        conf = str(li.get("confidence", "unknown"))
        confidence_summary[conf] = confidence_summary.get(conf, 0) + 1
    
    line_items = [
        LineItemSummary(
            description=li.get("description", ""),
            trade=li.get("trade", ""),
            quantity=li.get("quantity"),
            unit=li.get("unit"),
            confidence=str(li.get("confidence", "unknown")),
        )
        for li in line_items_data[:500]
    ]
    
    return ProjectOutputSummary(
        project_id=project_id,
        project_name=data.get("project_name", project_id),
        total_line_items=len(line_items_data),
        trades=trades,
        confidence_summary=confidence_summary,
        line_items=line_items,
    )


@router.get("/{project_id}/evaluation")
def get_project_evaluation(project_id: str) -> dict:
    """Get project evaluation report."""
    base = Path(get_config_value("paths.base_dir", "."))
    eval_file = base / "outputs" / project_id / "evaluation_report.json"
    
    if not eval_file.exists():
        return {"error": "No evaluation report found"}
    
    with open(eval_file, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/{project_id}/evaluate")
def evaluate_project(project_id: str) -> dict:
    """Run evaluation for a project that has expected output."""
    base = Path(get_config_value("paths.base_dir", "."))
    
    # Find project files path
    from api.routers.pipeline import _resolve_project_path
    project_path = _resolve_project_path(project_id)
    
    # Run evaluation via run.py
    import subprocess
    import sys
    
    try:
        result = subprocess.run(
            [
                sys.executable, str(base / "run.py"),
                "--project-id", project_id,
                "--input-dir", project_path,
                "--evaluate",
            ],
            capture_output=True,
            text=True,
            cwd=str(base),
            timeout=300,
        )
        
        eval_file = base / "outputs" / project_id / "evaluation_report.json"
        if eval_file.exists():
            with open(eval_file, "r", encoding="utf-8") as f:
                return json.load(f)
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as e:
        return {"error": str(e)}
