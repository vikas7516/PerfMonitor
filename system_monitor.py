# Gets CPU, RAM, and GPU stats using psutil and nvidia-smi

import psutil
from dataclasses import dataclass
from typing import Optional
import subprocess
import sys
import threading

try:
    import pynvml
except Exception:  # Optional dependency; fallback is nvidia-smi.
    pynvml = None

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
        self._gpu_mode = self._detect_gpu_mode()
        self._gpu_available = self._gpu_mode is not None
        self._gpu_cache = (None, None)
        self._gpu_lock = threading.Lock()
        self._gpu_stop = threading.Event()
        self._gpu_thread = None
        self._nvml_handle = None
        
        # First cpu_percent call is always 0, so we throw it away
        psutil.cpu_percent(interval=None)

        if self._gpu_mode == "nvml":
            self._init_nvml()

        if self._gpu_available:
            self._gpu_thread = threading.Thread(target=self._gpu_poll_loop, daemon=True)
            self._gpu_thread.start()

    def _detect_gpu_mode(self) -> Optional[str]:
        if pynvml is not None:
            return "nvml"
        if self._check_nvidia_smi():
            return "nvidia-smi"
        return None

    def _init_nvml(self):
        if pynvml is None:
            self._gpu_mode = "nvidia-smi" if self._check_nvidia_smi() else None
            self._gpu_available = self._gpu_mode is not None
            return

        try:
            pynvml.nvmlInit()
            self._nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        except Exception:
            self._nvml_handle = None
            self._gpu_mode = "nvidia-smi" if self._check_nvidia_smi() else None
            self._gpu_available = self._gpu_mode is not None

    def _check_nvidia_smi(self) -> bool:
        """See if nvidia-smi is available."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=3,
                creationflags=CREATE_NO_WINDOW,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False

    def _query_gpu_stats_nvml(self) -> tuple[Optional[float], Optional[float]]:
        if pynvml is None or self._nvml_handle is None:
            return None, None

        try:
            util = pynvml.nvmlDeviceGetUtilizationRates(self._nvml_handle)
            temp = pynvml.nvmlDeviceGetTemperature(
                self._nvml_handle, pynvml.NVML_TEMPERATURE_GPU
            )
            return float(util.gpu), float(temp)
        except Exception:
            return None, None
    
    def _query_gpu_stats_smi(self) -> tuple[Optional[float], Optional[float]]:
        """Query nvidia-smi for GPU usage and temp."""
        if self._gpu_mode != "nvidia-smi":
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

    def _query_gpu_stats(self) -> tuple[Optional[float], Optional[float]]:
        if not self._gpu_available:
            return None, None

        if self._gpu_mode == "nvml":
            return self._query_gpu_stats_nvml()

        return self._query_gpu_stats_smi()

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
        if self._gpu_thread and self._gpu_thread.is_alive():
            self._gpu_thread.join(timeout=2.5)
        if self._gpu_mode == "nvml" and pynvml is not None:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
