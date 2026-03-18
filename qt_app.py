import datetime
import sys
from typing import Optional

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


from fullscreen_detector import FullscreenDetector
from settings_manager import SettingsManager
from speed_monitor import SpeedMonitor
from system_monitor import SystemMonitor


class ClockWindow(QWidget):
    """Independent floating clock/date widget."""

    def __init__(self, app_controller: "PerfMonitorQt"):
        super().__init__()
        self.ctrl = app_controller
        self.settings = app_controller.settings
        self._visible = True
        self._hidden_fullscreen = False
        self._drag_offset: Optional[QPoint] = None

        self._last_time = ""
        self._last_day = ""
        self._last_date = ""

        self._init_window()
        self._init_ui()
        self._load_geometry()

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self.update_clock)
        self._clock_timer.start(1000)

        self._top_timer = QTimer(self)
        self._top_timer.timeout.connect(self._raise_top)
        self._top_timer.start(3500)

    def _init_window(self):
        self.setWindowTitle("PerfMonitor-Clock")
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

    def enforce_always_on_top(self):
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        if self._visible and not self._hidden_fullscreen:
            self.show()
            self.raise_()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(0)

        self.time_lbl = QLabel("--:-- --")
        self.time_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.time_lbl)

        date_row = QHBoxLayout()
        date_row.setContentsMargins(0, 0, 0, 0)
        date_row.setSpacing(0)

        self.day_lbl = QLabel("---")
        self.day_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self.sep_lbl = QLabel(" | ")
        self.sep_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        self.date_lbl = QLabel("--- --, ----")
        self.date_lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        date_row.addWidget(self.day_lbl)
        date_row.addWidget(self.sep_lbl)
        date_row.addWidget(self.date_lbl)
        date_row.addStretch(1)
        layout.addLayout(date_row)

        self.setLayout(layout)
        self.apply_user_scale()

    def apply_user_scale(self):
        scale = float(self.settings.get("clock_scale", 1.0))
        scale = min(max(scale, 0.6), 3.0)

        time_size = max(10, int(round(13 * scale)))
        date_size = max(8, int(round(9 * scale)))

        self.time_lbl.setStyleSheet(
            f"color: #FFFFFF; font-size: {time_size}pt; font-weight: 700;"
        )
        self.day_lbl.setStyleSheet(
            f"color: #FFFFFF; font-size: {date_size}pt; font-weight: 700;"
        )
        self.sep_lbl.setStyleSheet(
            f"color: #CCCCCC; font-size: {date_size}pt;"
        )
        self.date_lbl.setStyleSheet(
            f"color: #CCCCCC; font-size: {date_size}pt;"
        )

        self.adjustSize()

    def _load_geometry(self):
        x = int(self.settings.get("time_x", 100))
        y = int(self.settings.get("time_y", 200))

        self.apply_user_scale()

        screen_obj = QGuiApplication.screenAt(QPoint(x, y))
        if screen_obj is None:
            screen_obj = QApplication.primaryScreen()
        screen = screen_obj.availableGeometry()
        x = max(screen.left(), min(x, screen.right() - self.width()))
        y = max(screen.top(), min(y, screen.bottom() - self.height()))
        self.move(x, y)

    def _save_geometry(self):
        geo = self.geometry()
        self.settings.set("time_x", int(geo.x()))
        self.settings.set("time_y", int(geo.y()))

    def _raise_top(self):
        self.enforce_always_on_top()

    def _get_current_time(self) -> datetime.datetime:
        offset_hours = float(self.settings.get("time_offset", 0.0))
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        return utc_now + datetime.timedelta(hours=offset_hours)

    def update_clock(self):
        if not self._visible or self._hidden_fullscreen:
            return

        now = self._get_current_time()
        fmt = self.settings.get("time_fmt", "12h")

        if fmt == "12h":
            time_str = now.strftime("%I:%M:%S %p")
        else:
            time_str = now.strftime("%H:%M:%S")

        day_str = now.strftime("%a")
        date_str = now.strftime("%b %d, %Y")

        if self._last_time != time_str:
            self.time_lbl.setText(time_str)
            self._last_time = time_str
        if self._last_day != day_str:
            self.day_lbl.setText(day_str)
            self._last_day = day_str
        if self._last_date != date_str:
            self.date_lbl.setText(date_str)
            self._last_date = date_str

    def show_widget(self):
        self._visible = True
        if not self._hidden_fullscreen:
            self.show()

    def hide_widget(self):
        self._save_geometry()
        self._visible = False
        self.hide()

    def set_fullscreen_hidden(self, hidden: bool):
        self._hidden_fullscreen = hidden
        if hidden:
            self.hide()
        elif self._visible:
            self.show()

    def contextMenuEvent(self, event):  # type: ignore[override]
        self.ctrl.show_context_menu(event.globalPos())

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            handle = self.windowHandle()
            if handle and handle.startSystemMove():
                event.accept()
                return

            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):  # type: ignore[override]
        if (event.buttons() & Qt.LeftButton) and self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        self._drag_offset = None
        self._save_geometry()
        event.accept()


