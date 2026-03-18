import sys

from qt_app import run_qt_app


if __name__ == "__main__":
    if sys.platform == "darwin":
        print("PerfMonitor currently supports Windows and Linux only.")
        sys.exit(1)

    sys.exit(run_qt_app())
