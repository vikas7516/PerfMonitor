# PerfMonitor

A beautiful, transparent system monitor and clock widget for **Windows and Linux**. Displays network speed, CPU, RAM, and GPU stats in a floating overlay, alongside an independent floating clock.

<img src="icon.png" alt="PerfMonitor" width="180" />

## Features

- **Cross-Platform Support**: Works on Windows and Linux.
- **Dynamic UI**: Right-click to enable/disable individual monitor modules (Network, CPU, RAM, GPU). The UI shrinks/grows automatically.
- **Independent Clock Widget**:
  - Drag and place anywhere independently of the monitors.
  - Custom **GMT offsets** (e.g., +5.5, -7).
  - Toggle between **12-hour and 24-hour** formats.
  - Clear date layout with **bold day** + separator (`|`) + date.
- **Smart Hiding**: Both widgets automatically hide when *any* application enters fullscreen mode and reappear when you're done.
- **Native-Style Transparent UI**: Powered by Qt (`PySide6`) with frameless translucent windows.
- **Platform Adapter Architecture**: OS-specific fullscreen logic is split into dedicated backends.
- **Real-time Stats**: High-accuracy monitoring for network, CPU, RAM, and NVIDIA GPU (via NVML with `nvidia-smi` fallback).
- **Persistence**: Remembers window positions and settings between sessions.

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

```

*Note for Linux users: You may need Qt runtime dependencies provided by your distro (for example common XCB/Wayland Qt libraries).*

## Linux Fullscreen + Transparency Notes

- **Fullscreen detection**:
  - **X11**: Uses `xprop`.
  - **Wayland**: Best-effort support for common compositors:
    - Hyprland via `hyprctl`
    - Sway/wlroots via `swaymsg`
    - GNOME Shell via `gdbus`
  - If no compositor-specific tool is available, fullscreen auto-hide may be limited by the desktop environment.

- **Transparency behavior**:
  - UI uses Qt translucent windows (PySide6) for better cross-platform transparency behavior.
  - Final visual behavior still depends on compositor/window manager settings, especially on Linux Wayland.

## Architecture

- Shared app logic remains in core modules (`main.py`, monitors, settings).
- Platform backends are isolated under `platform_backends/`:
  - `platform_backends/fullscreen/` for fullscreen detection per OS/session
- `fullscreen_detector.py` is a stable compatibility wrapper that delegates to the active backend.

## Usage

| Action | What it does |
|--------|--------------|
| **Drag** | Move either widget anywhere on your screen. |
| **Right-click** | Access the context menu (toggles, clock settings, startup, exit). |

## Tech Stack

- **Python** + **PySide6 (Qt)**: Core UI and transparent floating windows.
- **psutil**: High-performance system and network metrics.
- **nvidia-ml-py** + **nvidia-smi fallback**: Reliable NVIDIA GPU utilization and temperature data.

## Requirements

- Windows 10/11, Linux (with X11/Wayland support).
- NVIDIA GPU (optional, for GPU metrics).
- Non-NVIDIA GPUs currently show `N/A` for GPU metrics.
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
- Builds are generated as **single-file binaries** (`--onefile`) so no `_internal` folder is required.
- Pushing a tag like `v1.2.0` automatically publishes release archives for all OS artifacts.
- Output artifact names:
  - `PerfMonitor-windows`
  - `PerfMonitor-linux`

## License

MIT
