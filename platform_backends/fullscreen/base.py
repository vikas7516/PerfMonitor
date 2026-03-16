from typing import Protocol


class FullscreenBackend(Protocol):
    """Platform backend API for fullscreen detection."""

    def should_hide(self) -> bool:
        ...
