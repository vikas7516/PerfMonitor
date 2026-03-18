import datetime
import sys
from typing import Optional

from PySide6.QtCore import QPoint, QTimer, Qt
from PySide6.QtGui import QAction, QActionGroup, QCursor, QGuiApplication
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
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
        self._is_resizing = False
        self._resize_edge = 0  # 1: right, 2: bottom, 3: bottom-right

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
        self._apply_scaled_styles()

    def _apply_scaled_styles(self):
        h_scale = min(max(self.height() / 50.0, 0.75), 2.0)
        w_scale = min(max(self.width() / 150.0, 0.75), 2.0)
        scale = min(h_scale, w_scale)

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

    def _load_geometry(self):
        x = int(self.settings.get("time_x", 100))
        y = int(self.settings.get("time_y", 200))
        w = int(self.settings.get("time_w", 150))
        h = int(self.settings.get("time_h", 50))
        screen_obj = QGuiApplication.screenAt(QPoint(x, y))
        if screen_obj is None:
            screen_obj = QApplication.primaryScreen()
        screen = screen_obj.availableGeometry()
        x = max(screen.left(), min(x, screen.right() - 50))
        y = max(screen.top(), min(y, screen.bottom() - 30))
        self.setGeometry(x, y, w, h)

    def _save_geometry(self):
        geo = self.geometry()
        self.settings.set("time_x", int(geo.x()))
        self.settings.set("time_y", int(geo.y()))
        self.settings.set("time_w", int(geo.width()))
        self.settings.set("time_h", int(geo.height()))

    def _raise_top(self):
        if self._visible and not self._hidden_fullscreen:
            self.raise_()

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
            pos = event.position().toPoint()
            rect = self.rect()
            margin = 8
            if pos.x() > rect.width() - margin and pos.y() > rect.height() - margin:
                self._is_resizing = True
                self._resize_edge = 3
            elif pos.x() > rect.width() - margin:
                self._is_resizing = True
                self._resize_edge = 1
            elif pos.y() > rect.height() - margin:
                self._is_resizing = True
                self._resize_edge = 2
            else:
                self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):  # type: ignore[override]
        pos = event.position().toPoint()
        rect = self.rect()
        margin = 8

        if not (event.buttons() & Qt.LeftButton):
            if pos.x() > rect.width() - margin and pos.y() > rect.height() - margin:
                self.setCursor(Qt.SizeFDiagCursor)
            elif pos.x() > rect.width() - margin:
                self.setCursor(Qt.SizeHorCursor)
            elif pos.y() > rect.height() - margin:
                self.setCursor(Qt.SizeVerCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            return

        if self._is_resizing:
            new_w = self.width()
            new_h = self.height()
            if self._resize_edge in (1, 3):
                new_w = pos.x()
            if self._resize_edge in (2, 3):
                new_h = pos.y()
            self.resize(max(100, new_w), max(40, new_h))
            event.accept()
        elif self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        self._drag_offset = None
        self._is_resizing = False
        self._resize_edge = 0
        self._save_geometry()
        self.setCursor(Qt.ArrowCursor)
        event.accept()

    def resizeEvent(self, event):  # type: ignore[override]
        super().resizeEvent(event)
        self._apply_scaled_styles()


class MonitorWindow(QWidget):
    """Main floating performance widget."""

    def __init__(self, app_controller: "PerfMonitorQt"):
        super().__init__()
        self.ctrl = app_controller
        self.settings = app_controller.settings
        self._style_targets = []
        self._drag_offset: Optional[QPoint] = None
        self._is_resizing = False
        self._resize_edge = 0

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

    def _label(self, text: str, color: str, size: int = 11, bold: bool = False) -> QLabel:
        lbl = QLabel(text)
        lbl.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._style_targets.append((lbl, color, size, bold))
        return lbl

    def _apply_scaled_styles(self):
        h_scale = min(max(self.height() / 60.0, 0.75), 2.2)
        w_scale = min(max(self.width() / 250.0, 0.75), 2.2)
        scale = min(h_scale, w_scale)

        for lbl, color, base_size, bold in self._style_targets:
            weight = "700" if bold else "400"
            size = max(8, int(round(base_size * scale)))
            lbl.setStyleSheet(
                f"color: {color}; font-size: {size}pt; font-weight: {weight};"
            )

        width_scale = max(0.75, w_scale)
        self.dl_speed.setFixedWidth(max(70, int(round(90 * width_scale))))
        self.ul_speed.setFixedWidth(max(70, int(round(90 * width_scale))))
        self.cpu_val.setFixedWidth(max(24, int(round(28 * width_scale))))
        self.ram_val.setFixedWidth(max(24, int(round(28 * width_scale))))
        self.gpu_val.setFixedWidth(max(24, int(round(28 * width_scale))))
        self.gpu_temp.setFixedWidth(max(36, int(round(45 * width_scale))))

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
        self._apply_scaled_styles()

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
        w = int(self.settings.get("window_w", 250))
        h = int(self.settings.get("window_h", 60))
        screen_obj = QGuiApplication.screenAt(QPoint(x, y))
        if screen_obj is None:
            screen_obj = QApplication.primaryScreen()
        screen = screen_obj.availableGeometry()
        x = max(screen.left(), min(x, screen.right() - 50))
        y = max(screen.top(), min(y, screen.bottom() - 30))
        self.setGeometry(x, y, w, h)

    def _save_geometry(self):
        geo = self.geometry()
        self.settings.set("window_x", int(geo.x()))
        self.settings.set("window_y", int(geo.y()))
        self.settings.set("window_w", int(geo.width()))
        self.settings.set("window_h", int(geo.height()))

    def _toggle_monitor(self, key: str, checked: bool):
        self.settings.set(key, checked)
        self._apply_visibility()

    def _toggle_clock(self, checked: bool):
        self.settings.set("show_time", checked)
        if checked:
            self.ctrl.clock.show_widget()
        else:
            self.ctrl.clock.hide_widget()

    def _set_startup(self, checked: bool):
        if checked:
            SettingsManager.add_to_startup()
        else:
            SettingsManager.remove_from_startup()

    def _set_time_fmt(self, fmt: str):
        self.settings.set("time_fmt", fmt)

    def _set_timezone(self):
        current_offset = float(self.settings.get("time_offset", 0.0))
        val, ok = QInputDialog.getDouble(
            self,
            "Set Timezone",
            "GMT Offset (e.g. +5.5 or -7):",
            current_offset,
            -14.0,
            14.0,
            2,
        )
        if ok:
            self.settings.set("time_offset", float(val))

    def show_context_menu(self, global_pos):
        menu = QMenu(self)

        startup_action = QAction("Start with OS", self, checkable=True)
        startup_action.setChecked(SettingsManager.is_in_startup())
        startup_action.triggered.connect(self._set_startup)
        menu.addAction(startup_action)
        menu.addSeparator()

        monitors_menu = menu.addMenu("Monitors")

        show_net = QAction("Network Speed", self, checkable=True)
        show_net.setChecked(bool(self.settings.get("show_network", True)))
        show_net.triggered.connect(lambda checked: self._toggle_monitor("show_network", checked))
        monitors_menu.addAction(show_net)

        show_cpu = QAction("CPU", self, checkable=True)
        show_cpu.setChecked(bool(self.settings.get("show_cpu", True)))
        show_cpu.triggered.connect(lambda checked: self._toggle_monitor("show_cpu", checked))
        monitors_menu.addAction(show_cpu)

        show_ram = QAction("RAM", self, checkable=True)
        show_ram.setChecked(bool(self.settings.get("show_ram", True)))
        show_ram.triggered.connect(lambda checked: self._toggle_monitor("show_ram", checked))
        monitors_menu.addAction(show_ram)

        show_gpu = QAction("GPU + Temp", self, checkable=True)
        show_gpu.setChecked(bool(self.settings.get("show_gpu", True)))
        show_gpu.triggered.connect(lambda checked: self._toggle_monitor("show_gpu", checked))
        monitors_menu.addAction(show_gpu)

        monitors_menu.addSeparator()

        show_clock = QAction("Clock Widget", self, checkable=True)
        show_clock.setChecked(bool(self.settings.get("show_time", True)))
        show_clock.triggered.connect(self._toggle_clock)
        monitors_menu.addAction(show_clock)

        clock_menu = menu.addMenu("Clock Settings")
        fmt_12 = QAction("12-hour format", self, checkable=True)
        fmt_24 = QAction("24-hour format", self, checkable=True)
        fmt_group = QActionGroup(self)
        fmt_group.setExclusive(True)
        fmt_group.addAction(fmt_12)
        fmt_group.addAction(fmt_24)
        fmt_12.setChecked(self.settings.get("time_fmt", "12h") == "12h")
        fmt_24.setChecked(self.settings.get("time_fmt", "12h") == "24h")
        fmt_12.triggered.connect(lambda checked: checked and self._set_time_fmt("12h"))
        fmt_24.triggered.connect(lambda checked: checked and self._set_time_fmt("24h"))
        clock_menu.addAction(fmt_12)
        clock_menu.addAction(fmt_24)
        clock_menu.addSeparator()

        tz_action = QAction("Set Timezone (GMT offset)...", self)
        tz_action.triggered.connect(self._set_timezone)
        clock_menu.addAction(tz_action)

        menu.addSeparator()
        reset_action = QAction("Reset Location", self)
        reset_action.triggered.connect(self._reset_pos)
        menu.addAction(reset_action)

        menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.ctrl.exit_app)
        menu.addAction(exit_action)

        menu.exec(global_pos)

    def contextMenuEvent(self, event):  # type: ignore[override]
        self.show_context_menu(event.globalPos())

    def _reset_pos(self):
        screen_obj = QGuiApplication.screenAt(QCursor.pos())
        if screen_obj is None:
            screen_obj = QApplication.primaryScreen()
        screen = screen_obj.availableGeometry()
        self.move(screen.left() + 50, screen.top() + 50)
        self.ctrl.clock.move(screen.left() + 50, screen.top() + 150)
        self._save_geometry()
        self.ctrl.clock._save_geometry()

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            rect = self.rect()
            margin = 8
            if pos.x() > rect.width() - margin and pos.y() > rect.height() - margin:
                self._is_resizing = True
                self._resize_edge = 3
            elif pos.x() > rect.width() - margin:
                self._is_resizing = True
                self._resize_edge = 1
            elif pos.y() > rect.height() - margin:
                self._is_resizing = True
                self._resize_edge = 2
            else:
                self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):  # type: ignore[override]
        pos = event.position().toPoint()
        rect = self.rect()
        margin = 8

        if not (event.buttons() & Qt.LeftButton):
            if pos.x() > rect.width() - margin and pos.y() > rect.height() - margin:
                self.setCursor(Qt.SizeFDiagCursor)
            elif pos.x() > rect.width() - margin:
                self.setCursor(Qt.SizeHorCursor)
            elif pos.y() > rect.height() - margin:
                self.setCursor(Qt.SizeVerCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            return

        if self._is_resizing:
            new_w = self.width()
            new_h = self.height()
            if self._resize_edge in (1, 3):
                new_w = pos.x()
            if self._resize_edge in (2, 3):
                new_h = pos.y()
            self.resize(max(200, new_w), max(40, new_h))
            event.accept()
        elif self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        self._drag_offset = None
        self._is_resizing = False
        self._resize_edge = 0
        self._save_geometry()
        self.setCursor(Qt.ArrowCursor)
        event.accept()

    def resizeEvent(self, event):  # type: ignore[override]
        super().resizeEvent(event)
        self._apply_scaled_styles()


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
        if self.main_window.isVisible() and not self._hidden_fullscreen:
            self.main_window.raise_()
        if self.clock.isVisible() and not self._hidden_fullscreen:
            self.clock.raise_()

    def show_context_menu(self, global_pos):
        self.main_window.show_context_menu(global_pos)

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

        self.fullscreen.stop()
        self.system.close()
        self.app.quit()

    def run(self) -> int:
        return self.app.exec()


def run_qt_app() -> int:
    app = PerfMonitorQt()
    return app.run()
