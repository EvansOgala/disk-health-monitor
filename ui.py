from __future__ import annotations

import threading
from datetime import datetime

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

from disk_ops import launch_in_terminal, read_all_disk_health
from settings import load_settings, save_settings
from gtk_style import install_material_smooth_css


class DiskHealthApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.evans.DiskHealthMonitor")
        self.window: Gtk.ApplicationWindow | None = None

        self.settings = load_settings()
        self.theme_values = ["dark", "light"]
        self.css_provider = None

        self.theme_dropdown: Gtk.DropDown | None = None
        self.status_label: Gtk.Label | None = None

        self.refresh_spin: Gtk.SpinButton | None = None
        self.alert_spin: Gtk.SpinButton | None = None
        self.auto_switch: Gtk.Switch | None = None

        self.summary_label: Gtk.Label | None = None
        self.disk_list: Gtk.ListBox | None = None
        self.details_view: Gtk.TextView | None = None
        self.trends_view: Gtk.TextView | None = None

        self.rows = []
        self.row_data_by_key: dict[str, object] = {}
        self.auto_source_id: int | None = None

    def do_activate(self):
        if self.window is None:
            self._build_ui()
            self.refresh_health(set_status=False)
            self._schedule_auto()
        self.window.present()

    def _build_ui(self):
        self.window = Gtk.ApplicationWindow(application=self)
        self.window.set_title("Disk Health Monitor")
        self.window.set_default_size(1260, 860)
        self.css_provider = install_material_smooth_css(self.window)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        root.set_margin_top(12)
        root.set_margin_bottom(12)
        root.set_margin_start(12)
        root.set_margin_end(12)
        self.window.set_child(root)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        root.append(header)

        title_wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        header.append(title_wrap)

        title = Gtk.Label(label="Disk Health Monitor")
        title.set_xalign(0.0)
        title.add_css_class("title-2")
        title_wrap.append(title)

        subtitle = Gtk.Label(label="SMART/NVMe status, temperature trends, and alerting")
        subtitle.set_xalign(0.0)
        subtitle.add_css_class("dim-label")
        title_wrap.append(subtitle)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header.append(spacer)

        self.theme_dropdown = Gtk.DropDown.new_from_strings(self.theme_values)
        self._set_dropdown_value(self.theme_dropdown, self.theme_values, self.settings.get("theme", "dark"))
        self.theme_dropdown.connect("notify::selected", self._on_theme_changed)
        header.append(self.theme_dropdown)

        notebook = Gtk.Notebook()
        notebook.set_hexpand(True)
        notebook.set_vexpand(True)
        root.append(notebook)

        notebook.append_page(self._build_health_tab(), Gtk.Label(label="Health"))
        notebook.append_page(self._build_trends_tab(), Gtk.Label(label="Trends"))

        self.status_label = Gtk.Label(label="Ready")
        self.status_label.set_xalign(0.0)
        self.status_label.add_css_class("dim-label")
        root.append(self.status_label)

        self._apply_theme(self.settings.get("theme", "dark"))

    def _build_health_tab(self) -> Gtk.Widget:
        tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        tab.set_margin_top(10)
        tab.set_margin_bottom(10)
        tab.set_margin_start(10)
        tab.set_margin_end(10)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        tab.append(controls)

        refresh_btn = Gtk.Button(label="Refresh")
        refresh_btn.connect("clicked", lambda _b: self.refresh_health())
        controls.append(refresh_btn)

        smart_btn = Gtk.Button(label="Full SMART")
        smart_btn.connect("clicked", lambda _b: self.run_full_smart())
        controls.append(smart_btn)

        controls.append(Gtk.Label(label="Refresh (s)"))
        self.refresh_spin = Gtk.SpinButton.new_with_range(30, 1800, 10)
        self.refresh_spin.set_value(int(self.settings.get("refresh_interval_sec", 60)))
        self.refresh_spin.connect("value-changed", self._on_options_changed)
        controls.append(self.refresh_spin)

        controls.append(Gtk.Label(label="Alert temp (C)"))
        self.alert_spin = Gtk.SpinButton.new_with_range(30, 100, 1)
        self.alert_spin.set_value(int(self.settings.get("alert_temp_c", 60)))
        self.alert_spin.connect("value-changed", self._on_options_changed)
        controls.append(self.alert_spin)

        controls.append(Gtk.Label(label="Auto refresh"))
        self.auto_switch = Gtk.Switch()
        self.auto_switch.set_active(bool(self.settings.get("auto_refresh", True)))
        self.auto_switch.connect("notify::active", self._on_options_changed)
        controls.append(self.auto_switch)

        self.summary_label = Gtk.Label(label="")
        self.summary_label.set_xalign(0.0)
        self.summary_label.add_css_class("dim-label")
        tab.append(self.summary_label)

        split = Gtk.Paned.new(Gtk.Orientation.VERTICAL)
        split.set_hexpand(True)
        split.set_vexpand(True)
        tab.append(split)

        list_frame = Gtk.Frame(label="Disks")
        split.set_start_child(list_frame)

        list_scroller = Gtk.ScrolledWindow()
        list_scroller.set_hexpand(True)
        list_scroller.set_vexpand(True)
        list_frame.set_child(list_scroller)

        self.disk_list = Gtk.ListBox()
        self.disk_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.disk_list.connect("row-selected", self._on_disk_selected)
        list_scroller.set_child(self.disk_list)

        details_frame = Gtk.Frame(label="Details")
        split.set_end_child(details_frame)

        details_scroller = Gtk.ScrolledWindow()
        details_scroller.set_hexpand(True)
        details_scroller.set_vexpand(True)
        details_frame.set_child(details_scroller)

        self.details_view = Gtk.TextView()
        self.details_view.set_editable(False)
        self.details_view.set_monospace(True)
        details_scroller.set_child(self.details_view)

        return tab

    def _build_trends_tab(self) -> Gtk.Widget:
        tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        tab.set_margin_top(10)
        tab.set_margin_bottom(10)
        tab.set_margin_start(10)
        tab.set_margin_end(10)

        trend_scroller = Gtk.ScrolledWindow()
        trend_scroller.set_hexpand(True)
        trend_scroller.set_vexpand(True)
        tab.append(trend_scroller)

        self.trends_view = Gtk.TextView()
        self.trends_view.set_editable(False)
        self.trends_view.set_monospace(True)
        trend_scroller.set_child(self.trends_view)

        return tab

    def _set_status(self, text: str):
        if self.status_label is not None:
            self.status_label.set_text(text)

    def _set_text(self, view: Gtk.TextView | None, text: str):
        if view is None:
            return
        view.get_buffer().set_text(text)

    def _on_theme_changed(self, dropdown: Gtk.DropDown, _param):
        self._apply_theme(self._get_dropdown_value(dropdown, self.theme_values))

    def _apply_theme(self, theme_name: str):
        if theme_name not in {"dark", "light"}:
            theme_name = "dark"

        self.settings["theme"] = theme_name
        save_settings(self.settings)

        gtk_settings = Gtk.Settings.get_default()
        if gtk_settings is not None:
            gtk_settings.set_property("gtk-application-prefer-dark-theme", theme_name == "dark")

    def _on_options_changed(self, _widget, _param=None):
        if self.refresh_spin is not None:
            self.settings["refresh_interval_sec"] = int(self.refresh_spin.get_value())
        if self.alert_spin is not None:
            self.settings["alert_temp_c"] = int(self.alert_spin.get_value())
        if self.auto_switch is not None:
            self.settings["auto_refresh"] = bool(self.auto_switch.get_active())
        save_settings(self.settings)
        self._schedule_auto()

    def _schedule_auto(self):
        if self.auto_source_id is not None:
            GLib.source_remove(self.auto_source_id)
            self.auto_source_id = None

        auto_enabled = bool(self.settings.get("auto_refresh", True))
        interval = int(self.settings.get("refresh_interval_sec", 60))
        if auto_enabled:
            self.auto_source_id = GLib.timeout_add_seconds(max(30, interval), self._on_auto_tick)

    def _on_auto_tick(self):
        self.refresh_health(set_status=False)
        return True

    def refresh_health(self, set_status: bool = True):
        alert_temp = int(self.settings.get("alert_temp_c", 60))
        if set_status:
            self._set_status("Refreshing disk health...")

        def task():
            rows = read_all_disk_health(alert_temp_c=alert_temp)
            GLib.idle_add(self._render_health, rows, set_status)

        threading.Thread(target=task, daemon=True).start()

    def _render_health(self, rows, set_status: bool):
        self.rows = list(rows)

        if self.disk_list is not None:
            self._clear_listbox(self.disk_list)
            self.row_data_by_key.clear()

            for idx, row_data in enumerate(rows):
                temp_str = "N/A" if row_data.temp_c is None else f"{row_data.temp_c}C"
                alerts = ", ".join(row_data.alerts) if row_data.alerts else "none"
                line = (
                    f"{row_data.device} | {row_data.health:<7} | temp={temp_str:<6} | "
                    f"hours={row_data.power_on_hours if row_data.power_on_hours is not None else 'N/A'} | alerts={alerts}"
                )
                row = Gtk.ListBoxRow()
                label = Gtk.Label(label=line, xalign=0.0)
                label.set_selectable(False)
                row.set_child(label)
                row_key = f"disk-{idx}"
                row.set_name(row_key)
                self.row_data_by_key[row_key] = row_data
                self.disk_list.append(row)

        total_alerts = sum(len(r.alerts) for r in rows)
        if self.summary_label is not None:
            self.summary_label.set_text(
                f"Disks: {len(rows)} | Alerts: {total_alerts} | Temp threshold: {self.settings.get('alert_temp_c', 60)}C"
            )

        self._update_history(rows)
        self._render_trends()

        if set_status:
            self._set_status("Disk health refreshed")
        return False

    def _on_disk_selected(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow | None):
        if row is None:
            return
        data = self.row_data_by_key.get(row.get_name() or "")
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
            points.append(
                {
                    "ts": now,
                    "temp": row.temp_c,
                    "health": row.health,
                }
            )
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
        row = self.disk_list.get_selected_row()
        if row is None:
            return ""
        data = self.row_data_by_key.get(row.get_name() or "")
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

    @staticmethod
    def _set_dropdown_value(dropdown: Gtk.DropDown, values: list[str], value: str):
        try:
            idx = values.index(value)
        except ValueError:
            idx = 0
        dropdown.set_selected(idx)

    @staticmethod
    def _get_dropdown_value(dropdown: Gtk.DropDown, values: list[str]) -> str:
        idx = int(dropdown.get_selected())
        if 0 <= idx < len(values):
            return values[idx]
        return values[0]

    @staticmethod
    def _clear_listbox(box: Gtk.ListBox):
        child = box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            box.remove(child)
            child = nxt
