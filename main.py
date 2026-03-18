import os
import shutil
import sys

from settings_manager import SettingsManager


def _is_wayland_session() -> bool:
    return os.environ.get("XDG_SESSION_TYPE", "").strip().lower() == "wayland"


def _maybe_reexec_with_xcb() -> None:
    if sys.platform != "linux" or not _is_wayland_session():
        return

    if os.environ.get("PERFMONITOR_DISABLE_XCB_FALLBACK") == "1":
        return

    if os.environ.get("PERFMONITOR_XCB_REEXEC") == "1":
        return

    # If a platform is explicitly chosen, respect it.
    if os.environ.get("QT_QPA_PLATFORM"):
        return

    # XWayland mode needs an X display available.
    if not os.environ.get("DISPLAY"):
        return

    # Heuristic gate to avoid forcing xcb where XWayland is absent.
    if shutil.which("Xwayland") is None and shutil.which("Xorg") is None:
        return

    settings = SettingsManager()
    prefer_xwayland = bool(settings.get("prefer_xwayland", True))
    if not prefer_xwayland:
        return

    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "xcb"
    env["PERFMONITOR_XCB_REEXEC"] = "1"
    os.execvpe(sys.executable, [sys.executable, *sys.argv], env)


if __name__ == "__main__":
    if sys.platform == "darwin":
        print("PerfMonitor currently supports Windows and Linux only.")
        sys.exit(1)

    _maybe_reexec_with_xcb()

    from qt_app import run_qt_app

    sys.exit(run_qt_app())
