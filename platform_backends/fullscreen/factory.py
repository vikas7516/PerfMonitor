import sys

from .base import FullscreenBackend


def create_fullscreen_backend() -> FullscreenBackend:
    """Load only the active platform backend to keep build artifacts lean."""
    if sys.platform == "win32":
        from .windows import WindowsFullscreenBackend

        return WindowsFullscreenBackend()

    if sys.platform == "linux":
        from .linux import LinuxFullscreenBackend

        return LinuxFullscreenBackend()

    from .noop import NoopFullscreenBackend

    return NoopFullscreenBackend()
