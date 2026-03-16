# Tracks network usage and calculates upload/download speeds

import psutil
import time
from dataclasses import dataclass


@dataclass
class SpeedData:
    download_speed: float
    upload_speed: float
    download_unit: str
    upload_unit: str
    download_display: str
    upload_display: str


class SpeedMonitor:
    """Measures network speed by comparing bytes over time."""
    
    def __init__(self):
        self._last_bytes_sent = 0
        self._last_bytes_recv = 0
        self._last_time = time.time()
        self._initialized = False
    
    def _format_speed(self, bytes_per_sec: float) -> tuple[str, str]:
        """Pick the right unit - B/s, KB/s, or MB/s."""
        if bytes_per_sec <= 0:
            return "0.0", "KB/s"
        if bytes_per_sec < 1024:
            return f"{bytes_per_sec:.0f}", "B/s"
        elif bytes_per_sec < 1024 * 1024:
            return f"{bytes_per_sec / 1024:.1f}", "KB/s"
        else:
            return f"{bytes_per_sec / (1024 * 1024):.2f}", "MB/s"
    
    def get_speed(self) -> SpeedData:
        """Get current upload and download speeds."""
        now = time.time()
        counters = psutil.net_io_counters()
        
        # First run - just save the baseline
        if not self._initialized:
            self._last_bytes_sent = counters.bytes_sent
            self._last_bytes_recv = counters.bytes_recv
            self._last_time = now
            self._initialized = True
            return SpeedData(0, 0, "KB/s", "KB/s", "0.0", "0.0")
        
        # Calculate speed from the difference
        elapsed = max(now - self._last_time, 0.1)
        
        recv_delta = counters.bytes_recv - self._last_bytes_recv
        sent_delta = counters.bytes_sent - self._last_bytes_sent

        # Interface resets/rollovers can produce negative deltas; clamp to 0.
        download = max(recv_delta / elapsed, 0.0)
        upload = max(sent_delta / elapsed, 0.0)
        
        self._last_bytes_sent = counters.bytes_sent
        self._last_bytes_recv = counters.bytes_recv
        self._last_time = now
        
        dl_display, dl_unit = self._format_speed(download)
        ul_display, ul_unit = self._format_speed(upload)
        
        return SpeedData(
            download_speed=download,
            upload_speed=upload,
            download_unit=dl_unit,
            upload_unit=ul_unit,
            download_display=dl_display,
            upload_display=ul_display
        )
