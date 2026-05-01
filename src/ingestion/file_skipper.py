"""Adaptive file skipping based on system resources and file characteristics.

Skips files that are too heavy to process when system resources are constrained,
or when files have characteristics that make them disproportionately expensive.
"""
import logging
import os
from pathlib import Path
from typing import Tuple, Optional, List, Dict

from src.ingestion.resource_monitor import ResourceMonitor

logger = logging.getLogger(__name__)


class FileSkipper:
    """Decides whether to skip a file based on system pressure and file traits.
    
    When system is heavily loaded, skips:
    - Large scanned PDFs (many pages needing OCR)
    - Files with very high-resolution pages
    - Duplicate files (by content hash)
    
    When system is lightly loaded, processes everything.
    """
    
    def __init__(self, monitor: Optional[ResourceMonitor] = None):
        self.monitor = monitor or ResourceMonitor()
        self._seen_hashes: set = set()
        self._skipped_files: List[Dict] = []
        self._processed_files: List[Dict] = []
    
    def check_duplicate(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Check if file is a duplicate by content hash.
        
        Returns:
            (is_duplicate, reason) tuple
        """
        try:
            import hashlib
            h = hashlib.md5(Path(file_path).read_bytes()).hexdigest()
            if h in self._seen_hashes:
                return True, f"duplicate hash {h[:8]}"
            self._seen_hashes.add(h)
            return False, None
        except Exception as e:
            logger.warning(f"Could not hash {file_path}: {e}")
            return False, None
    
    def estimate_ocr_cost(
        self,
        file_path: str,
        total_pages: int,
        scanned_pages: int,
    ) -> Dict[str, float]:
        """Estimate computational cost of processing a file.
        
        Returns dict with:
        - file_size_mb
        - total_pages
        - scanned_pages
        - estimated_pixels_millions
        - estimated_ocr_seconds
        - cost_score (0-100, higher = more expensive)
        """
        path = Path(file_path)
        file_size_mb = path.stat().st_size / (1024 * 1024)
        
        # Estimate pixels per page (conservative: A0 at 100 DPI ~ 33M pixels)
        # Most construction drawings are large format
        avg_pixels_per_page = 8_000_000  # ~8M pixels average for drawings
        estimated_pixels = scanned_pages * avg_pixels_per_page
        
        # OCR time estimate: ~2-5 seconds per page on modern CPU
        # But on overloaded systems, can be 30+ seconds
        load_ratio = self.monitor.get_load_ratio()
        base_time_per_page = 3.0  # seconds
        slowdown_factor = max(1.0, load_ratio)
        estimated_ocr_seconds = scanned_pages * base_time_per_page * slowdown_factor
        
        # Cost score: 0-100
        # Factors: file size (0-20), scanned pages (0-40), estimated time (0-40)
        size_score = min(20, file_size_mb / 5 * 20)
        scan_score = min(40, scanned_pages / 20 * 40)
        time_score = min(40, estimated_ocr_seconds / 120 * 40)
        cost_score = size_score + scan_score + time_score
        
        return {
            "file_size_mb": round(file_size_mb, 2),
            "total_pages": total_pages,
            "scanned_pages": scanned_pages,
            "estimated_pixels_millions": round(estimated_pixels / 1_000_000, 1),
            "estimated_ocr_seconds": round(estimated_ocr_seconds, 1),
            "cost_score": round(cost_score, 1),
        }
    
    def should_skip(
        self,
        file_path: str,
        total_pages: int = 0,
        scanned_pages: int = 0,
    ) -> Tuple[bool, Optional[str]]:
        """Decide whether to skip a file.
        
        Returns:
            (should_skip, reason) tuple. reason is None if not skipping.
        """
        path = Path(file_path)
        file_name = path.name
        
        # 1. Duplicate check
        is_dup, dup_reason = self.check_duplicate(file_path)
        if is_dup:
            self._skipped_files.append({
                "file": file_name,
                "reason": dup_reason,
                "pressure": self.monitor.get_pressure_level(),
            })
            return True, f"duplicate: {dup_reason}"
        
        # 2. Estimate cost
        cost = self.estimate_ocr_cost(file_path, total_pages, scanned_pages)
        
        # 3. Resource-aware skipping rules
        pressure = self.monitor.get_pressure_level()
        load_ratio = self.monitor.get_load_ratio()
        mem_mb = self.monitor.get_available_memory_mb()
        
        # Rule: Critical pressure → skip anything with scanned pages needing OCR
        # When system is at critical load, even simple OCR hangs due to process starvation
        if pressure == "critical" and scanned_pages > 0:
            reason = (
                f"critical system pressure (load={load_ratio:.1f}x, "
                f"mem={mem_mb:.0f}MB), {scanned_pages} scanned pages — "
                f"OCR would hang on overloaded system"
            )
            self._skipped_files.append({
                "file": file_name,
                "reason": reason,
                "pressure": pressure,
                "cost": cost,
            })
            return True, reason
        
        # Rule: High pressure → skip high-cost files (cost > 50)
        if pressure == "high" and cost["cost_score"] > 50:
            reason = (
                f"high system pressure (load={load_ratio:.1f}x, "
                f"mem={mem_mb:.0f}MB), file cost={cost['cost_score']:.0f}"
            )
            self._skipped_files.append({
                "file": file_name,
                "reason": reason,
                "pressure": pressure,
                "cost": cost,
            })
            return True, reason
        
        # Rule: High pressure → skip high-cost files (cost > 50)
        if pressure == "high" and cost["cost_score"] > 50:
            reason = (
                f"high system pressure (load={load_ratio:.1f}x, "
                f"mem={mem_mb:.0f}MB), file cost={cost['cost_score']:.0f}"
            )
            self._skipped_files.append({
                "file": file_name,
                "reason": reason,
                "pressure": pressure,
                "cost": cost,
            })
            return True, reason
        
        # Rule: Moderate pressure → skip very high-cost files (cost > 70)
        if pressure == "moderate" and cost["cost_score"] > 70:
            reason = (
                f"moderate system pressure (load={load_ratio:.1f}x), "
                f"file cost={cost['cost_score']:.0f}"
            )
            self._skipped_files.append({
                "file": file_name,
                "reason": reason,
                "pressure": pressure,
                "cost": cost,
            })
            return True, reason
        
        # Rule: Always skip extremely heavy files regardless of pressure
        # (would take > 5 minutes even on idle system)
        if cost["estimated_ocr_seconds"] > 300:
            reason = (
                f"file too heavy: {cost['estimated_ocr_seconds']:.0f}s "
                f"estimated OCR time ({scanned_pages} scanned pages)"
            )
            self._skipped_files.append({
                "file": file_name,
                "reason": reason,
                "pressure": pressure,
                "cost": cost,
            })
            return True, reason
        
        # Rule: Always skip very large scanned PDFs (> 5MB, > 20 scanned pages)
        if cost["file_size_mb"] > 5 and scanned_pages > 20:
            reason = (
                f"very large scanned PDF: {cost['file_size_mb']:.1f}MB, "
                f"{scanned_pages} scanned pages"
            )
            self._skipped_files.append({
                "file": file_name,
                "reason": reason,
                "pressure": pressure,
                "cost": cost,
            })
            return True, reason
        
        # Not skipping
        self._processed_files.append({
            "file": file_name,
            "pressure": pressure,
            "cost": cost,
        })
        return False, None
    
    def get_summary(self) -> Dict:
        """Return summary of skipped and processed files."""
        return {
            "system_pressure": self.monitor.get_pressure_level(),
            "system_status": str(self.monitor),
            "skipped_count": len(self._skipped_files),
            "processed_count": len(self._processed_files),
            "skipped_files": self._skipped_files,
            "processed_files": self._processed_files,
        }
    
    def log_summary(self):
        """Log summary to logger."""
        summary = self.get_summary()
        logger.info(
            f"FileSkipper Summary: {summary['skipped_count']} skipped, "
            f"{summary['processed_count']} processed, "
            f"pressure={summary['system_pressure']}"
        )
        for sf in summary["skipped_files"]:
            logger.info(f"  SKIPPED: {sf['file']} — {sf['reason']}")
