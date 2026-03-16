import ctypes


class WindowsFullscreenBackend:
    """Windows fullscreen detection using foreground window bounds."""

    def __init__(self):
        self._user32 = ctypes.windll.user32

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        self._rect_type = RECT
        self._user32.GetForegroundWindow.restype = ctypes.c_void_p
        self._user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(RECT)]
        self._user32.GetWindowRect.restype = ctypes.c_int

    def _get_foreground_window_info(self):
        try:
            hwnd = self._user32.GetForegroundWindow()
            if not hwnd:
                return None, None

            rect = self._rect_type()
            ok = self._user32.GetWindowRect(hwnd, ctypes.byref(rect))
            if not ok:
                return None, None

            return hwnd, (rect.left, rect.top, rect.right, rect.bottom)
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
