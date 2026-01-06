# System tray icon with right-click menu

import threading
import os
from typing import Callable, Optional
from PIL import Image
import pystray
from pystray import MenuItem as Item

from settings_manager import SettingsManager


class SystemTray:
    """Tray icon that sits in the taskbar."""
    
    def __init__(
        self,
        on_show: Callable[[], None],
        on_hide: Callable[[], None],
        on_exit: Callable[[], None]
    ):
        self.on_show = on_show
        self.on_hide = on_hide
        self.on_exit = on_exit
        
        self._icon: Optional[pystray.Icon] = None
        self._visible = True
        self._thread: Optional[threading.Thread] = None
    
    def _load_icon(self) -> Image.Image:
        """Try to load icon.png, fall back to generated icon."""
        app_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(app_dir, "icon.png")
        
        if os.path.exists(icon_path):
            try:
                img = Image.open(icon_path)
                img = img.resize((64, 64), Image.Resampling.LANCZOS)
                return img
            except Exception:
                pass
        
        return self._make_fallback_icon()
    
    def _make_fallback_icon(self) -> Image.Image:
        """Simple icon if icon.png is missing."""
        from PIL import ImageDraw
        
        size = 64
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        draw.rounded_rectangle([2, 2, size-2, size-2], radius=10, fill=(25, 25, 35, 250))
        draw.polygon([(12, 16), (24, 16), (18, 32)], fill=(255, 107, 107))  # Red arrow
        draw.polygon([(12, 48), (24, 48), (18, 32)], fill=(81, 207, 102))   # Green arrow
        draw.rounded_rectangle([38, 14, 56, 28], radius=3, fill=(116, 192, 252))  # Blue bar
        draw.rounded_rectangle([38, 36, 56, 50], radius=3, fill=(255, 169, 77))   # Orange bar
        
        return img
    
    def _toggle_visibility(self, icon, item):
        if self._visible:
            self.on_hide()
            self._visible = False
        else:
            self.on_show()
            self._visible = True
    
    def _get_visibility_text(self, item) -> str:
        return "Hide" if self._visible else "Show"
    
    def _is_startup_enabled(self, item) -> bool:
        return SettingsManager.is_in_startup()
    
    def _toggle_startup(self, icon, item):
        if SettingsManager.is_in_startup():
            SettingsManager.remove_from_startup()
        else:
            SettingsManager.add_to_startup()
    
    def _on_exit(self, icon, item):
        self.on_exit()
    
    def start(self):
        """Start the tray icon in a background thread."""
        menu = pystray.Menu(
            Item(self._get_visibility_text, self._toggle_visibility, default=True),
            Item("Start with Windows", self._toggle_startup, checked=self._is_startup_enabled),
            pystray.Menu.SEPARATOR,
            Item("Exit", self._on_exit)
        )
        
        self._icon = pystray.Icon(
            "PerfMonitor",
            self._load_icon(),
            "PerfMonitor",
            menu
        )
        
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()
    
    def stop(self):
        if self._icon:
            self._icon.stop()
    
    def set_visible(self, visible: bool):
        self._visible = visible