class MonitorWindow(QWidget):
    """Main floating performance widget."""

    def __init__(self, app_controller: "PerfMonitorQt"):
        super().__init__()
        self.ctrl = app_controller
        self.settings = app_controller.settings
        self._style_targets = []
        self._drag_offset: Optional[QPoint] = None

        self._last_dl = ""
        self._last_ul = ""
        self._last_cpu = ""
        self._last_ram = ""
        self._last_gpu = ""
        self._last_gpu_temp = ""

        self._init_window()
        self._init_ui()
        self._apply_visibility()
        self._load_geometry()

    def _init_window(self):
        self.setWindowTitle("PerfMonitor")
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

    def enforce_always_on_top(self):
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        if self.isVisible():
            self.show()
            self.raise_()

    def _label(self, text: str, color: str, size: int = 11, bold: bool = False) -> QLabel:
        lbl = QLabel(text)
        lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._style_targets.append((lbl, color, size, bold))
        return lbl

    def apply_user_scale(self):
        scale = float(self.settings.get("monitor_scale", 1.0))
        scale = min(max(scale, 0.6), 3.0)

        for lbl, color, base_size, bold in self._style_targets:
            weight = "700" if bold else "400"
            size = max(8, int(round(base_size * scale)))
            lbl.setStyleSheet(
                f"color: {color}; font-size: {size}pt; font-weight: {weight};"
            )

        self.dl_speed.setFixedWidth(max(70, int(round(90 * scale))))
        self.ul_speed.setFixedWidth(max(70, int(round(90 * scale))))
        self.cpu_val.setFixedWidth(max(24, int(round(28 * scale))))
        self.ram_val.setFixedWidth(max(24, int(round(28 * scale))))
        self.gpu_val.setFixedWidth(max(24, int(round(28 * scale))))
        self.gpu_temp.setFixedWidth(max(36, int(round(45 * scale))))

        self.adjustSize()

    def _init_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(2, 2, 2, 2)
        root.setSpacing(0)

        self.row1 = QHBoxLayout()
        self.row1.setContentsMargins(0, 0, 0, 0)
        self.row1.setSpacing(4)

        self.dl_arrow = self._label("▼", "#FF6B6B", size=12, bold=True)
        self.dl_speed = self._label("0 KB/s", "#FFFFFF", size=11)
        self.dl_speed.setFixedWidth(90)

        self.cpu_lbl = self._label("CPU", "#74C0FC", size=11, bold=True)
        self.cpu_val = self._label("0%", "#FFFFFF", size=11)
        self.cpu_val.setFixedWidth(28)

        self.ram_lbl = self._label("RAM", "#B197FC", size=11, bold=True)
        self.ram_val = self._label("0%", "#FFFFFF", size=11)
        self.ram_val.setFixedWidth(28)

        self.row1.addWidget(self.dl_arrow)
        self.row1.addWidget(self.dl_speed)
        self.row1.addWidget(self.cpu_lbl)
        self.row1.addWidget(self.cpu_val)
        self.row1.addWidget(self.ram_lbl)
        self.row1.addWidget(self.ram_val)
        self.row1.addStretch(1)

        self.row2 = QHBoxLayout()
        self.row2.setContentsMargins(0, 0, 0, 0)
        self.row2.setSpacing(4)

        self.ul_arrow = self._label("▲", "#51CF66", size=12, bold=True)
        self.ul_speed = self._label("0 KB/s", "#FFFFFF", size=11)
        self.ul_speed.setFixedWidth(90)

        self.gpu_lbl = self._label("GPU", "#FFA94D", size=11, bold=True)
        self.gpu_val = self._label("0%", "#FFFFFF", size=11)
        self.gpu_val.setFixedWidth(28)

        self.gpu_temp = self._label("", "#FF8888", size=11)
        self.gpu_temp.setFixedWidth(45)

        self.row2.addWidget(self.ul_arrow)
        self.row2.addWidget(self.ul_speed)
        self.row2.addWidget(self.gpu_lbl)
        self.row2.addWidget(self.gpu_val)
        self.row2.addWidget(self.gpu_temp)
        self.row2.addStretch(1)

        root.addLayout(self.row1)
        root.addLayout(self.row2)
        self.setLayout(root)
        self.apply_user_scale()

    def _set_text(self, label: QLabel, new_text: str, cache_attr: str):
        if getattr(self, cache_attr) != new_text:
            label.setText(new_text)
            setattr(self, cache_attr, new_text)

    def _apply_visibility(self):
        show_net = bool(self.settings.get("show_network", True))
        show_cpu = bool(self.settings.get("show_cpu", True))
        show_ram = bool(self.settings.get("show_ram", True))
        show_gpu = bool(self.settings.get("show_gpu", True))

        self.dl_arrow.setVisible(show_net)
        self.dl_speed.setVisible(show_net)
        self.ul_arrow.setVisible(show_net)
        self.ul_speed.setVisible(show_net)

        self.cpu_lbl.setVisible(show_cpu)
        self.cpu_val.setVisible(show_cpu)
        self.ram_lbl.setVisible(show_ram)
        self.ram_val.setVisible(show_ram)

        self.gpu_lbl.setVisible(show_gpu)
        self.gpu_val.setVisible(show_gpu)
        self.gpu_temp.setVisible(show_gpu)

    def _load_geometry(self):
        x = int(self.settings.get("window_x", 100))
        y = int(self.settings.get("window_y", 100))

        self.apply_user_scale()

        screen_obj = QGuiApplication.screenAt(QPoint(x, y))
        if screen_obj is None:
            screen_obj = QApplication.primaryScreen()
        screen = screen_obj.availableGeometry()
        x = max(screen.left(), min(x, screen.right() - self.width()))
        y = max(screen.top(), min(y, screen.bottom() - self.height()))
        self.move(x, y)

    def _save_geometry(self):
        geo = self.geometry()
        self.settings.set("window_x", int(geo.x()))
        self.settings.set("window_y", int(geo.y()))

    def _toggle_monitor(self, key: str, checked: bool):
        self.settings.set(key, checked)
        self._apply_visibility()

    def _toggle_clock(self, checked: bool):
        self.settings.set("show_time", checked)
        if checked:
            self.ctrl.clock.show_widget()
        else:
            self.ctrl.clock.hide_widget()

    def contextMenuEvent(self, event):  # type: ignore[override]
        self.ctrl.show_context_menu(event.globalPos())

    def _reset_pos(self):
        screen_obj = QGuiApplication.screenAt(QPoint(self.x(), self.y()))
        if screen_obj is None:
            screen_obj = QApplication.primaryScreen()
        screen = screen_obj.availableGeometry()
        self.move(screen.left() + 50, screen.top() + 50)
        self.ctrl.clock.move(screen.left() + 50, screen.top() + 150)
        self._save_geometry()
        self.ctrl.clock._save_geometry()

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            handle = self.windowHandle()
            if handle and handle.startSystemMove():
                event.accept()
                return

            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):  # type: ignore[override]
        if (event.buttons() & Qt.LeftButton) and self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        self._drag_offset = None
        self._save_geometry()
        event.accept()


