import ctypes


class WindowsFullscreenBackend:
    """Windows fullscreen detection using foreground window bounds."""

    def __init__(self):
        self._user32 = ctypes.windll.user32
        self._monitor_default_to_nearest = 0x00000002

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", ctypes.c_ulong),
            ]

        self._rect_type = RECT
        self._monitor_info_type = MONITORINFO
        self._user32.GetForegroundWindow.restype = ctypes.c_void_p
        self._user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(RECT)]
        self._user32.GetWindowRect.restype = ctypes.c_int
        self._user32.MonitorFromWindow.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        self._user32.MonitorFromWindow.restype = ctypes.c_void_p
        self._user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MONITORINFO)]
        self._user32.GetMonitorInfoW.restype = ctypes.c_int

    def _get_foreground_window_info(self):
        hwnd = self._user32.GetForegroundWindow()
        if not hwnd:
            return None, None

        rect = self._rect_type()
        ok = self._user32.GetWindowRect(hwnd, ctypes.byref(rect))
        if not ok:
            return None, None

        return hwnd, (rect.left, rect.top, rect.right, rect.bottom)

    def _get_monitor_rect(self, hwnd):
        monitor = self._user32.MonitorFromWindow(hwnd, self._monitor_default_to_nearest)
        if not monitor:
            return None

        info = self._monitor_info_type()
        info.cbSize = ctypes.sizeof(self._monitor_info_type)
        ok = self._user32.GetMonitorInfoW(monitor, ctypes.byref(info))
        if not ok:
            return None

        r = info.rcMonitor
        return (r.left, r.top, r.right, r.bottom)

    def _is_window_fullscreen(self, hwnd, rect) -> bool:
        if not hwnd or not rect:
            return False

        monitor_rect = self._get_monitor_rect(hwnd)
        if not monitor_rect:
            return False

        left, top, right, bottom = rect
        m_left, m_top, m_right, m_bottom = monitor_rect

        return (
            left <= m_left
            and top <= m_top
            and right >= m_right
            and bottom >= m_bottom
        )

    def should_hide(self) -> bool:
        hwnd, rect = self._get_foreground_window_info()
        if not hwnd:
            return False
        return self._is_window_fullscreen(hwnd, rect)
