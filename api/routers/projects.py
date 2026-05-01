"""Projects router for fully dynamic project management.

Users add projects manually by folder path. No hardcoded client_files scanning.
"""
import json
from pathlib import Path
from typing import List, Set, Optional
from fastapi import APIRouter

from ..models import ProjectInfo, ProjectOutputSummary, LineItemSummary, FolderProjectRequest, EvaluateRequest
from ..config_manager import get_config_value

router = APIRouter(prefix="/projects", tags=["projects"])

HIDDEN_PROJECTS_FILE = Path(__file__).parent.parent / "hidden_projects.json"
PROJECTS_REGISTRY_FILE = Path(__file__).parent.parent / "registered_projects.json"


def _load_hidden() -> Set[str]:
    if HIDDEN_PROJECTS_FILE.exists():
        try:
            with open(HIDDEN_PROJECTS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()


def _save_hidden(hidden: Set[str]) -> None:
    HIDDEN_PROJECTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HIDDEN_PROJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(hidden)), f, indent=2, ensure_ascii=False)


def _load_registry() -> dict:
    """Load registered projects: {project_id: {name, path, type, added_at}}"""
    if PROJECTS_REGISTRY_FILE.exists():
        try:
            with open(PROJECTS_REGISTRY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_registry(registry: dict) -> None:
    PROJECTS_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROJECTS_REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)


def _get_project_info(project_id: str, meta: dict) -> Optional[ProjectInfo]:
    """Build ProjectInfo from registry metadata."""
    folder = Path(meta["path"])
    if not folder.exists():
        return None
    
    pdf_count = 0
    for f in folder.rglob("*"):
        if f.is_file() and f.suffix.lower() == ".pdf":
            # Skip files inside Expected Manual Output folders
            parts = [p.lower() for p in f.relative_to(folder).parts]
            if "expected manual output" in parts:
                continue
            pdf_count += 1
    
    base = Path(get_config_value("paths.base_dir", "."))
    outputs_dir = base / "outputs" / project_id
    has_output = (outputs_dir / "prediction.json").exists()
    has_eval = (outputs_dir / "evaluation_report.json").exists()
    
    return ProjectInfo(
        id=project_id,
        name=meta.get("name", project_id),
        type=meta.get("type", "custom"),
        path=str(folder),
        files_count=pdf_count,
        has_output=has_output,
        output_path=str(outputs_dir / "prediction.json") if has_output else None,
        has_evaluation=has_eval,
    )


def _scan_registered_projects() -> List[ProjectInfo]:
    """Return projects from user registry (excluding hidden)."""
    registry = _load_registry()
    hidden = _load_hidden()
    results = []
    
    for proj_id, meta in sorted(registry.items()):
        if proj_id in hidden:
            continue
        info = _get_project_info(proj_id, meta)
        if info:
            results.append(info)
    
    return results


# =============================================================================
# FIXED-ORDER ROUTES (no path parameters) — MUST come before /{project_id}
# =============================================================================

@router.get("/")
def list_projects() -> List[ProjectInfo]:
    """List all registered projects (user-added only)."""
    return _scan_registered_projects()


@router.get("/hidden")
def list_hidden_projects() -> List[str]:
    """List hidden project IDs."""
    return sorted(list(_load_hidden()))