class SettingsWindow(QWidget):
    """Dedicated settings UI to avoid overloading right-click menus."""

    def __init__(self, app_controller: "PerfMonitorQt"):
        super().__init__()
        self.ctrl = app_controller
        self.settings = app_controller.settings

        self.setWindowTitle("PerfMonitor Settings")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)

        root = QVBoxLayout()
        form = QFormLayout()

        self.startup_cb = QCheckBox("Start with OS")
        self.startup_cb.setChecked(SettingsManager.is_in_startup())
        self.startup_cb.toggled.connect(self._on_startup_toggled)
        form.addRow(self.startup_cb)

        self.show_net_cb = QCheckBox("Show Network")
        self.show_net_cb.setChecked(bool(self.settings.get("show_network", True)))
        self.show_net_cb.toggled.connect(lambda c: self._on_toggle("show_network", c))
        form.addRow(self.show_net_cb)

        self.show_cpu_cb = QCheckBox("Show CPU")
        self.show_cpu_cb.setChecked(bool(self.settings.get("show_cpu", True)))
        self.show_cpu_cb.toggled.connect(lambda c: self._on_toggle("show_cpu", c))
        form.addRow(self.show_cpu_cb)

        self.show_ram_cb = QCheckBox("Show RAM")
        self.show_ram_cb.setChecked(bool(self.settings.get("show_ram", True)))
        self.show_ram_cb.toggled.connect(lambda c: self._on_toggle("show_ram", c))
        form.addRow(self.show_ram_cb)

        self.show_gpu_cb = QCheckBox("Show GPU")
        self.show_gpu_cb.setChecked(bool(self.settings.get("show_gpu", True)))
        self.show_gpu_cb.toggled.connect(lambda c: self._on_toggle("show_gpu", c))
        form.addRow(self.show_gpu_cb)

        self.show_clock_cb = QCheckBox("Show Clock")
        self.show_clock_cb.setChecked(bool(self.settings.get("show_time", True)))
        self.show_clock_cb.toggled.connect(lambda c: self._on_toggle("show_time", c))
        form.addRow(self.show_clock_cb)

        self.time_fmt_combo = QComboBox()
        self.time_fmt_combo.addItem("12-hour", "12h")
        self.time_fmt_combo.addItem("24-hour", "24h")
        current_fmt = self.settings.get("time_fmt", "12h")
        idx = 0 if current_fmt == "12h" else 1
        self.time_fmt_combo.setCurrentIndex(idx)
        self.time_fmt_combo.currentIndexChanged.connect(self._on_time_fmt_changed)
        form.addRow("Time Format", self.time_fmt_combo)

        self.timezone_spin = QDoubleSpinBox()
        self.timezone_spin.setRange(-14.0, 14.0)
        self.timezone_spin.setDecimals(2)
        self.timezone_spin.setSingleStep(0.25)
        self.timezone_spin.setValue(float(self.settings.get("time_offset", 0.0)))
        self.timezone_spin.valueChanged.connect(self._on_timezone_changed)
        form.addRow("GMT Offset", self.timezone_spin)

        self.monitor_scale_spin = QDoubleSpinBox()
        self.monitor_scale_spin.setRange(0.6, 3.0)
        self.monitor_scale_spin.setDecimals(2)
        self.monitor_scale_spin.setSingleStep(0.05)
        self.monitor_scale_spin.setValue(float(self.settings.get("monitor_scale", 1.0)))
        self.monitor_scale_spin.valueChanged.connect(self._on_monitor_scale_changed)
        form.addRow("Monitor Scale", self.monitor_scale_spin)

        self.clock_scale_spin = QDoubleSpinBox()
        self.clock_scale_spin.setRange(0.6, 3.0)
        self.clock_scale_spin.setDecimals(2)
        self.clock_scale_spin.setSingleStep(0.05)
        self.clock_scale_spin.setValue(float(self.settings.get("clock_scale", 1.0)))
        self.clock_scale_spin.valueChanged.connect(self._on_clock_scale_changed)
        form.addRow("Clock Scale", self.clock_scale_spin)

        root.addLayout(form)

        btn_row = QHBoxLayout()
        reset_btn = QPushButton("Reset Positions")
        reset_btn.clicked.connect(self.ctrl.main_window._reset_pos)
        btn_row.addWidget(reset_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.hide)
        btn_row.addWidget(close_btn)
        btn_row.addStretch(1)

        root.addLayout(btn_row)
        self.setLayout(root)

    def _on_startup_toggled(self, checked: bool):
        if checked:
            ok = SettingsManager.add_to_startup()
        else:
            ok = SettingsManager.remove_from_startup()
        if not ok:
            self.startup_cb.blockSignals(True)
            self.startup_cb.setChecked(not checked)
            self.startup_cb.blockSignals(False)

    def _on_toggle(self, key: str, checked: bool):
        self.settings.set(key, checked)
        self.ctrl.main_window._apply_visibility()
        if key == "show_time":
            if checked:
                self.ctrl.clock.show_widget()
            else:
                self.ctrl.clock.hide_widget()

    def _on_time_fmt_changed(self, _index: int):
        self.settings.set("time_fmt", self.time_fmt_combo.currentData())
        self.ctrl.clock.update_clock()

    def _on_timezone_changed(self, value: float):
        self.settings.set("time_offset", float(value))
        self.ctrl.clock.update_clock()

    def _on_monitor_scale_changed(self, value: float):
        self.settings.set("monitor_scale", float(value))
        self.ctrl.main_window.apply_user_scale()
        self.ctrl.main_window._save_geometry()

    def _on_clock_scale_changed(self, value: float):
        self.settings.set("clock_scale", float(value))
        self.ctrl.clock.apply_user_scale()
        self.ctrl.clock._save_geometry()


