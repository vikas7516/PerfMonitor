# Saves window position and handles Windows startup registry

import json
import os
import sys
import winreg
from pathlib import Path
from typing import Any, Dict


class SettingsManager:
    """Saves settings to AppData and manages Windows startup."""
    
    APP_NAME = "PerfMonitor"
    
    DEFAULT_SETTINGS = {
        "window_x": 100,
        "window_y": 100,
    }
    
    def __init__(self):
        self._settings: Dict[str, Any] = {}
        self._config_path = self._get_config_path()
        self._load_settings()
    
    def _get_config_path(self) -> Path:
        """Config goes in %APPDATA%/PerfMonitor/config.json"""
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        config_dir = Path(appdata) / self.APP_NAME
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.json"
    
    def _load_settings(self) -> None:
        """Load from file or use defaults."""
        try:
            if self._config_path.exists():
                with open(self._config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self._settings = {**self.DEFAULT_SETTINGS, **saved}
            else:
                self._settings = self.DEFAULT_SETTINGS.copy()
        except (json.JSONDecodeError, IOError):
            self._settings = self.DEFAULT_SETTINGS.copy()
    
    def save_settings(self) -> None:
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2)
        except IOError:
            pass
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        self._settings[key] = value
        self.save_settings()
    
    @classmethod
    def get_exe_path(cls) -> str:
        """Get the right path for startup - works for both .py and .exe"""
        if getattr(sys, 'frozen', False):
            return sys.executable
        else:
            script = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))
            return f'pythonw "{script}"'
    
    @classmethod
    def add_to_startup(cls) -> bool:
        """Add to Windows startup via registry."""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, cls.APP_NAME, 0, winreg.REG_SZ, cls.get_exe_path())
            winreg.CloseKey(key)
            return True
        except WindowsError:
            return False
    
    @classmethod
    def remove_from_startup(cls) -> bool:
        """Remove from Windows startup."""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            try:
                winreg.DeleteValue(key, cls.APP_NAME)
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)
            return True
        except WindowsError:
            return False
    
    @classmethod
    def is_in_startup(cls) -> bool:
        """Check if we're set to start with Windows."""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_QUERY_VALUE
            )
            try:
                winreg.QueryValueEx(key, cls.APP_NAME)
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except WindowsError:
            return False