def _derive_project_id_and_name(folder: Path) -> tuple:
    """Derive a clear project ID and name from a folder path.
    
    Handles common cases like 'Project Files' subfolders by looking up the tree.
    """
    original = folder
    name = folder.name
    
    # If folder is a generic subfolder like 'Project Files', use parent
    generic_names = {"project files", "project_files", "files", "docs", "documents", "pdf", "pdfs"}
    if name.lower() in generic_names and folder.parent != folder:
        folder = folder.parent
        name = folder.name
    
    # ID: take first segment (e.g., 'TAKEOFF-28' from 'TAKEOFF-28 - Name')
    proj_id = name.split()[0] if " " in name else name
    proj_id = proj_id.strip().replace(" ", "_")
    
    # If ID is still generic, search upward in path for a TAKEOFF-XX or meaningful name
    generic_ids = {"project", "project_files", "files", "docs", "documents", "pdf", "pdfs", ""}
    if proj_id.lower() in generic_ids:
        for part in reversed(original.parts):
            part_stripped = part.strip()
            if not part_stripped:
                continue
            # Look for TAKEOFF-XX pattern
            if "TAKEOFF-" in part_stripped.upper() or "takeoff-" in part_stripped.lower():
                name = part_stripped
                proj_id = part_stripped.split()[0] if " " in part_stripped else part_stripped
                proj_id = proj_id.strip().replace(" ", "_")
                break
            # Or any part with a dash/number that looks like a project code
            if "-" in part_stripped and len(part_stripped) > 5:
                name = part_stripped
                proj_id = part_stripped.split()[0] if " " in part_stripped else part_stripped
                proj_id = proj_id.strip().replace(" ", "_")
                break
    
    if not proj_id or proj_id.lower() in generic_ids:
        proj_id = "project_1"
    
    return proj_id, name


@router.post("/from-folder")
def project_from_folder(req: FolderProjectRequest) -> ProjectInfo:
    """Register a project from a custom folder path."""
    folder = Path(req.folder_path)
    if not folder.exists():
        return ProjectInfo(id="", name="", type="unknown", path=str(folder), files_count=0)
    
    proj_id, proj_name = _derive_project_id_and_name(folder)
    
    pdf_count = 0
    for f in folder.rglob("*"):
        if f.is_file() and f.suffix.lower() == ".pdf":
            parts = [p.lower() for p in f.relative_to(folder).parts]
            if "expected manual output" in parts:
                continue
            pdf_count += 1
    
    base = Path(get_config_value("paths.base_dir", "."))
    outputs_dir = base / "outputs" / proj_id
    has_output = (outputs_dir / "prediction.json").exists()
    has_eval = (outputs_dir / "evaluation_report.json").exists()
    
    # Save to registry
    registry = _load_registry()
    registry[proj_id] = {
        "name": proj_name,
        "path": str(folder),
        "type": "custom",
        "added_at": __import__('datetime').datetime.now().isoformat(),
    }
    _save_registry(registry)
    
    return ProjectInfo(
        id=proj_id,
        name=proj_name,
        type="custom",
        path=str(folder),
        files_count=pdf_count,
        has_output=has_output,
        output_path=str(outputs_dir / "prediction.json") if has_output else None,
        has_evaluation=has_eval,
    )


@router.get("/discover")
def discover_projects(search: str = "") -> List[dict]:
    """Discover available project folders under common paths.
    
    Scans /app/client_files recursively and returns folders that contain PDFs
    and are not already registered.
    """
    registry = _load_registry()
    registered_paths = {meta["path"] for meta in registry.values()}
    hidden = _load_hidden()
    
    discover_paths = [
        Path("/app/client_files"),
        Path("/app/data"),
        Path("/data"),
    ]
    
    found = []
    seen = set()
    
    skip_names = {"expected manual output", "project files", "__pycache__", ".git", "node_modules", "venv", ".venv"}
    
    for base_path in discover_paths:
        if not base_path.exists():
            continue
        for item in base_path.rglob("*"):
            if not item.is_dir():
                continue
            # Skip very deep paths (more than 4 levels from base)
            depth = len(item.relative_to(base_path).parts)
            if depth > 4:
                continue
            # Skip too shallow (top-level category folders and wrapper folders)
            if depth < 3:
                continue
            # Skip known non-project folders
            if item.name.lower() in skip_names:
                continue
            # Skip if already registered
            path_str = str(item)
            if path_str in registered_paths:
                continue
            # Skip if hidden
            proj_id = item.name.split()[0] if " " in item.name else item.name
            proj_id = proj_id.strip().replace(" ", "_")
            if proj_id in hidden:
                continue
            # Skip if no PDFs anywhere in this folder tree
            has_pdf = any(f.suffix.lower() == ".pdf" for f in item.rglob("*") if f.is_file())
            if not has_pdf:
                continue
            # Deduplicate by path
            if path_str in seen:
                continue
            seen.add(path_str)
            
            pdf_count = 0
            for f in item.rglob("*"):
                if f.is_file() and f.suffix.lower() == ".pdf":
                    parts = [p.lower() for p in f.relative_to(item).parts]
                    if "expected manual output" in parts:
                        continue
                    pdf_count += 1
            
            found.append({
                "id": proj_id,
                "name": item.name,
                "path": path_str,
                "files_count": pdf_count,
                "depth": depth,
            })
    
    # Sort by path depth (shallower first) then by name
    found.sort(key=lambda x: (x["depth"], x["name"]))
    
    # Filter by search if provided
    if search:
        search_lower = search.lower()
        found = [f for f in found if search_lower in f["name"].lower() or search_lower in f["id"].lower()]
    
    return found


