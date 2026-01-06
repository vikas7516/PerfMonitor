# Handles detecting fullscreen apps so we can hide the widget during movies

import ctypes
from ctypes import wintypes
import win32gui
import win32process
import psutil


class FullscreenDetector:
    """Hides the widget when you're watching something fullscreen."""
    
    # Apps we care about - video players and browsers for streaming
    VIDEO_APPS = {
        # Media players
        "vlc.exe", "mpv.exe", "mpc-hc.exe", "mpc-hc64.exe", "mpc-be.exe",
        "mpc-be64.exe", "potplayer.exe", "potplayer64.exe", "kmplayer.exe",
        "wmplayer.exe", "movies & tv.exe", "video.ui.exe",
        
        # Browsers (Netflix, YouTube, etc.)
        "chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe",
        "vivaldi.exe", "iexplore.exe",
        
        # Streaming apps
        "netflix.exe", "amazonvideo.exe", "disney+.exe", "hulu.exe",
        "hbomax.exe", "peacock.exe", "paramountplus.exe",
        "prime video.exe", "spotify.exe", "plex.exe", "plex htpc.exe",
        "kodi.exe", "emby.exe", "jellyfin.exe"
    }
    
    def __init__(self):
        self._user32 = ctypes.windll.user32
    
    def _get_foreground_window_info(self):
        """Figure out what window is currently in focus."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None, None, None
            
            rect = win32gui.GetWindowRect(hwnd)
            
            # Get the process name from the window handle
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                process = psutil.Process(pid)
                process_name = process.name().lower()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                process_name = ""
            
            return hwnd, rect, process_name
        except Exception:
            return None, None, None
    
    def _is_window_fullscreen(self, hwnd, rect) -> bool:
        """Check if the window covers the entire screen."""
        if not hwnd or not rect:
            return False
        
        try:
            screen_width = self._user32.GetSystemMetrics(0)
            screen_height = self._user32.GetSystemMetrics(1)
            
            left, top, right, bottom = rect
            window_width = right - left
            window_height = bottom - top
            
            # Window is fullscreen if it covers everything
            return (left <= 0 and top <= 0 and
                    window_width >= screen_width and
                    window_height >= screen_height)
        except Exception:
            return False
    
    def should_hide(self) -> bool:
        """Returns True if we should hide - a video app is fullscreen."""
        hwnd, rect, process_name = self._get_foreground_window_info()
        
        if not hwnd:
            return False
        
        if not self._is_window_fullscreen(hwnd, rect):
            return False
        
        # Hide if it's any of our known video apps
        return process_name in self.VIDEO_APPS
