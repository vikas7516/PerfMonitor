# Saves window position and handles Windows startup registry

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Conditionally import winreg for Windows
if sys.platform == "win32":
    import winreg


class SettingsManager:
    """Saves settings to AppData and manages Windows startup."""
    
    APP_NAME = "PerfMonitor"
    
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
        elif sys.platform == "darwin":
            config_dir = Path.home() / "Library" / "Application Support" / self.APP_NAME
        else: # Linux
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
        """Add to OS startup."""
        exe_path = cls.get_exe_path()
        
        if sys.platform == "win32":
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0, winreg.KEY_SET_VALUE
                )
                winreg.SetValueEx(key, cls.APP_NAME, 0, winreg.REG_SZ, exe_path)
                winreg.CloseKey(key)
                return True
            except Exception:
                return False
                
        elif sys.platform == "darwin":
            plist_path = Path.home() / "Library" / "LaunchAgents" / f"com.{cls.APP_NAME.lower()}.plist"
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.{cls.APP_NAME.lower()}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{exe_path.split()[0]}</string>
        <string>{exe_path.split()[1] if len(exe_path.split()) > 1 else ""}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>"""
            try:
                plist_path.parent.mkdir(parents=True, exist_ok=True)
                plist_path.write_text(plist_content)
                return True
            except Exception:
                return False
                
        else: # Linux
            desktop_path = Path.home() / ".config" / "autostart" / f"{cls.APP_NAME.lower()}.desktop"
            desktop_content = f"""[Desktop Entry]
Type=Application
Exec={exe_path}
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
            except Exception:
                return False
    
    @classmethod
    def remove_from_startup(cls) -> bool:
        """Remove from OS startup."""
        if sys.platform == "win32":
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
            except Exception:
                return False
                
        elif sys.platform == "darwin":
            plist_path = Path.home() / "Library" / "LaunchAgents" / f"com.{cls.APP_NAME.lower()}.plist"
            if plist_path.exists():
                try:
                    plist_path.unlink()
                    return True
                except Exception:
                    return False
            return True
            
        else: # Linux
            desktop_path = Path.home() / ".config" / "autostart" / f"{cls.APP_NAME.lower()}.desktop"
            if desktop_path.exists():
                try:
                    desktop_path.unlink()
                    return True
                except Exception:
                    return False
            return True
    
    @classmethod
    def is_in_startup(cls) -> bool:
        """Check if we're set to start with OS."""
        if sys.platform == "win32":
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
            except Exception:
                return False
                
        elif sys.platform == "darwin":
            plist_path = Path.home() / "Library" / "LaunchAgents" / f"com.{cls.APP_NAME.lower()}.plist"
            return plist_path.exists()
            
        else: # Linux
            desktop_path = Path.home() / ".config" / "autostart" / f"{cls.APP_NAME.lower()}.desktop"
            return desktop_path.exists()
