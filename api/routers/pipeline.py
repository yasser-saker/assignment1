"""Pipeline router for running extraction and evaluation."""
import json
import subprocess
import sys
import threading
import os
from pathlib import Path
from typing import Dict, List
from fastapi import APIRouter, BackgroundTasks

from ..models import PipelineRequest, PipelineStatus
from ..config_manager import get_config_value
from ..jobs_manager import (
    create_job,
    update_job,
    add_job_log,
    add_job_stage,
    get_job,
    list_jobs,
    delete_job,
)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

# In-memory running state (for real-time polling)
_running_state: Dict[str, dict] = {}
_state_lock = threading.Lock()


def _detect_project_type(project_path: str) -> str:
    """Detect if project has expected output folder."""
    p = Path(project_path)
    # Check if parent has Expected Manual Output subfolder
    for parent in [p, p.parent]:
        expected_dir = parent / "Expected Manual Output"
        if expected_dir.exists():
            return "sample"
    return "challenge"


def _resolve_project_path(project_id: str, provided_path: str = None) -> str:
    """Resolve the actual project files directory."""
    if provided_path:
        return provided_path
    
    base = Path(get_config_value("paths.base_dir", "."))
    
    # Search in client_files for the project folder
    prefixes = [
        "01_Sample_Projects_With_Expected_Output",
        "02_Challenge_Projects_Project_Files_Only",
    ]
    
    for prefix in prefixes:
        dir1 = base / "client_files" / prefix
        if not dir1.exists():
            continue
        # Handle nested duplicate folder names
        candidates = list(dir1.iterdir())
        if len(candidates) == 1 and candidates[0].is_dir() and candidates[0].name == prefix:
            search_dir = candidates[0]
        else:
            search_dir = dir1
        
        for proj_dir in search_dir.iterdir():
            if not proj_dir.is_dir():
                continue
            if proj_dir.name.startswith(project_id):
                files_dir = proj_dir / "Project Files"
                if files_dir.exists():
                    return str(files_dir)
    
    return str(base / "client_files" / project_id / "Project Files")


