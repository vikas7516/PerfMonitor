# Gets CPU, RAM, and GPU stats using psutil and nvidia-smi

import psutil
from dataclasses import dataclass
from typing import Optional
import subprocess
import sys
import threading

# Windows-only flag for subprocess to hide the console window
if sys.platform == "win32":
    CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW
else:
    CREATE_NO_WINDOW = 0


@dataclass
class SystemStats:
    cpu_usage: float
    ram_usage: float
    gpu_usage: Optional[float]
    gpu_temp: Optional[float]
    cpu_display: str
    ram_display: str
    gpu_display: str
    gpu_temp_display: str


class SystemMonitor:
    """Tracks CPU, RAM, and GPU usage."""
    
    # Don't spam nvidia-smi too often
    GPU_CACHE_SECONDS = 2.0
    
    def __init__(self):
        self._gpu_available = self._check_nvidia()
        self._gpu_cache = (None, None)
        self._gpu_lock = threading.Lock()
        self._gpu_stop = threading.Event()
        self._gpu_thread = None
        
        # First cpu_percent call is always 0, so we throw it away
        psutil.cpu_percent(interval=None)

        if self._gpu_available:
            self._gpu_thread = threading.Thread(target=self._gpu_poll_loop, daemon=True)
            self._gpu_thread.start()
    
    def _check_nvidia(self) -> bool:
        """See if nvidia-smi is available."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3,
                creationflags=CREATE_NO_WINDOW
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False
    
    def _query_gpu_stats(self) -> tuple[Optional[float], Optional[float]]:
        """Query nvidia-smi for GPU usage and temp."""
        if not self._gpu_available:
            return None, None
        
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2,
                creationflags=CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(',')
                if len(parts) >= 2:
                    usage = float(parts[0].strip())
                    temp = float(parts[1].strip())
                    return usage, temp
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, OSError):
            pass

        return None, None

    def _gpu_poll_loop(self):
        while not self._gpu_stop.is_set():
            usage, temp = self._query_gpu_stats()
            if usage is not None:
                with self._gpu_lock:
                    self._gpu_cache = (usage, temp)
            self._gpu_stop.wait(self.GPU_CACHE_SECONDS)

    def _get_gpu_stats(self) -> tuple[Optional[float], Optional[float]]:
        """Get cached GPU stats without blocking UI."""
        if not self._gpu_available:
            return None, None

        with self._gpu_lock:
            return self._gpu_cache
    
    def get_stats(self) -> SystemStats:
        """Get all system stats in one call."""
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        gpu_usage, gpu_temp = self._get_gpu_stats()
        
        return SystemStats(
            cpu_usage=cpu,
            ram_usage=ram,
            gpu_usage=gpu_usage,
            gpu_temp=gpu_temp,
            cpu_display=f"{cpu:.0f}%",
            ram_display=f"{ram:.0f}%",
            gpu_display=f"{gpu_usage:.0f}%" if gpu_usage is not None else "N/A",
            gpu_temp_display=f"{gpu_temp:.0f}°C" if gpu_temp is not None else ""
        )

    def close(self):
        self._gpu_stop.set()
