# Tracks network usage and calculates upload/download speeds

import psutil
import time
from dataclasses import dataclass
from typing import Dict, Tuple


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
        self._last_pernic: Dict[str, Tuple[int, int]] = {}
        self._last_time = time.time()
        self._initialized = False

    @staticmethod
    def _is_relevant_iface(name: str) -> bool:
        n = name.lower()
        ignored_prefixes = (
            "lo",
            "loopback",
            "docker",
            "br-",
            "veth",
            "virbr",
            "vmnet",
            "vboxnet",
            "zt",
            "tailscale",
            "tun",
            "tap",
        )
        return not n.startswith(ignored_prefixes)

    def _snapshot_interfaces(self) -> Dict[str, Tuple[int, int]]:
        pernic = psutil.net_io_counters(pernic=True)
        stats = psutil.net_if_stats()
        snapshot: Dict[str, Tuple[int, int]] = {}

        for name, counters in pernic.items():
            iface_stats = stats.get(name)
            if iface_stats is not None and not iface_stats.isup:
                continue
            if not self._is_relevant_iface(name):
                continue
            snapshot[name] = (int(counters.bytes_sent), int(counters.bytes_recv))

        # Fall back to aggregate counters if filtering removes everything.
        if not snapshot:
            agg = psutil.net_io_counters(pernic=False)
            snapshot["__aggregate__"] = (int(agg.bytes_sent), int(agg.bytes_recv))

        return snapshot
    
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
        current = self._snapshot_interfaces()
        
        # First run - just save the baseline
        if not self._initialized:
            self._last_pernic = current
            self._last_time = now
            self._initialized = True
            return SpeedData(0, 0, "KB/s", "KB/s", "0.0", "0.0")
        
        # Calculate speed from the difference
        elapsed = max(now - self._last_time, 0.1)

        sent_delta = 0
        recv_delta = 0
        for name, (sent, recv) in current.items():
            prev = self._last_pernic.get(name)
            if prev is None:
                continue
            prev_sent, prev_recv = prev
            sent_delta += sent - prev_sent
            recv_delta += recv - prev_recv

        # Interface resets/rollovers can produce negative deltas; clamp to 0.
        download = max(recv_delta / elapsed, 0.0)
        upload = max(sent_delta / elapsed, 0.0)
        
        self._last_pernic = current
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
