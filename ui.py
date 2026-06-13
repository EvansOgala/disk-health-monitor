from __future__ import annotations

import sys
import threading
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from disk_ops import launch_in_terminal, read_all_disk_health
from qt_style import THEMES, apply_qt_theme
from settings import load_settings, save_settings


class DiskHealthWindow(QMainWindow):
    health_ready = Signal(object, bool)

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.setWindowTitle("Disk Health Monitor")
        self.resize(1260, 860)
        self.setMinimumSize(1040, 680)

        self.settings = load_settings()
        self.theme_name = self.settings.get("theme", "dark")
        if self.theme_name not in THEMES:
            self.theme_name = "dark"

        self.rows = []
        self.row_data_by_item: dict[int, object] = {}
        self.nav_buttons: list[QPushButton] = []

        self.theme_dropdown: QComboBox | None = None
        self.refresh_spin: QSpinBox | None = None
        self.alert_spin: QSpinBox | None = None
        self.auto_check: QCheckBox | None = None
        self.summary_label: QLabel | None = None
        self.status_label: QLabel | None = None
        self.disk_list: QListWidget | None = None
        self.details_view: QTextEdit | None = None
        self.trends_view: QTextEdit | None = None
        self.stack: QStackedWidget | None = None

        self.auto_timer = QTimer(self)
        self.auto_timer.timeout.connect(lambda: self.refresh_health(set_status=False))
        self.health_ready.connect(self._render_health)

        self._build_ui()
        self._apply_settings()
        self.refresh_health(set_status=False)
        self._schedule_auto()

    def _build_ui(self):
        apply_qt_theme(self.app, self.theme_name)

        root = QWidget()
        root.setObjectName("appRoot")
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        self.setCentralWidget(root)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(12, 14, 12, 12)
        side_layout.setSpacing(8)
        shell.addWidget(sidebar)

        brand = QLabel("Disk Health")
        brand.setObjectName("brandTitle")
        side_layout.addWidget(brand)

        for index, (label, page_name) in enumerate((("Health", "health"), ("Trends", "trends"))):
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setProperty("pageName", page_name)
            button.clicked.connect(lambda _checked=False, page=index: self._set_page(page))
            side_layout.addWidget(button)
            self.nav_buttons.append(button)

        side_layout.addSpacing(10)
        line = QFrame()
        line.setObjectName("sidebarLine")
        line.setFrameShape(QFrame.Shape.HLine)
        side_layout.addWidget(line)

        theme_label = QLabel("Theme")
        theme_label.setObjectName("sidebarLabel")
        side_layout.addWidget(theme_label)

        self.theme_dropdown = QComboBox()
        self.theme_dropdown.addItems(["dark", "light"])
        self.theme_dropdown.currentTextChanged.connect(self._on_theme_changed)
        side_layout.addWidget(self.theme_dropdown)

        side_layout.addStretch(1)

        quit_button = QPushButton("Quit")
        quit_button.setObjectName("navButton")
        quit_button.clicked.connect(lambda _checked=False: self.app.quit())
        side_layout.addWidget(quit_button)

        content = QWidget()
        content.setObjectName("content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(26, 22, 26, 18)
        content_layout.setSpacing(16)
        shell.addWidget(content, 1)

        header = QVBoxLayout()
        header.setSpacing(2)
        title = QLabel("Disk Health Monitor")
        title.setObjectName("pageTitle")
        subtitle = QLabel("SMART/NVMe status, temperature trends, and alerting")
        subtitle.setObjectName("mutedText")
        header.addWidget(title)
        header.addWidget(subtitle)
        content_layout.addLayout(header)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_health_page())
        self.stack.addWidget(self._build_trends_page())
        content_layout.addWidget(self.stack, 1)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        content_layout.addWidget(self.status_label)

        self._set_page(0)

    def _build_health_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        controls = QFrame()
        controls.setObjectName("panel")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(12, 12, 12, 12)
        controls_layout.setSpacing(8)
        layout.addWidget(controls)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setProperty("primary", True)
        refresh_btn.clicked.connect(lambda _checked=False: self.refresh_health())
        controls_layout.addWidget(refresh_btn)

        smart_btn = QPushButton("Full SMART")
        smart_btn.clicked.connect(lambda _checked=False: self.run_full_smart())
        controls_layout.addWidget(smart_btn)

        controls_layout.addSpacing(10)
        controls_layout.addWidget(QLabel("Refresh (s)"))
        self.refresh_spin = QSpinBox()
        self.refresh_spin.setRange(30, 1800)
        self.refresh_spin.setSingleStep(10)
        self.refresh_spin.valueChanged.connect(lambda _value: self._on_options_changed())
        controls_layout.addWidget(self.refresh_spin)

        controls_layout.addWidget(QLabel("Alert temp (C)"))
        self.alert_spin = QSpinBox()
        self.alert_spin.setRange(30, 100)
        self.alert_spin.valueChanged.connect(lambda _value: self._on_options_changed())
        controls_layout.addWidget(self.alert_spin)

        self.auto_check = QCheckBox("Auto refresh")
        self.auto_check.stateChanged.connect(lambda _state: self._on_options_changed())
        controls_layout.addWidget(self.auto_check)
        controls_layout.addStretch(1)

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("summaryLabel")
        layout.addWidget(self.summary_label)

        split = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(split, 1)

        disk_panel = QFrame()
        disk_panel.setObjectName("panel")
        disk_layout = QVBoxLayout(disk_panel)
        disk_layout.setContentsMargins(12, 12, 12, 12)
        disk_layout.setSpacing(8)
        disk_title = QLabel("Disks")
        disk_title.setObjectName("sectionTitle")
        disk_layout.addWidget(disk_title)
        self.disk_list = QListWidget()
        self.disk_list.setObjectName("resultList")
        self.disk_list.setSpacing(8)
        self.disk_list.itemSelectionChanged.connect(self._on_disk_selected)
        disk_layout.addWidget(self.disk_list, 1)
        split.addWidget(disk_panel)

        details_panel = QFrame()
        details_panel.setObjectName("panel")
        details_layout = QVBoxLayout(details_panel)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setSpacing(8)
        details_title = QLabel("Details")
        details_title.setObjectName("sectionTitle")
        details_layout.addWidget(details_title)
        self.details_view = QTextEdit()
        self.details_view.setObjectName("textView")
        self.details_view.setReadOnly(True)
        self.details_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        details_layout.addWidget(self.details_view, 1)
        split.addWidget(details_panel)
        split.setSizes([300, 430])

        return page

    def _build_trends_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        trend_panel = QFrame()
        trend_panel.setObjectName("panel")
        trend_layout = QVBoxLayout(trend_panel)
        trend_layout.setContentsMargins(12, 12, 12, 12)
        trend_layout.setSpacing(8)
        title = QLabel("Temperature History")
        title.setObjectName("sectionTitle")
        trend_layout.addWidget(title)
        self.trends_view = QTextEdit()
        self.trends_view.setObjectName("textView")
        self.trends_view.setReadOnly(True)
        self.trends_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        trend_layout.addWidget(self.trends_view, 1)
        layout.addWidget(trend_panel, 1)
        return page

    def _apply_settings(self):
        if self.theme_dropdown is not None:
            self.theme_dropdown.blockSignals(True)
            self.theme_dropdown.setCurrentText(self.theme_name)
            self.theme_dropdown.blockSignals(False)
        if self.refresh_spin is not None:
            self.refresh_spin.setValue(int(self.settings.get("refresh_interval_sec", 60)))
        if self.alert_spin is not None:
            self.alert_spin.setValue(int(self.settings.get("alert_temp_c", 60)))
        if self.auto_check is not None:
            self.auto_check.setChecked(bool(self.settings.get("auto_refresh", True)))
        self._apply_theme(self.theme_name)

    def _set_page(self, index: int):
        if self.stack is not None:
            self.stack.setCurrentIndex(index)
        for button_index, button in enumerate(self.nav_buttons):
            button.setChecked(button_index == index)

    def _set_status(self, text: str):
        if self.status_label is not None:
            self.status_label.setText(text)

    def _set_text(self, view: QTextEdit | None, text: str):
        if view is not None:
            view.setPlainText(text)

    def _on_theme_changed(self, theme_name: str):
        self._apply_theme(theme_name)

    def _apply_theme(self, theme_name: str):
        if theme_name not in THEMES:
            theme_name = "dark"
        self.theme_name = theme_name
        self.settings["theme"] = theme_name
        save_settings(self.settings)
        apply_qt_theme(self.app, theme_name)

    def _on_options_changed(self):
        if self.refresh_spin is not None:
            self.settings["refresh_interval_sec"] = int(self.refresh_spin.value())
        if self.alert_spin is not None:
            self.settings["alert_temp_c"] = int(self.alert_spin.value())
        if self.auto_check is not None:
            self.settings["auto_refresh"] = bool(self.auto_check.isChecked())
        save_settings(self.settings)
        self._schedule_auto()

    def _schedule_auto(self):
        self.auto_timer.stop()
        if bool(self.settings.get("auto_refresh", True)):
            interval = max(30, int(self.settings.get("refresh_interval_sec", 60)))
            self.auto_timer.start(interval * 1000)

    def refresh_health(self, set_status: bool = True):
        alert_temp = int(self.settings.get("alert_temp_c", 60))
        if set_status:
            self._set_status("Refreshing disk health...")

        def task():
            rows = read_all_disk_health(alert_temp_c=alert_temp)
            self.health_ready.emit(rows, set_status)

        threading.Thread(target=task, daemon=True).start()

    def _render_health(self, rows, set_status: bool):
        self.rows = list(rows)

        if self.disk_list is not None:
            self.disk_list.clear()
            self.row_data_by_item.clear()

            for idx, row_data in enumerate(rows):
                temp_str = "N/A" if row_data.temp_c is None else f"{row_data.temp_c}C"
                alerts = ", ".join(row_data.alerts) if row_data.alerts else "none"
                line = (
                    f"{row_data.device} | {row_data.health:<7} | temp={temp_str:<6} | "
                    f"hours={row_data.power_on_hours if row_data.power_on_hours is not None else 'N/A'} | alerts={alerts}"
                )
                item = QListWidgetItem(line)
                item.setData(Qt.ItemDataRole.UserRole, idx)
                self.row_data_by_item[idx] = row_data
                self.disk_list.addItem(item)

            if self.disk_list.count() > 0 and self.disk_list.currentRow() < 0:
                self.disk_list.setCurrentRow(0)

        total_alerts = sum(len(r.alerts) for r in rows)
        if self.summary_label is not None:
            self.summary_label.setText(
                f"Disks: {len(rows)} | Alerts: {total_alerts} | Temp threshold: {self.settings.get('alert_temp_c', 60)}C"
            )

        self._update_history(rows)
        self._render_trends()

        if set_status:
            self._set_status("Disk health refreshed")

    def _on_disk_selected(self):
        if self.disk_list is None:
            return
        item = self.disk_list.currentItem()
        if item is None:
            return
        idx = item.data(Qt.ItemDataRole.UserRole)
        data = self.row_data_by_item.get(idx)
        if data is None:
            return

        details = (
            f"Device: {data.device}\n"
            f"Model: {data.model}\n"
            f"Protocol: {data.protocol}\n"
            f"Size: {data.size}\n"
            f"Health: {data.health}\n"
            f"Temp: {data.temp_c if data.temp_c is not None else 'N/A'}\n"
            f"Power-on hours: {data.power_on_hours if data.power_on_hours is not None else 'N/A'}\n"
            f"Alerts: {', '.join(data.alerts) if data.alerts else 'none'}\n\n"
            f"Raw output:\n{data.details}"
        )
        self._set_text(self.details_view, details)
        self._set_status(f"Selected {data.device}")

    def _update_history(self, rows):
        history = self.settings.get("history", {})
        if not isinstance(history, dict):
            history = {}

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for row in rows:
            points = history.get(row.device, [])
            if not isinstance(points, list):
                points = []
            points.append({"ts": now, "temp": row.temp_c, "health": row.health})
            history[row.device] = points[-200:]

        self.settings["history"] = history
        save_settings(self.settings)

    def _render_trends(self):
        history = self.settings.get("history", {})
        if not isinstance(history, dict) or not history:
            self._set_text(self.trends_view, "No history yet.")
            return

        lines: list[str] = []
        for device in sorted(history.keys()):
            lines.append(f"[{device}]")
            points = history.get(device, [])
            if not isinstance(points, list):
                lines.append("  (invalid history)")
                lines.append("")
                continue
            for point in points[-40:]:
                temp = point.get("temp")
                temp_s = "N/A" if temp is None else f"{temp}C"
                lines.append(f"  {point.get('ts', '?')} | health={point.get('health', '?')} | temp={temp_s}")
            lines.append("")

        self._set_text(self.trends_view, "\n".join(lines).strip())

    def _selected_device(self) -> str:
        if self.disk_list is None:
            return ""
        item = self.disk_list.currentItem()
        if item is None:
            return ""
        data = self.row_data_by_item.get(item.data(Qt.ItemDataRole.UserRole))
        if data is None:
            return ""
        return str(data.device)

    def run_full_smart(self):
        device = self._selected_device()
        if not device:
            self._set_status("Select a disk first")
            return

        cmd = f"sudo smartctl -x {device} || sudo nvme smart-log {device}"
        ok, msg = launch_in_terminal(cmd, title=f"SMART Report: {device}")
        self._set_status(msg if ok else f"Failed to open terminal: {msg}")


class DiskHealthApp(QApplication):
    def __init__(self):
        super().__init__(sys.argv)
        self.setApplicationName("Disk Health Monitor")
        self.setApplicationDisplayName("Disk Health Monitor")
        self.setOrganizationName("Evans")
        self.window = DiskHealthWindow(self)
        icon_path = "org.evans.DiskHealthMonitor.svg"
        self.window.setWindowIcon(QIcon(icon_path))

    def run(self, _argv: list[str] | None = None) -> int:
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        return self.exec()
