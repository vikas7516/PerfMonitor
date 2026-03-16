# PerfMonitor - Floating performance widget for Windows
# Shows network speed, CPU, RAM, and GPU stats with a transparent overlay

import tkinter as tk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from speed_monitor import SpeedMonitor
from system_monitor import SystemMonitor
from fullscreen_detector import FullscreenDetector
from settings_manager import SettingsManager
from system_tray import SystemTray


class PerfMonitor:
    """The main widget window."""
    
    # How often to refresh (ms)
    UPDATE_MS = 500
    FULLSCREEN_CHECK_MS = 2000
    POSITION_SAVE_MS = 5000
    TOPMOST_MS = 500
    
    # This color becomes invisible
    TRANSPARENT = "#010101"
    
    def __init__(self):
        self.settings = SettingsManager()
        self.speed = SpeedMonitor()
        self.system = SystemMonitor()
        self.fullscreen = FullscreenDetector()
        
        # Main window setup
        self.root = tk.Tk()
        self.root.title("PerfMonitor")
        self.root.overrideredirect(True)
        
        self._setup_transparency()
        self._create_ui()
        self._setup_drag()
        self._setup_menu()
        self._load_position()
        
        self.tray = SystemTray(
            on_show=self._show,
            on_hide=self._hide,
            on_exit=self._exit
        )
        
        self._visible = True
        self._hidden_fullscreen = False
        self._last_x = self.settings.get("window_x", 100)
        self._last_y = self.settings.get("window_y", 100)
        
        self._start_loops()
        self.root.protocol("WM_DELETE_WINDOW", self._hide)
    
    def _setup_transparency(self):
        """Make the background invisible based on OS."""
        if sys.platform == "win32":
            self.root.configure(bg=self.TRANSPARENT)
            self.root.attributes("-transparentcolor", self.TRANSPARENT)
        elif sys.platform == "darwin":  # macOS
            self.root.configure(bg=self.TRANSPARENT)
            self.root.attributes("-transparent", True)
            # macOS Tkinter transparency is limited, -alpha handles overall opacity
        else:  # Linux (X11/Wayland)
            # On Linux, setting alpha makes the whole window translucent.
            # True "click-through" transparency requires an X11 compositor (like picom) 
            # and specific window hints which Tkinter doesn't easily expose.
            # A common workaround is a dark translucent background.
            self.root.configure(bg="#222222")
            self.root.attributes("-type", "dock") # Avoid window manager decorations
            self.root.wait_visibility(self.root)
            self.root.attributes("-alpha", 0.8)

        self.root.attributes("-topmost", True)
    
    def _keep_on_top(self):
        """Force the window to stay on top."""
        if not self._hidden_fullscreen and self._visible:
            try:
                self.root.attributes("-topmost", False)
                self.root.attributes("-topmost", True)
                self.root.lift()
            except tk.TclError:
                return
        self.root.after(self.TOPMOST_MS, self._keep_on_top)
    
    def _create_ui(self):
        """Build the two-row display."""
        self.frame = tk.Frame(self.root, bg=self.TRANSPARENT)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Fonts
        arrow = ("Arial", 12, "bold")
        value = ("Arial", 11)
        label = ("Arial", 11, "bold")
        white = "#FFFFFF"
        
        # Row 1: Download, CPU, RAM
        row1 = tk.Frame(self.frame, bg=self.TRANSPARENT)
        row1.pack(fill=tk.X)
        
        self.dl_arrow = tk.Label(row1, text="▼", font=arrow, fg="#FF6B6B", bg=self.TRANSPARENT)
        self.dl_arrow.pack(side=tk.LEFT)
        
        self.dl_speed = tk.Label(row1, text="0 KB/s", font=value, fg=white, bg=self.TRANSPARENT, width=11, anchor="w")
        self.dl_speed.pack(side=tk.LEFT, padx=(2, 4))
        
        self.cpu_lbl = tk.Label(row1, text="CPU", font=label, fg="#74C0FC", bg=self.TRANSPARENT)
        self.cpu_lbl.pack(side=tk.LEFT)
        
        self.cpu_val = tk.Label(row1, text="0%", font=value, fg=white, bg=self.TRANSPARENT, width=4, anchor="e")
        self.cpu_val.pack(side=tk.LEFT)
        
        self.ram_lbl = tk.Label(row1, text="RAM", font=label, fg="#B197FC", bg=self.TRANSPARENT)
        self.ram_lbl.pack(side=tk.LEFT, padx=(4, 0))
        
        self.ram_val = tk.Label(row1, text="0%", font=value, fg=white, bg=self.TRANSPARENT, width=4, anchor="e")
        self.ram_val.pack(side=tk.LEFT)
        
        # Row 2: Upload, GPU, Temp
        row2 = tk.Frame(self.frame, bg=self.TRANSPARENT)
        row2.pack(fill=tk.X)
        
        self.ul_arrow = tk.Label(row2, text="▲", font=arrow, fg="#51CF66", bg=self.TRANSPARENT)
        self.ul_arrow.pack(side=tk.LEFT)
        
        self.ul_speed = tk.Label(row2, text="0 KB/s", font=value, fg=white, bg=self.TRANSPARENT, width=11, anchor="w")
        self.ul_speed.pack(side=tk.LEFT, padx=(2, 4))
        
        self.gpu_lbl = tk.Label(row2, text="GPU", font=label, fg="#FFA94D", bg=self.TRANSPARENT)
        self.gpu_lbl.pack(side=tk.LEFT)
        
        self.gpu_val = tk.Label(row2, text="0%", font=value, fg=white, bg=self.TRANSPARENT, width=4, anchor="e")
        self.gpu_val.pack(side=tk.LEFT)
        
        self.gpu_temp = tk.Label(row2, text="", font=value, fg="#FF8888", bg=self.TRANSPARENT, width=5, anchor="e")
        self.gpu_temp.pack(side=tk.LEFT, padx=(4, 0))
        
        self.row1 = row1
        self.row2 = row2
    
    def _all_widgets(self):
        return [
            self.root, self.frame, self.row1, self.row2,
            self.dl_arrow, self.dl_speed, self.ul_arrow, self.ul_speed,
            self.cpu_lbl, self.cpu_val, self.ram_lbl, self.ram_val,
            self.gpu_lbl, self.gpu_val, self.gpu_temp,
        ]
    
    def _setup_drag(self):
        """Let user drag the widget around."""
        self._drag_x = 0
        self._drag_y = 0
        self._dragging = False
        
        def start(e):
            self._drag_x = e.x
            self._drag_y = e.y
            self._dragging = True
        
        def move(e):
            if self._dragging:
                x = self.root.winfo_x() + e.x - self._drag_x
                y = self.root.winfo_y() + e.y - self._drag_y
                self.root.geometry(f"+{x}+{y}")
        
        def stop(e):
            if self._dragging:
                self._dragging = False
                self._save_position()
        
        for w in self._all_widgets():
            w.bind("<Button-1>", start)
            w.bind("<B1-Motion>", move)
            w.bind("<ButtonRelease-1>", stop)
    
    def _setup_menu(self):
        """Right-click context menu."""
        self.menu = tk.Menu(self.root, tearoff=0)
        
        self._startup_var = tk.BooleanVar(value=SettingsManager.is_in_startup())
        self.menu.add_checkbutton(label="Start with Windows", variable=self._startup_var, command=self._toggle_startup)
        self.menu.add_separator()
        self.menu.add_command(label="Hide", command=self._hide)
        self.menu.add_separator()
        self.menu.add_command(label="Exit", command=self._exit)
        
        def show(e):
            self._startup_var.set(SettingsManager.is_in_startup())
            self.menu.tk_popup(e.x_root, e.y_root)
        
        for w in self._all_widgets():
            w.bind("<Button-3>", show)
    
    def _toggle_startup(self):
        if self._startup_var.get():
            SettingsManager.add_to_startup()
        else:
            SettingsManager.remove_from_startup()
    
    def _load_position(self):
        x = self.settings.get("window_x", 100)
        y = self.settings.get("window_y", 100)
        
        # Keep on screen
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, min(x, sw - 100))
        y = max(0, min(y, sh - 50))
        
        self.root.geometry(f"+{x}+{y}")
        self._last_x = x
        self._last_y = y
    
    def _save_position(self):
        try:
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            if x != self._last_x or y != self._last_y:
                self.settings.set("window_x", x)
                self.settings.set("window_y", y)
                self._last_x = x
                self._last_y = y
        except tk.TclError:
            pass
    
    def _auto_save(self):
        self._save_position()
        self.root.after(self.POSITION_SAVE_MS, self._auto_save)
    
    def _update(self):
        """Refresh all the stats."""
        if not self._visible or self._hidden_fullscreen:
            self.root.after(self.UPDATE_MS, self._update)
            return
        
        s = self.speed.get_speed()
        self.dl_speed.config(text=f"{s.download_display} {s.download_unit}")
        self.ul_speed.config(text=f"{s.upload_display} {s.upload_unit}")
        
        st = self.system.get_stats()
        self.cpu_val.config(text=st.cpu_display)
        self.ram_val.config(text=st.ram_display)
        self.gpu_val.config(text=st.gpu_display)
        self.gpu_temp.config(text=st.gpu_temp_display if st.gpu_temp else "")
        
        self.root.after(self.UPDATE_MS, self._update)
    
    def _check_fullscreen(self):
        """Hide during fullscreen video."""
        try:
            fs = self.fullscreen.should_hide()
            
            if fs and self._visible and not self._hidden_fullscreen:
                self._hidden_fullscreen = True
                self.root.withdraw()
            elif not fs and self._hidden_fullscreen:
                self._hidden_fullscreen = False
                if self._visible:
                    self.root.deiconify()
        except Exception:
            pass
        
        self.root.after(self.FULLSCREEN_CHECK_MS, self._check_fullscreen)
    
    def _start_loops(self):
        self._update()
        self._check_fullscreen()
        self._auto_save()
        self._keep_on_top()
    
    def _show(self):
        self._visible = True
        self.root.deiconify()
        self.tray.set_visible(True)
    
    def _hide(self):
        self._save_position()
        self._visible = False
        self.root.withdraw()
        self.tray.set_visible(False)
    
    def _exit(self):
        self._save_position()
        self.tray.stop()
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        self.tray.start()
        self.root.mainloop()


if __name__ == "__main__":
    app = PerfMonitor()
    app.run()
