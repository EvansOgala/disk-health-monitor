from __future__ import annotations

import ctypes
import os
import sys
import threading
from datetime import datetime
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from disk_ops import launch_in_terminal, read_all_disk_health
from settings import load_settings, save_settings

_LIGHT_QSS = """
QWidget {
  font-family: "Segoe UI Variable", "Segoe UI", "Inter", sans-serif;
  font-size: 13px;
  color: #1c2433;
}
QMainWindow { background: #eef2f7; }
QGroupBox {
  background: #ffffff;
  border: 1px solid rgba(27, 39, 64, 0.12);
  border-radius: 12px;
  margin-top: 10px;
  padding: 12px;
}
QGroupBox::title {
  subcontrol-origin: margin;
  left: 10px;
  padding: 0 6px 0 6px;
  color: #1c2433;
  font-weight: 600;
}
QLineEdit, QComboBox, QSpinBox, QTextEdit, QListWidget {
  border: 1px solid rgba(27, 39, 64, 0.14);
  border-radius: 10px;
  padding: 7px 10px;
  background: #ffffff;
}
QPushButton {
  border-radius: 18px;
  padding: 7px 14px;
  background: #2b7cff;
  color: white;
  font-weight: 600;
}
QPushButton:disabled { background: rgba(120, 140, 170, 0.5); }
"""

_DARK_QSS = """
QWidget {
  font-family: "Segoe UI Variable", "Segoe UI", "Inter", sans-serif;
  font-size: 13px;
  color: #e6e9f2;
}
QMainWindow { background: #1b1f2a; }
QGroupBox {
  background: #232a36;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  margin-top: 10px;
  padding: 12px;
}
QGroupBox::title {
  subcontrol-origin: margin;
  left: 10px;
  padding: 0 6px 0 6px;
  color: #e6e9f2;
  font-weight: 600;
}
QLineEdit, QComboBox, QSpinBox, QTextEdit, QListWidget {
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 10px;
  padding: 7px 10px;
  background: #1f2430;
  color: #e6e9f2;
}
QPushButton {
  border-radius: 18px;
  padding: 7px 14px;
  background: #3f7bff;
  color: white;
  font-weight: 600;
}
QPushButton:disabled { background: rgba(120, 140, 170, 0.45); }
"""


