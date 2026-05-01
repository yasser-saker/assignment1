"""System resource monitoring for adaptive file processing.

Monitors CPU load, memory availability, and system pressure
to decide whether to process heavy files or skip them.
"""
import logging
import os
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """Monitor system resources without external dependencies.
    
    Uses /proc filesystem on Linux. Falls back to conservative
    estimates on other platforms.
    """
    
    def __init__(self):
        self._cpu_count = self._detect_cpu_count()
        self._is_linux = os.path.exists("/proc/loadavg")
    
    @staticmethod
    def _detect_cpu_count() -> int:
        """Get number of logical CPUs."""
        try:
            return os.cpu_count() or 4
        except Exception:
            return 4
    
    def get_cpu_count(self) -> int:
        """Return number of logical CPUs."""
        return self._cpu_count
    
    def get_load_avg(self) -> Tuple[float, float, float]:
        """Return 1-min, 5-min, 15-min load averages.
        
        Returns (999.0, 999.0, 999.0) if unavailable (conservative).
        """
        if not self._is_linux:
            return (999.0, 999.0, 999.0)
        try:
            with open("/proc/loadavg", "r") as f:
                parts = f.read().strip().split()
                return (float(parts[0]), float(parts[1]), float(parts[2]))
        except Exception as e:
            logger.warning(f"Could not read loadavg: {e}")
            return (999.0, 999.0, 999.0)
    
    def get_available_memory_mb(self) -> float:
        """Return available memory in MB.
        
        Returns 0.0 if unavailable (conservative).
        """
        if not self._is_linux:
            return 0.0
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        kb = int(line.split()[1])
                        return kb / 1024.0
            # Fallback: MemFree
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemFree:"):
                        kb = int(line.split()[1])
                        return kb / 1024.0
        except Exception as e:
            logger.warning(f"Could not read meminfo: {e}")
        return 0.0
    
    def get_load_ratio(self) -> float:
        """Return load_avg_1min / cpu_count.
        
        > 1.0 means overloaded, > 2.0 means heavily overloaded.
        """
        load_1min, _, _ = self.get_load_avg()
        return load_1min / max(self._cpu_count, 1)
    
    def is_heavily_loaded(self, threshold: float = 2.0) -> bool:
        """Check if system load exceeds threshold * cpu_count.
        
        Args:
            threshold: load ratio threshold (default 2.0 = 2x overload)
        """
        return self.get_load_ratio() > threshold
    
    def is_moderately_loaded(self, threshold: float = 1.5) -> bool:
        """Check if system load exceeds threshold * cpu_count."""
        return self.get_load_ratio() > threshold
    
    def is_memory_low(self, threshold_mb: float = 2048.0) -> bool:
        """Check if available memory is below threshold."""
        return self.get_available_memory_mb() < threshold_mb
    
    def get_pressure_level(self) -> str:
        """Return system pressure as a human-readable level.
        
        Returns one of: 'critical', 'high', 'moderate', 'low'
        """
        load_ratio = self.get_load_ratio()
        mem_mb = self.get_available_memory_mb()
        
        if load_ratio > 3.0 or mem_mb < 512:
            return "critical"
        if load_ratio > 2.0 or mem_mb < 1024:
            return "high"
        if load_ratio > 1.5 or mem_mb < 2048:
            return "moderate"
        return "low"
    
    def __str__(self) -> str:
        load_1, load_5, load_15 = self.get_load_avg()
        mem = self.get_available_memory_mb()
        pressure = self.get_pressure_level()
        return (
            f"System: {self._cpu_count} CPUs, "
            f"load={load_1:.1f}/{load_5:.1f}/{load_15:.1f}, "
            f"mem_available={mem:.0f}MB, "
            f"pressure={pressure}"
        )
