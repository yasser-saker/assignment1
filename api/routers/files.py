"""Files router for browsing project files and running per-file extraction."""
import json
from pathlib import Path
from typing import List, Dict, Optional
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field

from ..config_manager import get_config_value
from ..jobs_manager import create_job, update_job, add_job_log, add_job_stage
from api.routers.projects import _load_registry
from api.routers.pipeline import _resolve_project_path

router = APIRouter(prefix="/files", tags=["files"])


class FileInfo(BaseModel):
    """Information about a single PDF file in a project."""
    name: str
    path: str
    relative_path: str
    size_mb: float
    total_pages: int = 0
    scanned_pages: int = 0
    text_pages: int = 0
    file_type: str = "unknown"
    has_output_v2: bool = False


class RunFilesRequest(BaseModel):
    """Request to run extraction on selected files."""
    project_id: str
    files: List[str] = Field(default_factory=list)
    output_version: str = "v2"
    evaluate: bool = False
    expected_dir: Optional[str] = None


def _scan_project_files(project_id: str) -> List[FileInfo]:
    """Scan all PDF files in a project directory."""
    project_path = _resolve_project_path(project_id)
    folder = Path(project_path)
    
    if not folder.exists():
        return []
    
    base = Path(get_config_value("paths.base_dir", "."))
    v2_output_dir = base / "outputs" / project_id / "v2"
    
    results = []
    import hashlib
    seen_hashes = set()
    
    for pdf_file in sorted(folder.rglob("*.pdf")):
        # Skip expected output folders
        parts = [p.lower() for p in pdf_file.relative_to(folder).parts]
        if "expected manual output" in parts:
            continue
        
        # Deduplicate by content hash
        try:
            h = hashlib.md5(pdf_file.read_bytes()).hexdigest()
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
        except Exception:
            pass
        
        size_mb = pdf_file.stat().st_size / (1024 * 1024)
        rel_path = str(pdf_file.relative_to(folder))
        
        # Quick page count (fast, no OCR)
        total_pages = 0
        scanned_pages = 0
        try:
            import fitz
            doc = fitz.open(str(pdf_file))
            total_pages = len(doc)
            for i in range(total_pages):
                text = doc[i].get_text().strip()
                if len(text) < 50:
                    scanned_pages += 1
            doc.close()
        except Exception:
            pass
        
        # File type classification
        name_lower = pdf_file.name.lower()
        if "spec" in name_lower:
            file_type = "spec"
        elif "draw" in name_lower or "arch" in name_lower or "plan" in name_lower or "sheet" in name_lower:
            file_type = "drawing"
        elif "sow" in name_lower or "scope" in name_lower:
            file_type = "sow"
        elif "addend" in name_lower:
            file_type = "addendum"
        else:
            file_type = "other"
        
        # Check if v2 output exists for this file
        v2_file = v2_output_dir / f"{pdf_file.stem}.json"
        has_output_v2 = v2_file.exists()
        
        results.append(FileInfo(
            name=pdf_file.name,
            path=str(pdf_file),
            relative_path=rel_path,
            size_mb=round(size_mb, 2),
            total_pages=total_pages,
            scanned_pages=scanned_pages,
            text_pages=total_pages - scanned_pages,
            file_type=file_type,
            has_output_v2=has_output_v2,
        ))
    
    return results


@router.get("/{project_id}/list")
def list_project_files(project_id: str) -> List[FileInfo]:
    """List all PDF files in a project with metadata."""
    return _scan_project_files(project_id)


