import importlib


class WindowsFullscreenBackend:
    """Windows fullscreen detection using foreground window bounds."""

    def __init__(self):
        import ctypes

        self._user32 = ctypes.windll.user32

    def _get_foreground_window_info(self):
        try:
            win32gui = importlib.import_module("win32gui")
            win32process = importlib.import_module("win32process")

            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None, None

            rect = win32gui.GetWindowRect(hwnd)
            _, _ = win32process.GetWindowThreadProcessId(hwnd)

            return hwnd, rect
        except Exception:
            return None, None

    def _is_window_fullscreen(self, hwnd, rect) -> bool:
        if not hwnd or not rect:
            return False

        try:
            screen_width = self._user32.GetSystemMetrics(0)
            screen_height = self._user32.GetSystemMetrics(1)

            left, top, right, bottom = rect
            window_width = right - left
            window_height = bottom - top

            return (
                left <= 0
                and top <= 0
                and window_width >= screen_width
                and window_height >= screen_height
            )
        except Exception:
            return False

    def should_hide(self) -> bool:
        hwnd, rect = self._get_foreground_window_info()
        if not hwnd:
            return False
        return self._is_window_fullscreen(hwnd, rect)
