# PerfMonitor - Floating performance widget (multi-platform)
# Shows network speed, CPU, RAM, GPU stats and an optional floating clock.

import tkinter as tk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from speed_monitor import SpeedMonitor
from system_monitor import SystemMonitor
from fullscreen_detector import FullscreenDetector
from settings_manager import SettingsManager
from system_tray import SystemTray
from time_widget import TimeWidget
from platform_backends.transparency import apply_tk_transparency


class PerfMonitor:
    """The main stats widget window."""

    UPDATE_MS = 700
    FULLSCREEN_CHECK_MS = 1000
    POSITION_SAVE_MS = 5000
    TOPMOST_MS = 3500

    TRANSPARENT = "#010101"

    # ─────────────────────────────── init ──────────────────────────────────────

    def __init__(self):
        self.settings = SettingsManager()
        self.speed = SpeedMonitor()
        self.system = SystemMonitor()
        self.fullscreen = FullscreenDetector()

        self._visible = True
        self._hidden_fullscreen = False
        self._supports_tray = sys.platform == "win32"

        # Initialize UI variables for linter/safety
        self.root: tk.Tk = None # type: ignore
        self.frame: tk.Frame = None # type: ignore
        self.row1: tk.Frame = None # type: ignore
        self.row2: tk.Frame = None # type: ignore
        self.dl_arrow: tk.Label = None # type: ignore
        self.dl_speed: tk.Label = None # type: ignore
        self.ul_arrow: tk.Label = None # type: ignore
        self.ul_speed: tk.Label = None # type: ignore
        self.cpu_lbl: tk.Label = None # type: ignore
        self.cpu_val: tk.Label = None # type: ignore
        self.ram_lbl: tk.Label = None # type: ignore
        self.ram_val: tk.Label = None # type: ignore
        self.gpu_lbl: tk.Label = None # type: ignore
        self.gpu_val: tk.Label = None # type: ignore
        self.gpu_temp: tk.Label = None # type: ignore
        self.menu: tk.Menu = None # type: ignore
        self._startup_var: tk.BooleanVar = None # type: ignore
        self._show_net_var: tk.BooleanVar = None # type: ignore
        self._show_cpu_var: tk.BooleanVar = None # type: ignore
        self._show_ram_var: tk.BooleanVar = None # type: ignore
        self._show_gpu_var: tk.BooleanVar = None # type: ignore
        self._show_time_var: tk.BooleanVar = None # type: ignore
        self._time_fmt_var: tk.StringVar = None # type: ignore
        self._drag_x: int = 0
        self._drag_y: int = 0
        self._dragging: bool = False
        self._effective_bg: str = self.TRANSPARENT
        self._last_dl_text = ""
        self._last_ul_text = ""
        self._last_cpu_text = ""
        self._last_ram_text = ""
        self._last_gpu_text = ""
        self._last_gpu_temp_text = ""

        self.root = tk.Tk()
        self.root.title("PerfMonitor")
        self.root.overrideredirect(True)

        self._last_x = self.settings.get("window_x", 100)
        self._last_y = self.settings.get("window_y", 100)

        self._setup_transparency()
        self._create_ui()
        self._refresh_layout()
        self._setup_bindings()
        self._load_position()

        # Create independent time widget
        self.time_widget = TimeWidget(self.settings, self.root)
        if not self.settings.get("show_time", True):
            self.time_widget.hide()

        self.tray = SystemTray(
            on_show=self._show,
            on_hide=self._hide,
            on_exit=self._exit
        )

        self._last_x = self.settings.get("window_x", 100)
        self._last_y = self.settings.get("window_y", 100)

        self._start_loops()
        self.root.protocol("WM_DELETE_WINDOW", self._hide if self._supports_tray else self._exit)

    # ─────────────────────────────── transparency ──────────────────────────────

    def _setup_transparency(self):
        self._effective_bg = apply_tk_transparency(self.root, self.TRANSPARENT)

    @property
    def _bg(self):
        return self._effective_bg

    # ─────────────────────────────── UI creation ───────────────────────────────

    def _create_ui(self):
        """Create all label widgets (but do NOT pack them yet)."""
        bg = self._bg

        self.frame = tk.Frame(self.root, bg=bg)
        self.frame.pack(fill=tk.BOTH, expand=True)

        arrow_font  = ("Arial", 12, "bold")
        value_font  = ("Arial", 11)
        label_font  = ("Arial", 11, "bold")
        white       = "#FFFFFF"

        # ── Row 1 ──────────────────────────────────────────────────────────────
        self.row1 = tk.Frame(self.frame, bg=bg)

        self.dl_arrow = tk.Label(self.row1, text="▼", font=arrow_font, fg="#FF6B6B", bg=bg)
        self.dl_speed = tk.Label(self.row1, text="0 KB/s", font=value_font, fg=white,
                                 bg=bg, width=11, anchor="w")

        self.cpu_lbl = tk.Label(self.row1, text="CPU", font=label_font, fg="#74C0FC", bg=bg)
        self.cpu_val = tk.Label(self.row1, text="0%",  font=value_font,  fg=white, bg=bg, width=4, anchor="e")

        self.ram_lbl = tk.Label(self.row1, text="RAM", font=label_font, fg="#B197FC", bg=bg)
        self.ram_val = tk.Label(self.row1, text="0%",  font=value_font,  fg=white, bg=bg, width=4, anchor="e")

        # ── Row 2 ──────────────────────────────────────────────────────────────
        self.row2 = tk.Frame(self.frame, bg=bg)

        self.ul_arrow = tk.Label(self.row2, text="▲", font=arrow_font, fg="#51CF66", bg=bg)
        self.ul_speed = tk.Label(self.row2, text="0 KB/s", font=value_font, fg=white,
                                 bg=bg, width=11, anchor="w")

        self.gpu_lbl  = tk.Label(self.row2, text="GPU",  font=label_font, fg="#FFA94D", bg=bg)
        self.gpu_val  = tk.Label(self.row2, text="0%",   font=value_font,  fg=white, bg=bg, width=4, anchor="e")
        self.gpu_temp = tk.Label(self.row2, text="",     font=value_font,  fg="#FF8888", bg=bg, width=5, anchor="e")

    def _refresh_layout(self):
        """
        Unpack all inner widgets and re-pack only the enabled ones.
        Call this whenever a toggle changes.
        """
        show_net = self.settings.get("show_network", True)
        show_cpu = self.settings.get("show_cpu", True)
        show_ram = self.settings.get("show_ram", True)
        show_gpu = self.settings.get("show_gpu", True)

        # ── Forget everything ─────────────────────────────────────────────────
        for w in [self.dl_arrow, self.dl_speed, self.cpu_lbl, self.cpu_val,
                  self.ram_lbl, self.ram_val, self.ul_arrow, self.ul_speed,
                  self.gpu_lbl, self.gpu_val, self.gpu_temp,
                  self.row1, self.row2]:
            w.pack_forget()

        # ── Row 1 ─────────────────────────────────────────────────────────────
        row1_has_content = show_net or show_cpu or show_ram
        if row1_has_content:
            self.row1.pack(fill=tk.X)
            if show_net:
                self.dl_arrow.pack(side=tk.LEFT)
                self.dl_speed.pack(side=tk.LEFT, padx=(2, 4))
            if show_cpu:
                self.cpu_lbl.pack(side=tk.LEFT)
                self.cpu_val.pack(side=tk.LEFT)
            if show_ram:
                self.ram_lbl.pack(side=tk.LEFT, padx=(4, 0))
                self.ram_val.pack(side=tk.LEFT)

        # ── Row 2 ─────────────────────────────────────────────────────────────
        row2_has_content = show_net or show_gpu
        if row2_has_content:
            self.row2.pack(fill=tk.X)
            if show_net:
                self.ul_arrow.pack(side=tk.LEFT)
                self.ul_speed.pack(side=tk.LEFT, padx=(2, 4))
            if show_gpu:
                self.gpu_lbl.pack(side=tk.LEFT)
                self.gpu_val.pack(side=tk.LEFT)
                self.gpu_temp.pack(side=tk.LEFT, padx=(4, 0))

        # Force geometry update so window auto-shrinks to content
        self.root.update_idletasks()

    # ─────────────────────────────── drag ──────────────────────────────────────

    def _all_widgets(self):
        return [
            self.root, self.frame, self.row1, self.row2,
            self.dl_arrow, self.dl_speed, self.ul_arrow, self.ul_speed,
            self.cpu_lbl, self.cpu_val, self.ram_lbl, self.ram_val,
            self.gpu_lbl, self.gpu_val, self.gpu_temp,
        ]

    def _setup_bindings(self):
        """Setup all mouse bindings (drag and right-click) for all widgets."""
        self._drag_x = 0
        self._drag_y = 0
        self._dragging = False

        self.menu = tk.Menu(self.root, tearoff=0)
        self._init_menu()

        def start_drag(e):
            self._drag_x = e.x
            self._drag_y = e.y
            self._dragging = True

        def do_drag(e):
            if self._dragging:
                x = self.root.winfo_x() + e.x - self._drag_x
                y = self.root.winfo_y() + e.y - self._drag_y
                self.root.geometry(f"+{x}+{y}")

        def stop_drag(e):
            self._dragging = False
            self._save_position()

        def show_menu(e):
            self._startup_var.set(SettingsManager.is_in_startup())
            self.menu.tk_popup(e.x_root, e.y_root)

        for w in self._all_widgets():
            if not w: continue
            w.bind("<Button-1>", start_drag)
            w.bind("<B1-Motion>", do_drag)
            w.bind("<ButtonRelease-1>", stop_drag)
            w.bind("<Button-3>", show_menu)

    def _init_menu(self):
        """Build the right-click menu structure."""
        # ── Startup ───────────────────────────────────────────────────────────
        self._startup_var = tk.BooleanVar(value=SettingsManager.is_in_startup())
        self.menu.add_checkbutton(
            label="Start with OS",
            variable=self._startup_var,
            command=self._toggle_startup
        )
        self.menu.add_separator()

        # ── Monitors submenu ──────────────────────────────────────────────────
        monitors_menu = tk.Menu(self.menu, tearoff=0)

        self._show_net_var = tk.BooleanVar(value=self.settings.get("show_network", True))
        monitors_menu.add_checkbutton(
            label="Network Speed",
            variable=self._show_net_var,
            command=lambda: self._toggle_monitor("show_network", self._show_net_var)
        )

        self._show_cpu_var = tk.BooleanVar(value=self.settings.get("show_cpu", True))
        monitors_menu.add_checkbutton(
            label="CPU",
            variable=self._show_cpu_var,
            command=lambda: self._toggle_monitor("show_cpu", self._show_cpu_var)
        )

        self._show_ram_var = tk.BooleanVar(value=self.settings.get("show_ram", True))
        monitors_menu.add_checkbutton(
            label="RAM",
            variable=self._show_ram_var,
            command=lambda: self._toggle_monitor("show_ram", self._show_ram_var)
        )

        self._show_gpu_var = tk.BooleanVar(value=self.settings.get("show_gpu", True))
        monitors_menu.add_checkbutton(
            label="GPU + Temp",
            variable=self._show_gpu_var,
            command=lambda: self._toggle_monitor("show_gpu", self._show_gpu_var)
        )

        monitors_menu.add_separator()

        self._show_time_var = tk.BooleanVar(value=self.settings.get("show_time", True))
        monitors_menu.add_checkbutton(
            label="Clock Widget",
            variable=self._show_time_var,
            command=self._toggle_time_widget
        )

        self.menu.add_cascade(label="Monitors", menu=monitors_menu)

        # ── Time settings submenu ─────────────────────────────────────────────
        time_menu = tk.Menu(self.menu, tearoff=0)

        self._time_fmt_var = tk.StringVar(value=self.settings.get("time_fmt", "12h"))
        time_menu.add_radiobutton(
            label="12-hour format", variable=self._time_fmt_var,
            value="12h", command=self._update_time_fmt
        )
        time_menu.add_radiobutton(
            label="24-hour format", variable=self._time_fmt_var,
            value="24h", command=self._update_time_fmt
        )
        time_menu.add_separator()
        time_menu.add_command(label="Set Timezone (GMT offset)…", command=self._open_timezone_dialog)

        self.menu.add_cascade(label="Clock Settings", menu=time_menu)
        self.menu.add_separator()

        # ── Hide / Exit ───────────────────────────────────────────────────────
        if self._supports_tray:
            self.menu.add_command(label="Hide", command=self._hide)
            self.menu.add_separator()
        self.menu.add_command(label="Exit", command=self._exit)

        def show(e):
            self._startup_var.set(SettingsManager.is_in_startup())
            self.menu.tk_popup(e.x_root, e.y_root)

        for w in self._all_widgets():
            w.bind("<Button-3>", show)

    # ─────────────────────────────── toggle helpers ────────────────────────────

    def _toggle_startup(self):
        if self._startup_var.get():
            SettingsManager.add_to_startup()
        else:
            SettingsManager.remove_from_startup()

    def _toggle_monitor(self, key: str, var: tk.BooleanVar):
        self.settings.set(key, var.get())
        self._refresh_layout()
        # Ensure new layout widgets have bindings (though they should persist)
        self._setup_bindings()

    def _toggle_time_widget(self):
        show = self._show_time_var.get()
        self.settings.set("show_time", show)
        if show:
            self.time_widget.show()
        else:
            self.time_widget.hide()

    def _update_time_fmt(self):
        self.settings.set("time_fmt", self._time_fmt_var.get())

    def _open_timezone_dialog(self):
        """Simple dialog to input a GMT offset (e.g. +5.5 or -7)."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Set Timezone")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)

        bg = "#1E1E2E"
        fg = "#FFFFFF"
        dialog.configure(bg=bg)

        tk.Label(
            dialog, text="GMT Offset (e.g. +5.5 or -7):",
            bg=bg, fg=fg, font=("Arial", 10)
        ).grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")

        current_offset = self.settings.get("time_offset", 0.0)
        entry_var = tk.StringVar(value=str(current_offset))
        entry = tk.Entry(dialog, textvariable=entry_var, width=10,
                         bg="#2E2E3E", fg=fg, insertbackground=fg,
                         font=("Arial", 10), relief=tk.FLAT)
        entry.grid(row=1, column=0, padx=12, pady=4)

        err_lbl = tk.Label(dialog, text="", bg=bg, fg="#FF6B6B", font=("Arial", 9))
        err_lbl.grid(row=2, column=0, padx=12)

        def apply():
            try:
                val = float(entry_var.get())
                if not (-14.0 <= val <= 14.0):
                    raise ValueError
                self.settings.set("time_offset", val)
                dialog.destroy()
            except ValueError:
                err_lbl.config(text="Enter a number between -14 and +14")

        btn_frame = tk.Frame(dialog, bg=bg)
        btn_frame.grid(row=3, column=0, pady=10, padx=12, sticky="e")

        tk.Button(
            btn_frame, text="Cancel", command=dialog.destroy,
            bg="#333344", fg=fg, relief=tk.FLAT, padx=8,
            font=("Arial", 9)
        ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            btn_frame, text="Apply", command=apply,
            bg="#5C7CFA", fg=fg, relief=tk.FLAT, padx=8,
            font=("Arial", 9, "bold")
        ).pack(side=tk.LEFT)

        dialog.grab_set()

    # ─────────────────────────────── position ──────────────────────────────────

    def _load_position(self):
        x = self.settings.get("window_x", 100)
        y = self.settings.get("window_y", 100)

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
        self.root.after(self.POSITION_SAVE_MS, self._auto_save) # type: ignore

    # ─────────────────────────────── keep on top ───────────────────────────────

    def _keep_on_top(self):
        if self._visible and not self._hidden_fullscreen:
            try:
                self.root.attributes("-topmost", True)
                self.root.lift()
            except tk.TclError:
                return
        self.root.after(self.TOPMOST_MS, self._keep_on_top) # type: ignore

    def _set_label_text(self, label: tk.Label, value: str, cache_attr: str):
        """Only update Tk label text when value changed to reduce UI churn."""
        if getattr(self, cache_attr) != value:
            label.config(text=value)
            setattr(self, cache_attr, value)

    # ─────────────────────────────── update loop ───────────────────────────────

    def _update(self):
        if not self._visible or self._hidden_fullscreen:
            self.root.after(self.UPDATE_MS, self._update) # type: ignore
            return

        try:
            if self.settings.get("show_network", True):
                s = self.speed.get_speed()
                dl_text = f"{s.download_display} {s.download_unit}"
                ul_text = f"{s.upload_display} {s.upload_unit}"
                self._set_label_text(self.dl_speed, dl_text, "_last_dl_text")
                self._set_label_text(self.ul_speed, ul_text, "_last_ul_text")

            st = self.system.get_stats()

            if self.settings.get("show_cpu", True):
                self._set_label_text(self.cpu_val, st.cpu_display, "_last_cpu_text")

            if self.settings.get("show_ram", True):
                self._set_label_text(self.ram_val, st.ram_display, "_last_ram_text")

            if self.settings.get("show_gpu", True):
                gpu_temp_text = st.gpu_temp_display if st.gpu_temp is not None else ""
                self._set_label_text(self.gpu_val, st.gpu_display, "_last_gpu_text")
                self._set_label_text(self.gpu_temp, gpu_temp_text, "_last_gpu_temp_text")
        except tk.TclError:
            pass

        self.root.after(self.UPDATE_MS, self._update)

    # ─────────────────────────────── fullscreen ────────────────────────────────

    def _check_fullscreen(self):
        try:
            fs = self.fullscreen.should_hide()

            if fs and not self._hidden_fullscreen:
                self._hidden_fullscreen = True
                if self._visible:
                    self.root.withdraw()
                self.time_widget.set_fullscreen_hidden(True)

            elif not fs and self._hidden_fullscreen:
                self._hidden_fullscreen = False
                if self._visible:
                    self.root.deiconify()
                self.time_widget.set_fullscreen_hidden(False)

        except Exception:
            pass

        self.root.after(self.FULLSCREEN_CHECK_MS, self._check_fullscreen) # type: ignore

    # ─────────────────────────────── lifecycle ─────────────────────────────────

    def _start_loops(self):
        self._update()
        self._check_fullscreen()
        self._auto_save()
        self._keep_on_top()

    def _show(self):
        self._visible = True
        if not self._hidden_fullscreen:
            self.root.deiconify()
        if self._supports_tray:
            self.tray.set_visible(True)

    def _hide(self):
        if not self._supports_tray:
            self._exit()
            return

        self._save_position()
        self._visible = False
        self.root.withdraw()
        self.tray.set_visible(False)

    def _exit(self):
        self._save_position()
        self.tray.stop()
        self.fullscreen.stop()
        self.system.close()
        self.time_widget.destroy()
        self.root.quit()
        self.root.destroy()

    def run(self):
        if self._supports_tray:
            self.tray.start()
        self.root.mainloop()


if __name__ == "__main__":
    app = PerfMonitor()
    app.run()