@router.get("/{project_id}/info/{file_path:path}")
def get_file_info(project_id: str, file_path: str) -> FileInfo:
    """Get information about a specific file."""
    project_path = _resolve_project_path(project_id)
    full_path = Path(project_path) / file_path
    
    if not full_path.exists() or not full_path.suffix.lower() == ".pdf":
        return FileInfo(name=file_path, path=str(full_path), relative_path=file_path, size_mb=0)
    
    size_mb = full_path.stat().st_size / (1024 * 1024)
    
    total_pages = 0
    scanned_pages = 0
    try:
        import fitz
        doc = fitz.open(str(full_path))
        total_pages = len(doc)
        for i in range(total_pages):
            text = doc[i].get_text().strip()
            if len(text) < 50:
                scanned_pages += 1
        doc.close()
    except Exception:
        pass
    
    base = Path(get_config_value("paths.base_dir", "."))
    v2_file = base / "outputs" / project_id / "v2" / f"{full_path.stem}.json"
    
    return FileInfo(
        name=full_path.name,
        path=str(full_path),
        relative_path=file_path,
        size_mb=round(size_mb, 2),
        total_pages=total_pages,
        scanned_pages=scanned_pages,
        text_pages=total_pages - scanned_pages,
        has_output_v2=v2_file.exists(),
    )


def _run_files_task(request: RunFilesRequest, job_id: str) -> None:
    """Run extraction on selected files in background."""
    import subprocess
    import sys
    import threading
    import os
    
    project_id = request.project_id
    files = request.files
    output_version = request.output_version
    
    update_job(job_id, status="running", message=f"Starting file extraction for {len(files)} files...")
    add_job_stage(job_id, "initialization", "completed")
    add_job_stage(job_id, "ingestion", "running")
    
    base = Path(get_config_value("paths.base_dir", "."))
    
    # Build command
    cmd = [
        sys.executable,
        str(base / "run.py"),
        "--project-id", project_id,
        "--input-files",
    ] + files
    
    if output_version:
        cmd.extend(["--output-version", output_version])
    
    if request.evaluate and request.expected_dir:
        cmd.extend(["--evaluate", "--expected-dir", request.expected_dir])
    
    env = os.environ.copy()
    env["PROJECT_ID"] = project_id
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(base),
            env=env,
        )
        
        logs = []
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue
            logs.append(line)
            add_job_log(job_id, line)
            update_job(job_id, message=line[:200])
        
        process.wait()
        
        if process.returncode == 0:
            v2_dir = base / "outputs" / project_id / output_version
            update_job(
                job_id,
                status="completed",
                message=f"File extraction completed for {len(files)} files",
                output_path=str(v2_dir) if v2_dir.exists() else None,
            )
        else:
            error_msg = f"Process exited with code {process.returncode}"
            update_job(job_id, status="failed", message=error_msg, error=error_msg)
    except Exception as e:
        error_msg = str(e)
        update_job(job_id, status="failed", message=error_msg, error=error_msg)


@router.post("/run")
def run_files(request: RunFilesRequest, background_tasks: BackgroundTasks) -> dict:
    """Run extraction on selected files with v2 output."""
    if not request.files:
        return {"error": "No files selected"}
    
    job_id = create_job(request.project_id, f"file_run:{','.join(request.files)}")
    background_tasks.add_task(_run_files_task, request, job_id)
    
    return {
        "job_id": job_id,
        "status": "started",
        "files_count": len(request.files),
        "output_version": request.output_version,
    }


@router.get("/{project_id}/v2-outputs")
def list_v2_outputs(project_id: str) -> List[dict]:
    """List all v2 output files for a project."""
    base = Path(get_config_value("paths.base_dir", "."))
    v2_dir = base / "outputs" / project_id / "v2"
    
    if not v2_dir.exists():
        return []
    
    results = []
    for f in sorted(v2_dir.iterdir()):
        if f.suffix == ".json":
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                results.append({
                    "file": f.name,
                    "size": f.stat().st_size,
                    "line_items_count": len(data.get("line_items", [])),
                    "extracted_at": data.get("extracted_at", ""),
                })
            except Exception:
                results.append({
                    "file": f.name,
                    "size": f.stat().st_size,
                    "line_items_count": 0,
                })
    
    return results