@router.post("/clear-outputs")
def clear_all_outputs() -> dict:
    """Delete all output files and folders."""
    base = Path(get_config_value("paths.base_dir", "."))
    outputs_dir = base / "outputs"
    deleted = []
    errors = []
    
    if outputs_dir.exists():
        for item in outputs_dir.iterdir():
            try:
                if item.is_dir():
                    import shutil
                    shutil.rmtree(item)
                    deleted.append(str(item.name))
                elif item.is_file():
                    item.unlink()
                    deleted.append(str(item.name))
            except Exception as e:
                errors.append(f"{item.name}: {str(e)}")
    
    return {
        "success": len(errors) == 0,
        "deleted": deleted,
        "count": len(deleted),
        "errors": errors,
    }


# =============================================================================
# DYNAMIC ROUTES (with {project_id}) — MUST come after fixed routes
# =============================================================================

@router.get("/{project_id}")
def get_project(project_id: str) -> ProjectInfo:
    """Get project details."""
    registry = _load_registry()
    if project_id in registry:
        info = _get_project_info(project_id, registry[project_id])
        if info:
            return info
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


@router.post("/{project_id}/delete")
def delete_project(project_id: str) -> dict:
    """Hide a project, delete its outputs and job history."""
    import shutil
    base = Path(get_config_value("paths.base_dir", "."))
    
    hidden = _load_hidden()
    hidden.add(project_id)
    _save_hidden(hidden)
    
    deleted_paths = []
    errors = []
    
    outputs_dir = base / "outputs" / project_id
    if outputs_dir.exists():
        try:
            shutil.rmtree(outputs_dir)
            deleted_paths.append(str(outputs_dir))
        except Exception as e:
            errors.append(f"outputs: {str(e)}")
    
    from ..jobs_manager import _load_jobs, _save_jobs
    jobs = _load_jobs()
    new_jobs = [j for j in jobs if j.get("project_id") != project_id]
    if len(new_jobs) != len(jobs):
        _save_jobs(new_jobs)
    
    return {
        "success": len(errors) == 0,
        "hidden": True,
        "deleted": deleted_paths,
        "errors": errors,
    }


@router.post("/{project_id}/restore")
def restore_project(project_id: str) -> dict:
    """Restore a hidden project to the list."""
    hidden = _load_hidden()
    if project_id in hidden:
        hidden.remove(project_id)
        _save_hidden(hidden)
        return {"success": True, "message": f"Project {project_id} restored"}
    return {"success": False, "message": "Project not found in hidden list"}


@router.post("/{project_id}/evaluate")
def evaluate_project(project_id: str, req: EvaluateRequest = None) -> dict:
    """Run evaluation for a project. Optionally specify expected output path."""
    base = Path(get_config_value("paths.base_dir", "."))
    
    from api.routers.pipeline import _resolve_project_path
    project_path = _resolve_project_path(project_id)
    
    import subprocess
    import sys
    
    cmd = [
        sys.executable, str(base / "run.py"),
        "--project-id", project_id,
        "--input-dir", project_path,
        "--evaluate",
    ]
    
    if req and req.expected_output_path:
        cmd.extend(["--expected-dir", req.expected_output_path])
    
    try:
        result = subprocess.run(
            cmd,
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
