# PerfMonitor

A minimal, transparent system monitor widget for Windows. Displays network speed, CPU, RAM, and GPU stats in a floating overlay.

![Widget Preview](icon.png)

## Features

- Real-time network upload/download speeds
- CPU and RAM usage
- NVIDIA GPU usage and temperature
- Transparent floating overlay
- Always on top (hides during fullscreen video)
- Remembers position between sessions
- System tray with quick controls

## Download

**[Download Latest Release](../../releases/latest)** - Portable `.exe`, no installation required.

Or run from source:

```bash
git clone https://github.com/vikas7516/PerfMonitor.git
cd PerfMonitor
pip install -r requirements.txt
python main.py
```

## Usage

| Action | What it does |
|--------|--------------|
| Drag | Move the widget anywhere |
| Right-click | Context menu (startup toggle, hide, exit) |
| Tray icon | Double-click to show/hide |

## Build from Source

```bash
pip install pyinstaller
pyinstaller --onefile --noconsole --icon=icon.png --add-data "icon.png;." --name PerfMonitor main.py
```

## Tech Stack

- **Python** + **Tkinter** for the overlay
- **psutil** for system metrics
- **pystray** + **Pillow** for system tray
- **nvidia-smi** for GPU stats

## Requirements

- Windows 10/11
- NVIDIA GPU (optional, for GPU stats)

## License

MIT
