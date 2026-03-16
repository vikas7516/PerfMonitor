# Independent floating Time/Date widget
# Always on top, draggable, configurable timezone and format

import tkinter as tk
import sys
import time
import datetime


class TimeWidget:
    """A standalone draggable floating clock/date widget."""

    TIME_REFRESH_MS = 1000
    TOPMOST_MS = 500

    TRANSPARENT = "#010101"

    def __init__(self, settings, root):
        """
        :param settings: SettingsManager instance (shared with main widget).
        :param root: The main Tk() root – TimeWidget uses a Toplevel on top of it.
        """
        self.settings = settings
        self._root = root

        self._visible = True
        self._hidden_fullscreen = False

        # Separate Toplevel window
        self.win = tk.Toplevel(root)
        self.win.title("PerfMonitor-Clock")
        self.win.overrideredirect(True)
        self._setup_transparency()

        self._create_ui()
        self._setup_drag()
        self._load_position()
        self._start_loops()

    # ─────────────────────────────── transparency ──────────────────────────────

    def _setup_transparency(self):
        if sys.platform == "win32":
            self.win.configure(bg=self.TRANSPARENT)
            self.win.attributes("-transparentcolor", self.TRANSPARENT)
        elif sys.platform == "darwin":
            self.win.configure(bg=self.TRANSPARENT)
            self.win.attributes("-transparent", True)
        else:  # Linux
            self.win.configure(bg="#222222")
            self.win.attributes("-type", "dock")
            self.win.wait_visibility(self.win)
            self.win.attributes("-alpha", 0.8)

        self.win.attributes("-topmost", True)

    # ─────────────────────────────── UI ────────────────────────────────────────

    def _create_ui(self):
        bg = self.TRANSPARENT if sys.platform != "linux" else "#222222"

        self.frame = tk.Frame(self.win, bg=bg)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.time_lbl = tk.Label(
            self.frame, text="--:-- --",
            font=("Arial", 13, "bold"), fg="#FFE066", bg=bg
        )
        self.time_lbl.pack(side=tk.TOP, padx=6, pady=(2, 0))

        self.date_lbl = tk.Label(
            self.frame, text="--- --, ----",
            font=("Arial", 9), fg="#CCCCCC", bg=bg
        )
        self.date_lbl.pack(side=tk.TOP, padx=6, pady=(0, 2))

    def _all_widgets(self):
        return [self.win, self.frame, self.time_lbl, self.date_lbl]

    # ─────────────────────────────── drag ──────────────────────────────────────

    def _setup_drag(self):
        self._drag_x = 0
        self._drag_y = 0
        self._dragging = False

        def start(e):
            self._drag_x = e.x
            self._drag_y = e.y
            self._dragging = True

        def move(e):
            if self._dragging:
                x = self.win.winfo_x() + e.x - self._drag_x
                y = self.win.winfo_y() + e.y - self._drag_y
                self.win.geometry(f"+{x}+{y}")

        def stop(e):
            if self._dragging:
                self._dragging = False
                self._save_position()

        for w in self._all_widgets():
            w.bind("<Button-1>", start)
            w.bind("<B1-Motion>", move)
            w.bind("<ButtonRelease-1>", stop)

    # ─────────────────────────────── position ──────────────────────────────────

    def _load_position(self):
        x = self.settings.get("time_x", 100)
        y = self.settings.get("time_y", 200)

        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        x = max(0, min(x, sw - 120))
        y = max(0, min(y, sh - 60))

        self.win.geometry(f"+{x}+{y}")
        self._last_x = x
        self._last_y = y

    def _save_position(self):
        try:
            x = self.win.winfo_x()
            y = self.win.winfo_y()
            if x != self._last_x or y != self._last_y:
                self.settings.set("time_x", x)
                self.settings.set("time_y", y)
                self._last_x = x
                self._last_y = y
        except tk.TclError:
            pass

    # ─────────────────────────────── clock update ──────────────────────────────

    def _get_current_time(self):
        """Get the current time with applied GMT offset."""
        offset_hours = self.settings.get("time_offset", 0.0)
        utc_now = datetime.datetime.utcnow()
        local_now = utc_now + datetime.timedelta(hours=offset_hours)
        return local_now

    def _update_clock(self):
        if self._visible and not self._hidden_fullscreen:
            now = self._get_current_time()
            fmt = self.settings.get("time_fmt", "12h")

            if fmt == "12h":
                time_str = now.strftime("%I:%M:%S %p")
            else:
                time_str = now.strftime("%H:%M:%S")

            date_str = now.strftime("%a %b %d, %Y")

            try:
                self.time_lbl.config(text=time_str)
                self.date_lbl.config(text=date_str)
            except tk.TclError:
                return

        self.win.after(self.TIME_REFRESH_MS, self._update_clock)

    def _keep_on_top(self):
        if self._visible and not self._hidden_fullscreen:
            try:
                self.win.attributes("-topmost", False)
                self.win.attributes("-topmost", True)
                self.win.lift()
            except tk.TclError:
                return
        self.win.after(self.TOPMOST_MS, self._keep_on_top)

    def _start_loops(self):
        self._update_clock()
        self._keep_on_top()

    # ─────────────────────────────── visibility ─────────────────────────────────

    def show(self):
        self._visible = True
        try:
            self.win.deiconify()
        except tk.TclError:
            pass

    def hide(self):
        self._save_position()
        self._visible = False
        try:
            self.win.withdraw()
        except tk.TclError:
            pass

    def set_fullscreen_hidden(self, hidden: bool):
        """Called by the main app's fullscreen detector."""
        self._hidden_fullscreen = hidden
        if hidden:
            try:
                self.win.withdraw()
            except tk.TclError:
                pass
        else:
            if self._visible:
                try:
                    self.win.deiconify()
                except tk.TclError:
                    pass

    def destroy(self):
        try:
            self.win.destroy()
        except tk.TclError:
            pass
