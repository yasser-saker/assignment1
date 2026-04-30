"""Job history manager for tracking pipeline runs."""
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

JOBS_FILE = Path(__file__).parent / "jobs_history.json"


def _load_jobs() -> List[Dict[str, Any]]:
    if JOBS_FILE.exists():
        try:
            with open(JOBS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_jobs(jobs: List[Dict[str, Any]]) -> None:
    JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2, ensure_ascii=False)


def create_job(project_id: str, project_path: str) -> str:
    jobs = _load_jobs()
    job_id = str(uuid.uuid4())[:8]
    job = {
        "id": job_id,
        "project_id": project_id,
        "project_path": project_path,
        "status": "pending",
        "stages": [],
        "current_stage": None,
        "progress": 0.0,
        "message": "Waiting to start...",
        "logs": [],
        "output_path": None,
        "evaluation_path": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "completed_at": None,
        "error": None,
    }
    jobs.insert(0, job)  # Newest first
    _save_jobs(jobs[:100])  # Keep last 100
    return job_id


def update_job(job_id: str, **kwargs) -> None:
    jobs = _load_jobs()
    for job in jobs:
        if job["id"] == job_id:
            job.update(kwargs)
            job["updated_at"] = datetime.now().isoformat()
            break
    _save_jobs(jobs)


def add_job_log(job_id: str, message: str) -> None:
    jobs = _load_jobs()
    for job in jobs:
        if job["id"] == job_id:
            job["logs"].append({"time": datetime.now().isoformat(), "message": message})
            if len(job["logs"]) > 500:
                job["logs"] = job["logs"][-500:]
            break
    _save_jobs(jobs)


def add_job_stage(job_id: str, stage_name: str, status: str = "running") -> None:
    jobs = _load_jobs()
    for job in jobs:
        if job["id"] == job_id:
            # Update existing stage or add new
            existing = [s for s in job["stages"] if s["name"] == stage_name]
            if existing:
                existing[0]["status"] = status
                if status == "completed":
                    existing[0]["completed_at"] = datetime.now().isoformat()
            else:
                job["stages"].append({
                    "name": stage_name,
                    "status": status,
                    "started_at": datetime.now().isoformat(),
                    "completed_at": None,
                })
            job["current_stage"] = stage_name
            break
    _save_jobs(jobs)


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    jobs = _load_jobs()
    for job in jobs:
        if job["id"] == job_id:
            return job
    return None


def list_jobs(limit: int = 50) -> List[Dict[str, Any]]:
    jobs = _load_jobs()
    return jobs[:limit]


def delete_job(job_id: str) -> bool:
    jobs = _load_jobs()
    new_jobs = [j for j in jobs if j["id"] != job_id]
    if len(new_jobs) != len(jobs):
        _save_jobs(new_jobs)
        return True
    return False
