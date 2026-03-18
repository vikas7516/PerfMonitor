import json
import os
import shutil
import subprocess


class LinuxFullscreenBackend:
    """Best-effort fullscreen detection for X11 and common Wayland compositors."""

    def __init__(self):
        session = os.environ.get("XDG_SESSION_TYPE", "").strip().lower()
        self._is_wayland = session == "wayland"
        self._is_x11 = session in {"x11", "xorg"}

        self._has_xprop = shutil.which("xprop") is not None
        self._has_hyprctl = shutil.which("hyprctl") is not None
        self._has_swaymsg = shutil.which("swaymsg") is not None
        self._has_gdbus = shutil.which("gdbus") is not None

        self._detector = self._select_detector()

    def _select_detector(self):
        if self._is_wayland:
            if self._has_hyprctl:
                return self._wayland_hyprland_should_hide
            if self._has_swaymsg:
                return self._wayland_sway_should_hide
            if self._has_gdbus:
                return self._wayland_gnome_should_hide
            if self._has_xprop:
                return self._x11_should_hide
            return self._always_false

        if self._is_x11:
            return self._x11_should_hide if self._has_xprop else self._always_false

        if self._has_hyprctl:
            return self._wayland_hyprland_should_hide
        if self._has_swaymsg:
            return self._wayland_sway_should_hide
        if self._has_gdbus:
            return self._wayland_gnome_should_hide
        if self._has_xprop:
            return self._x11_should_hide
        return self._always_false

    def _always_false(self) -> bool:
        return False

    def _run_cmd(self, args: list[str]) -> str:
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=1.2)
            if result.returncode == 0:
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
        return ""

    def _x11_should_hide(self) -> bool:
        if not self._has_xprop:
            return False

        active_line = self._run_cmd(["xprop", "-root", "_NET_ACTIVE_WINDOW"])
        if not active_line or "#" not in active_line:
            return False

        win_id = active_line.split("#", 1)[1].strip()
        if not win_id or win_id == "0x0":
            return False

        state = self._run_cmd(["xprop", "-id", win_id, "_NET_WM_STATE"])
        return "_NET_WM_STATE_FULLSCREEN" in state

    def _wayland_hyprland_should_hide(self) -> bool:
        if not self._has_hyprctl:
            return False

        raw = self._run_cmd(["hyprctl", "activewindow", "-j"])
        if not raw:
            return False

        try:
            data = json.loads(raw)
            return bool(data.get("fullscreen", 0))
        except (ValueError, TypeError, AttributeError):
            return False

    def _wayland_sway_should_hide(self) -> bool:
        if not self._has_swaymsg:
            return False

        raw = self._run_cmd(["swaymsg", "-t", "get_tree", "-r"])
        if not raw:
            return False

        try:
            tree = json.loads(raw)
        except ValueError:
            return False

        def find_focused(node):
            if not isinstance(node, dict):
                return None
            if node.get("focused"):
                return node
            for key in ("nodes", "floating_nodes"):
                for child in node.get(key, []):
                    focused = find_focused(child)
                    if focused:
                        return focused
            return None

        focused = find_focused(tree)
        if not focused:
            return False

        return int(focused.get("fullscreen_mode", 0)) == 1

    def _wayland_gnome_should_hide(self) -> bool:
        if not self._has_gdbus:
            return False

        expr = (
            "let w = global.display.get_focus_window();"
            " w ? w.is_fullscreen() : false"
        )
        out = self._run_cmd(
            [
                "gdbus",
                "call",
                "--session",
                "--dest",
                "org.gnome.Shell",
                "--object-path",
                "/org/gnome/Shell",
                "--method",
                "org.gnome.Shell.Eval",
                expr,
            ]
        )
        if not out:
            return False

        return "'true'" in out.lower()

    def should_hide(self) -> bool:
        return self._detector()