class DiskHealthQtWindow(QtWidgets.QMainWindow):
    health_ready = QtCore.Signal(object, object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Disk Health Monitor")
        self.resize(1240, 860)

        self.settings = load_settings()
        self.rows = []
        self.row_data_by_index: dict[int, object] = {}
        self._elevation_prompted = False
        self.auto_timer = QtCore.QTimer(self)
        self.auto_timer.timeout.connect(lambda: self.refresh_health(set_status=False))
        self.health_ready.connect(self._render_health)

        self._build_ui()
        self._apply_settings()
        self.refresh_health(set_status=False)
        self._schedule_auto()

    def _build_ui(self):
        root = QtWidgets.QWidget()
        self.setCentralWidget(root)
        outer = QtWidgets.QVBoxLayout(root)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(10)

        self.title_label = QtWidgets.QLabel("Disk Health Monitor")
        self.title_label.setStyleSheet("font-size: 26px; font-weight: 700;")
        self.subtitle_label = QtWidgets.QLabel("Disk status, temperature trends, and alerting")
        outer.addWidget(self.title_label)
        outer.addWidget(self.subtitle_label)

        controls = QtWidgets.QHBoxLayout()
        outer.addLayout(controls)

        refresh_btn = QtWidgets.QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_health)
        controls.addWidget(refresh_btn)

        self.detail_btn = QtWidgets.QPushButton("Full Details")
        self.detail_btn.clicked.connect(self.run_full_details)
        controls.addWidget(self.detail_btn)

        controls.addWidget(QtWidgets.QLabel("Refresh (s)"))
        self.refresh_spin = QtWidgets.QSpinBox()
        self.refresh_spin.setRange(30, 1800)
        self.refresh_spin.setSingleStep(10)
        self.refresh_spin.valueChanged.connect(self._on_options_changed)
        controls.addWidget(self.refresh_spin)

        controls.addWidget(QtWidgets.QLabel("Alert temp (C)"))
        self.alert_spin = QtWidgets.QSpinBox()
        self.alert_spin.setRange(30, 100)
        self.alert_spin.valueChanged.connect(self._on_options_changed)
        controls.addWidget(self.alert_spin)

        self.auto_check = QtWidgets.QCheckBox("Auto refresh")
        self.auto_check.stateChanged.connect(self._on_options_changed)
        controls.addWidget(self.auto_check)

        controls.addWidget(QtWidgets.QLabel("Theme"))
        self.theme_box = QtWidgets.QComboBox()
        self.theme_box.addItems(["light", "dark"])
        self.theme_box.currentIndexChanged.connect(self._on_theme_changed)
        controls.addWidget(self.theme_box)
        controls.addStretch(1)

        self.summary_label = QtWidgets.QLabel("")
        outer.addWidget(self.summary_label)

        tabs = QtWidgets.QTabWidget()
        outer.addWidget(tabs, 1)

        health_tab = QtWidgets.QWidget()
        health_layout = QtWidgets.QVBoxLayout(health_tab)
        split = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        health_layout.addWidget(split)

        top_box = QtWidgets.QGroupBox("Disks")
        top_layout = QtWidgets.QVBoxLayout(top_box)
        self.disk_list = QtWidgets.QListWidget()
        self.disk_list.itemSelectionChanged.connect(self._on_disk_selected)
        top_layout.addWidget(self.disk_list)
        split.addWidget(top_box)

        details_box = QtWidgets.QGroupBox("Details")
        details_layout = QtWidgets.QVBoxLayout(details_box)
        self.details_view = QtWidgets.QTextEdit()
        self.details_view.setReadOnly(True)
        details_layout.addWidget(self.details_view)
        split.addWidget(details_box)
        split.setSizes([260, 420])
        tabs.addTab(health_tab, "Health")

        trends_tab = QtWidgets.QWidget()
        trends_layout = QtWidgets.QVBoxLayout(trends_tab)
        self.trends_view = QtWidgets.QTextEdit()
        self.trends_view.setReadOnly(True)
        trends_layout.addWidget(self.trends_view)
        tabs.addTab(trends_tab, "Trends")

        self.status_label = QtWidgets.QLabel("Ready")
        outer.addWidget(self.status_label)

    def _apply_settings(self):
        self.refresh_spin.setValue(int(self.settings.get("refresh_interval_sec", 60)))
        self.alert_spin.setValue(int(self.settings.get("alert_temp_c", 60)))
        self.auto_check.setChecked(bool(self.settings.get("auto_refresh", True)))
        theme = self.settings.get("theme", "light")
        self.theme_box.setCurrentIndex(0 if theme == "light" else 1)
        self._apply_theme(theme)

    def _set_status(self, text: str):
        self.status_label.setText(text)

    def _on_theme_changed(self):
        theme = self.theme_box.currentText()
        self.settings["theme"] = theme
        save_settings(self.settings)
        self._apply_theme(theme)

    def _apply_theme(self, theme: str):
        app = QtWidgets.QApplication.instance()
        if app is None:
            return
        if theme == "dark":
            app.setStyle("Fusion")
            app.setStyleSheet(_DARK_QSS)
            self.title_label.setStyleSheet("font-size: 26px; font-weight: 700; color: #e6e9f2;")
            self.subtitle_label.setStyleSheet("color: rgba(230,233,242,0.72);")
            self.status_label.setStyleSheet("color: rgba(230,233,242,0.68);")
        else:
            app.setStyle("Fusion")
            app.setStyleSheet(_LIGHT_QSS)
            self.title_label.setStyleSheet("font-size: 26px; font-weight: 700; color: #1f2a44;")
            self.subtitle_label.setStyleSheet("color: rgba(30,40,60,0.72);")
            self.status_label.setStyleSheet("color: rgba(30,40,60,0.68);")

    def _on_options_changed(self):
        self.settings["refresh_interval_sec"] = int(self.refresh_spin.value())
        self.settings["alert_temp_c"] = int(self.alert_spin.value())
        self.settings["auto_refresh"] = bool(self.auto_check.isChecked())
        save_settings(self.settings)
        self._schedule_auto()

    def _schedule_auto(self):
        self.auto_timer.stop()
        if bool(self.settings.get("auto_refresh", True)):
            self.auto_timer.start(max(30, int(self.settings.get("refresh_interval_sec", 60))) * 1000)

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
        self.disk_list.clear()
        self.row_data_by_index.clear()

        for idx, row_data in enumerate(rows):
            temp_str = "N/A" if row_data.temp_c is None else f"{row_data.temp_c}C"
            alerts = ", ".join(row_data.alerts) if row_data.alerts else "none"
            line = (
                f"{row_data.device} | {row_data.health:<7} | temp={temp_str:<6} | "
                f"hours={row_data.power_on_hours if row_data.power_on_hours is not None else 'N/A'} | alerts={alerts}"
            )
            self.disk_list.addItem(line)
            self.row_data_by_index[idx] = row_data

        total_alerts = sum(len(r.alerts) for r in rows)
        self.summary_label.setText(
            f"Disks: {len(rows)} | Alerts: {total_alerts} | Temp threshold: {self.settings.get('alert_temp_c', 60)}C"
        )
        if os.name == "nt":
            all_unknown = bool(rows) and all(str(r.health).lower() == "unknown" for r in rows)
            if all_unknown:
                self._set_status("Install smartmontools (smartctl) and run as Administrator for SMART health data")
                if not self._is_windows_admin() and not self._elevation_prompted:
                    self._elevation_prompted = True
                    self._prompt_admin_restart()
        self._update_history(rows)
        self._render_trends()
        if self.disk_list.count() > 0 and self.disk_list.currentRow() < 0:
            self.disk_list.setCurrentRow(0)
        if set_status:
            self._set_status("Disk health refreshed")

    def _on_disk_selected(self):
        idx = self.disk_list.currentRow()
        if idx < 0:
            return
        data = self.row_data_by_index.get(idx)
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
        self.details_view.setPlainText(details)
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
            self.trends_view.setPlainText("No history yet.")
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
        self.trends_view.setPlainText("\n".join(lines).strip())

    def _selected_device(self) -> str:
        idx = self.disk_list.currentRow()
        if idx < 0:
            return ""
        data = self.row_data_by_index.get(idx)
        if data is None:
            return ""
        return str(data.device)

    def run_full_details(self):
        device = self._selected_device()
        if not device:
            self._set_status("Select a disk first")
            return
        if os.name == "nt":
            cmd = f"smartctl -x \"{device}\""
        else:
            cmd = f"sudo smartctl -x {device} || sudo nvme smart-log {device}"
        ok, msg = launch_in_terminal(cmd, title=f"Disk Report: {device}")
        self._set_status(msg if ok else f"Failed to open terminal: {msg}")

    def _is_windows_admin(self) -> bool:
        if os.name != "nt":
            return False
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:  # noqa: BLE001
            return False

    def _prompt_admin_restart(self):
        reply = QtWidgets.QMessageBox.question(
            self,
            "Admin Access Recommended",
            "SMART access is limited without Administrator privileges.\n\n"
            "Relaunch Disk Health Monitor as Administrator now?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.Yes,
        )
        if reply != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        self._restart_as_admin()

    def _restart_as_admin(self):
        if os.name != "nt":
            return
        try:
            if getattr(sys, "frozen", False):
                target = sys.executable
                params = ""
            else:
                target = sys.executable
                main_py = Path(__file__).with_name("main.py")
                params = f'"{main_py}"'
            result = ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                target,
                params,
                None,
                1,
            )
            if int(result) <= 32:
                self._set_status("Elevation canceled or failed")
                return
            QtWidgets.QApplication.quit()
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Failed to elevate: {exc}")


class DiskHealthQtApp:
    @staticmethod
    def run_app():
        app = QtWidgets.QApplication([])
        app.setStyle("Fusion")
        window = DiskHealthQtWindow()
        icon_path = os.path.join(os.path.dirname(__file__), "org.evans.DiskHealthMonitor.svg")
        if os.path.exists(icon_path):
            window.setWindowIcon(QtGui.QIcon(icon_path))
        window.show()
        app.exec()
