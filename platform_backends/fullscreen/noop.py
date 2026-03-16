class NoopFullscreenBackend:
    """Fallback backend for platforms without fullscreen support."""

    def should_hide(self) -> bool:
        return False
