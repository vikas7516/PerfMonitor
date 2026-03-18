"""Compatibility wrapper for fullscreen detection.

The implementation is delegated to platform-specific backends in
`platform_backends/fullscreen` so each OS can evolve independently.
"""

import threading
import logging

from platform_backends.fullscreen import create_fullscreen_backend


class FullscreenDetector:
    """Public fullscreen detector API used by the app."""

    POLL_SECONDS = 1.2
    _LOG = logging.getLogger(__name__)

    def __init__(self):
        self._backend = create_fullscreen_backend()
        self._hide_cached = False
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _poll_loop(self):
        while not self._stop_event.is_set():
            value = False
            try:
                value = bool(self._backend.should_hide())
            except Exception:
                self._LOG.debug("Fullscreen backend poll failed", exc_info=True)
                value = False

            with self._lock:
                self._hide_cached = value

            self._stop_event.wait(self.POLL_SECONDS)

    def should_hide(self) -> bool:
        with self._lock:
            return self._hide_cached

    def stop(self):
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=1.5)
