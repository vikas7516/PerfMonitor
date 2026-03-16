import sys
import tkinter as tk


FALLBACK_BG = "#222222"


def apply_tk_transparency(win: tk.Misc, transparent_color: str) -> str:
    """Apply best available transparency mode and return effective background color."""
    if sys.platform == "win32":
        win.configure(bg=transparent_color)
        win.attributes("-transparentcolor", transparent_color)
        win.attributes("-topmost", True)
        return transparent_color

    if sys.platform == "darwin":
        win.configure(bg=transparent_color)
        win.attributes("-transparent", True)
        win.attributes("-topmost", True)
        return transparent_color

    # Linux / other Unix desktops
    try:
        win.configure(bg=transparent_color)
        win.attributes("-transparentcolor", transparent_color)
        win.attributes("-topmost", True)
        return transparent_color
    except tk.TclError:
        win.configure(bg=FALLBACK_BG)
        try:
            win.attributes("-type", "dock")
        except tk.TclError:
            pass
        try:
            win.wait_visibility(win)
            win.attributes("-alpha", 0.8)
        except tk.TclError:
            pass
        win.attributes("-topmost", True)
        return FALLBACK_BG
