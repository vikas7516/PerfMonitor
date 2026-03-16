# PerfMonitor

A beautiful, transparent system monitor and clock widget for **Windows, Linux, and macOS**. Displays network speed, CPU, RAM, and GPU stats in a floating overlay, alongside an independent floating clock.

![PerfMonitor Screenshot](icon.png)

## Features

- **Cross-Platform Support**: Works seamlessly on Windows, Linux, and macOS.
- **Dynamic UI**: Right-click to enable/disable individual monitor modules (Network, CPU, RAM, GPU). The UI shrinks/grows automatically.
- **Independent Clock Widget**:
  - Drag and place anywhere independently of the monitors.
  - Custom **GMT offsets** (e.g., +5.5, -7).
  - Toggle between **12-hour and 24-hour** formats.
  - Clear date layout with **bold day** + separator (`|`) + date.
- **Smart Hiding**: Both widgets automatically hide when *any* application enters fullscreen mode and reappear when you're done.
- **Platform Adapter Architecture**: OS-specific fullscreen/transparency logic is split into dedicated backends.
- **Real-time Stats**: High-accuracy monitoring for network, CPU, RAM, and NVIDIA GPU (via `nvidia-smi`).
- **Persistence**: Remembers window positions and settings between sessions.
- **System Tray**: Comprehensive tray menu for visibility and startup controls.

## Download

**[Download Latest Release](../../releases/latest)** - Optimized executables for your OS are generated automatically via GitHub Actions.

Or run from source:

```bash
git clone https://github.com/vikas7516/PerfMonitor.git
cd PerfMonitor
pip install -r requirements/base.txt
python main.py
```

Install platform extras when needed:

```bash
# Windows
pip install -r requirements/windows.txt

# Linux
pip install -r requirements/linux.txt

# macOS
pip install -r requirements/macos.txt
```

*Note for Linux users: You may need to install `python3-tk` via your package manager (e.g., `sudo apt-get install python3-tk`).*

## Linux Fullscreen + Transparency Notes

- **Fullscreen detection**:
  - **X11**: Uses `xprop`.
  - **Wayland**: Best-effort support for common compositors:
    - Hyprland via `hyprctl`
    - Sway/wlroots via `swaymsg`
    - GNOME Shell via `gdbus`
  - If no compositor-specific tool is available, fullscreen auto-hide may be limited by the desktop environment.

- **Transparency behavior**:
  - Windows/macOS support stronger native transparency controls in Tk.
  - On Linux, Tk transparency depends on compositor + backend support.
  - PerfMonitor attempts transparent-color mode first, then falls back to semi-transparent dark background when unsupported.
  - Fully forcing "no background at all" is not guaranteed on all Linux environments with Tkinter.

## Architecture

- Shared app logic remains in core modules (`main.py`, monitors, settings).
- Platform backends are isolated under `platform_backends/`:
  - `platform_backends/fullscreen/` for fullscreen detection per OS/session
  - `platform_backends/transparency.py` for window transparency behavior
- `fullscreen_detector.py` is a stable compatibility wrapper that delegates to the active backend.

## Usage

| Action | What it does |
|--------|--------------|
| **Drag** | Move either widget anywhere on your screen. |
| **Right-click** | Access the focus menu (Toggle monitors, Clock settings, Startup, Hide, Exit). |
| **Tray Icon** | Quick toggle visibility or manage OS startup. |

## Tech Stack

- **Python** + **Tkinter**: Core UI and cross-platform windows.
- **psutil**: High-performance system and network metrics.
- **pystray** + **Pillow**: System tray integration and icon rendering.
- **nvidia-smi**: Reliable GPU utilization and temperature data.

## Requirements

- Windows 10/11, Linux (with X11/Wayland support), or macOS.
- NVIDIA GPU (optional, for GPU metrics).
- Python 3.9+ (if running from source).
- Linux tools for best fullscreen support (optional but recommended):
  - `xprop` (X11)
  - `hyprctl` (Hyprland Wayland)
  - `swaymsg` (Sway Wayland)
  - `gdbus` (GNOME Wayland)

## CI/CD Builds

- GitHub Actions builds **separate artifacts per OS** using matrix jobs.
- Each OS installs only its own dependency file:
  - `requirements/windows.txt`
  - `requirements/linux.txt`
  - `requirements/macos.txt`
- Pushing a tag like `v1.2.0` automatically publishes release archives for all OS artifacts.
- Output artifact names:
  - `PerfMonitor-windows`
  - `PerfMonitor-linux`
  - `PerfMonitor-macos`

## License

MIT