class PerfMonitorQt:
    """Qt implementation of PerfMonitor with true translucent windows."""

    def __init__(self):
        self.settings = SettingsManager()
        self.speed = SpeedMonitor()
        self.system = SystemMonitor()
        self.fullscreen = FullscreenDetector()

        self._hidden_fullscreen = False

        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.main_window = MonitorWindow(self)
        self.clock = ClockWindow(self)
        self.settings_window = SettingsWindow(self)

        self.main_window.show()
        if self.settings.get("show_time", True):
            self.clock.show_widget()
        else:
            self.clock.hide_widget()

        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self.update_stats)
        self._update_timer.start(700)

        self._fs_timer = QTimer()
        self._fs_timer.timeout.connect(self.check_fullscreen)
        self._fs_timer.start(1000)

        self._top_timer = QTimer()
        self._top_timer.timeout.connect(self.raise_windows)
        self._top_timer.start(3500)

    def raise_windows(self):
        if not self._hidden_fullscreen:
            self.main_window.enforce_always_on_top()
            self.clock.enforce_always_on_top()

    def show_context_menu(self, global_pos):
        menu = QMenu()
        settings_action = QAction("Settings", menu)
        settings_action.triggered.connect(self.open_settings)
        menu.addAction(settings_action)

        menu.addSeparator()
        exit_action = QAction("Quit", menu)
        exit_action.triggered.connect(self.exit_app)
        menu.addAction(exit_action)
        menu.exec(global_pos)

    def open_settings(self):
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def update_stats(self):
        if self._hidden_fullscreen:
            return

        show_net = bool(self.settings.get("show_network", True))
        show_cpu = bool(self.settings.get("show_cpu", True))
        show_ram = bool(self.settings.get("show_ram", True))
        show_gpu = bool(self.settings.get("show_gpu", True))

        if show_net:
            s = self.speed.get_speed()
            self.main_window._set_text(
                self.main_window.dl_speed,
                f"{s.download_display} {s.download_unit}",
                "_last_dl",
            )
            self.main_window._set_text(
                self.main_window.ul_speed,
                f"{s.upload_display} {s.upload_unit}",
                "_last_ul",
            )

        if not (show_cpu or show_ram or show_gpu):
            return

        st = self.system.get_stats()

        if show_cpu:
            self.main_window._set_text(self.main_window.cpu_val, st.cpu_display, "_last_cpu")

        if show_ram:
            self.main_window._set_text(self.main_window.ram_val, st.ram_display, "_last_ram")

        if show_gpu:
            self.main_window._set_text(self.main_window.gpu_val, st.gpu_display, "_last_gpu")
            self.main_window._set_text(
                self.main_window.gpu_temp,
                st.gpu_temp_display if st.gpu_temp is not None else "",
                "_last_gpu_temp",
            )

    def check_fullscreen(self):
        fs = self.fullscreen.should_hide()

        if fs and not self._hidden_fullscreen:
            self._hidden_fullscreen = True
            self.main_window.hide()
            self.clock.set_fullscreen_hidden(True)
        elif not fs and self._hidden_fullscreen:
            self._hidden_fullscreen = False
            self.main_window.show()
            self.clock.set_fullscreen_hidden(False)

    def exit_app(self):
        self._update_timer.stop()
        self._fs_timer.stop()
        self._top_timer.stop()
        self.main_window._save_geometry()
        self.clock._save_geometry()
        self.settings_window.hide()

        self.fullscreen.stop()
        self.system.close()
        self.app.quit()

    def run(self) -> int:
        return self.app.exec()


def run_qt_app() -> int:
    app = PerfMonitorQt()
    return app.run()