def _run_pipeline_task(request: PipelineRequest, job_id: str) -> None:
    """Run pipeline in background with detailed progress."""
    project_id = request.project_id
    project_path = _resolve_project_path(project_id, request.project_path)
    base = Path(get_config_value("paths.base_dir", "."))
    
    update_job(job_id, status="running", message=f"Starting pipeline for {project_id}...")
    add_job_stage(job_id, "initialization", "completed")
    add_job_stage(job_id, "ingestion", "running")
    
    # Determine if we should run evaluation
    project_type = _detect_project_type(project_path)
    has_expected = project_type == "sample"
    
    # Check LLM setting from config
    use_llm = get_config_value("llm.use_llm_in_pipeline", False)
    
    # Build command with correct named arguments
    cmd = [
        sys.executable,
        str(base / "run.py"),
        "--project-id", project_id,
        "--input-dir", project_path,
    ]
    
    if has_expected:
        cmd.append("--evaluate")
    
    if use_llm:
        cmd.append("--use-llm")
    
    env = os.environ.copy()
    env["PROJECT_PATH"] = project_path
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(base),
            env=env,
        )
        
        logs: List[str] = []
        current_stage = "ingestion"
        stage_progress = {
            "initialization": 0.05,
            "ingestion": 0.30,
            "extraction": 0.60,
            "output": 0.85,
            "evaluation": 0.95,
            "finalization": 1.0,
        }
        
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue
            
            logs.append(line)
            add_job_log(job_id, line)
            
            lower = line.lower()
            
            # Detect stage changes from output
            if any(kw in lower for kw in ["ingesting", "extracting text", "pdf extraction", "classifying", "processing"]):
                if current_stage != "ingestion":
                    add_job_stage(job_id, current_stage, "completed")
                    current_stage = "ingestion"
                    add_job_stage(job_id, "ingestion", "running")
            elif any(kw in lower for kw in ["extracting", "llm", "prompt", "chunk", "consolidating", "rule-based"]):
                if current_stage != "extraction":
                    add_job_stage(job_id, current_stage, "completed")
                    current_stage = "extraction"
                    add_job_stage(job_id, "extraction", "running")
            elif any(kw in lower for kw in ["generating output", "serializing", "writing json", "output", "saved to"]):
                if current_stage != "output":
                    add_job_stage(job_id, current_stage, "completed")
                    current_stage = "output"
                    add_job_stage(job_id, "output", "running")
            elif any(kw in lower for kw in ["evaluating", "comparing", "fuzzy match", "scoring"]):
                if current_stage != "evaluation":
                    add_job_stage(job_id, current_stage, "completed")
                    current_stage = "evaluation"
                    add_job_stage(job_id, "evaluation", "running")
            
            # Calculate progress
            progress = stage_progress.get(current_stage, 0.5)
            update_job(
                job_id,
                current_stage=current_stage,
                progress=progress,
                message=line[:200],
            )
            
            with _state_lock:
                _running_state[job_id] = {
                    "status": "running",
                    "current_stage": current_stage,
                    "progress": progress,
                    "message": line[:200],
                    "logs": logs[-100:],
                }
        
        process.wait()
        
        # Mark current stage complete
        add_job_stage(job_id, current_stage, "completed")
        
        if process.returncode == 0:
            output_path = str(base / "outputs" / project_id / "prediction.json")
            eval_path = str(base / "outputs" / project_id / "evaluation_report.json")
            has_eval = Path(eval_path).exists()
            
            update_job(
                job_id,
                status="completed",
                current_stage="finalization",
                progress=1.0,
                message=f"Pipeline completed for {project_id}",
                output_path=output_path if Path(output_path).exists() else None,
                evaluation_path=eval_path if has_eval else None,
                completed_at=__import__('datetime').datetime.now().isoformat(),
            )
            
            with _state_lock:
                _running_state[job_id] = {
                    "status": "completed",
                    "current_stage": "finalization",
                    "progress": 1.0,
                    "message": f"Pipeline completed for {project_id}",
                    "output_path": output_path if Path(output_path).exists() else None,
                    "evaluation_path": eval_path if has_eval else None,
                }
        else:
            # Collect last few lines as error
            error_lines = [l for l in logs if "error" in l.lower() or "traceback" in l.lower() or "exception" in l.lower()]
            error_msg = f"Pipeline failed with code {process.returncode}"
            if error_lines:
                error_msg += f" | Last error: {error_lines[-1][:200]}"
            update_job(job_id, status="failed", message=error_msg, error=error_msg)
            with _state_lock:
                _running_state[job_id] = {"status": "failed", "message": error_msg}
    except Exception as e:
        error_msg = str(e)
        update_job(job_id, status="failed", message=error_msg, error=error_msg)
        with _state_lock:
            _running_state[job_id] = {"status": "failed", "message": error_msg}


@router.post("/run")
def run_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks) -> dict:
    """Start pipeline for a project."""
    project_path = _resolve_project_path(request.project_id, request.project_path)
    job_id = create_job(request.project_id, project_path)
    
    background_tasks.add_task(_run_pipeline_task, request, job_id)
    return {"job_id": job_id, "status": "started"}


@router.get("/status/{job_id}")
def get_pipeline_status(job_id: str) -> dict:
    """Get pipeline status by job ID."""
    job = get_job(job_id)
    if job:
        return job
    return {"error": "Job not found"}


@router.get("/jobs")
def get_jobs(limit: int = 50) -> List[dict]:
    """List recent jobs."""
    return list_jobs(limit)


@router.delete("/jobs/{job_id}")
def remove_job(job_id: str) -> dict:
    """Delete a job from history."""
    success = delete_job(job_id)
    return {"success": success}


@router.post("/run-script")
def run_script(request: dict) -> dict:
    """Run an arbitrary Python script with arguments."""
    base = Path(get_config_value("paths.base_dir", "."))
    script_name = request.get("script", "run.py")
    args = request.get("args", [])
    
    cmd = [sys.executable, str(base / script_name)] + args
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(base),
            timeout=600,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Script timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}
