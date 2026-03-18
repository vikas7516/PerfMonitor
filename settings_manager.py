# Saves window position and handles Windows startup registry

import json
import logging
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

# Conditionally import winreg for Windows
if sys.platform == "win32":
    import winreg


class SettingsManager:
    """Saves settings to AppData and manages Windows startup."""
    
    APP_NAME = "PerfMonitor"
    _LOG = logging.getLogger(__name__)
    
    DEFAULT_SETTINGS = {
        "window_x": 100,
        "window_y": 100,
        "show_network": True,
        "show_cpu": True,
        "show_ram": True,
        "show_gpu": True,
        "show_time": True,
        "time_fmt": "12h",
        "time_offset": 0.0,
        "time_x": 100,
        "time_y": 200,
        "window_w": 250,
        "window_h": 60,
        "time_w": 150,
        "time_h": 50,
    }
    
    def __init__(self):
        self._settings: Dict[str, Any] = {}
        self._config_path = self._get_config_path()
        self._load_settings()
    
    def _get_config_path(self) -> Path:
        """Config goes in OS-specific app data directory."""
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
            config_dir = Path(appdata) / self.APP_NAME
        else:  # Linux and other Unix-like platforms
            config_dir = Path.home() / ".config" / self.APP_NAME
            
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
            self._LOG.exception("Failed to save settings file")
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        self._settings[key] = value
        self.save_settings()
    
    @classmethod
    def _startup_command_parts(cls) -> List[str]:
        """Build startup command as argv parts for reliable per-platform quoting."""
        if getattr(sys, 'frozen', False):
            return [sys.executable]

        script = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))

        if sys.platform == "win32":
            py_exec = Path(sys.executable)
            pythonw = py_exec.with_name("pythonw.exe")
            interpreter = str(pythonw if pythonw.exists() else py_exec)
            return [interpreter, script]

        return [sys.executable, script]

    @classmethod
    def _windows_run_value(cls, command_parts: List[str]) -> str:
        """Convert argv into a Windows Run key command string."""
        return subprocess.list2cmdline(command_parts)

    @classmethod
    def _linux_exec_value(cls, command_parts: List[str]) -> str:
        """Convert argv into a desktop-entry Exec string."""
        return shlex.join(command_parts)

    @classmethod
    def _linux_autostart_path(cls) -> Path:
        return Path.home() / ".config" / "autostart" / f"{cls.APP_NAME.lower()}.desktop"

    @classmethod
    def add_to_startup(cls) -> bool:
        """Add to OS startup."""
        command_parts = cls._startup_command_parts()
        
        if sys.platform == "win32":
            try:
                run_value = cls._windows_run_value(command_parts)
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0, winreg.KEY_SET_VALUE
                ) as key:
                    winreg.SetValueEx(key, cls.APP_NAME, 0, winreg.REG_SZ, run_value)
                return True
            except OSError:
                cls._LOG.exception("Failed to add startup registry entry")
                return False

        else:  # Linux and other Unix-like platforms
            desktop_path = cls._linux_autostart_path()
            desktop_content = f"""[Desktop Entry]
Type=Application
Exec={cls._linux_exec_value(command_parts)}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name={cls.APP_NAME}
Comment=Performance Monitor Widget
"""
            try:
                desktop_path.parent.mkdir(parents=True, exist_ok=True)
                desktop_path.write_text(desktop_content)
                return True
            except OSError:
                cls._LOG.exception("Failed to write Linux autostart desktop file")
                return False
    
    @classmethod
    def remove_from_startup(cls) -> bool:
        """Remove from OS startup."""
        if sys.platform == "win32":
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0, winreg.KEY_SET_VALUE
                ) as key:
                    try:
                        winreg.DeleteValue(key, cls.APP_NAME)
                    except FileNotFoundError:
                        pass
                return True
            except OSError:
                cls._LOG.exception("Failed to remove startup registry entry")
                return False

        else:  # Linux and other Unix-like platforms
            desktop_path = cls._linux_autostart_path()
            if desktop_path.exists():
                try:
                    desktop_path.unlink()
                    return True
                except OSError:
                    cls._LOG.exception("Failed to remove Linux autostart desktop file")
                    return False
            return True
    
    @classmethod
    def is_in_startup(cls) -> bool:
        """Check if we're set to start with OS."""
        if sys.platform == "win32":
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0, winreg.KEY_QUERY_VALUE
                ) as key:
                    try:
                        winreg.QueryValueEx(key, cls.APP_NAME)
                        return True
                    except FileNotFoundError:
                        return False
            except OSError:
                return False

        else:  # Linux and other Unix-like platforms
            desktop_path = cls._linux_autostart_path()
            return desktop_path.exists()
