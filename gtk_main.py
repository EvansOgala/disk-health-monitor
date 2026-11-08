"""Native GNOME/libadwaita frontend for Disk Health Monitor."""
from __future__ import annotations

import sys
import threading

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from disk_ops import launch_in_terminal, read_all_disk_health
from settings import load_settings, save_settings


class DiskHealthGtk(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.evans.DiskHealthMonitor.Gtk", flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.settings = load_settings()
        self.rows = []
        self.window = None
        self.disk_list = None
        self.details = None
        self.trends = None
        self.summary = None
        self.status = None
        self.refresh_spin = None
        self.alert_spin = None
        self.auto_switch = None
        self.stack = None
        self.refresh_button = None
        self.timer_id = 0

    def do_activate(self):
        if self.window is None:
            self._build_window()
        self.window.present()

    def _build_window(self):
        Adw.init()
        self.window = Adw.ApplicationWindow(application=self, title="Disk Health Monitor", default_width=1180, default_height=800)
        self.window.set_size_request(900, 620)
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title="Disk Health", subtitle="SMART status and temperature monitoring"))
        toolbar.add_top_bar(header)

        self.stack = Adw.ViewStack()
        self.stack.add_titled_with_icon(self._health_page(), "health", "Health", "drive-harddisk-symbolic")
        self.stack.add_titled_with_icon(self._trends_page(), "trends", "Trends", "view-list-bullet-symbolic")
        switcher = Adw.ViewSwitcher()
        switcher.set_stack(self.stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        header.set_title_widget(switcher)
        toolbar.set_content(self.stack)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        footer.add_css_class("toolbar")
        footer.set_margin_start(18); footer.set_margin_end(18)
        footer.set_margin_top(7); footer.set_margin_bottom(9)
        self.status = Gtk.Label(label="Starting disk scan…", xalign=0)
        self.status.add_css_class("dim-label")
        footer.append(self.status)
        toolbar.add_bottom_bar(footer)
        self.window.set_content(toolbar)
        self._render_trends()
        self.refresh_health()
        self._schedule_auto()

    @staticmethod
    def _page(title: str, subtitle: str) -> Gtk.Box:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_margin_start(24); page.set_margin_end(24)
        page.set_margin_top(20); page.set_margin_bottom(16)
        heading = Gtk.Label(label=title, xalign=0); heading.add_css_class("title-1")
        sub = Gtk.Label(label=subtitle, xalign=0, wrap=True); sub.add_css_class("dim-label")
        page.append(heading); page.append(sub)
        return page

    @staticmethod
    def _card() -> Gtk.Box:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.add_css_class("card")
        return card

    def _health_page(self) -> Gtk.Widget:
        page = self._page("Drive health", "Review drive status, temperature, and SMART details.")
        toolbar = self._card()
        toolbar.set_margin_top(8)
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        top.set_margin_start(12); top.set_margin_end(12); top.set_margin_top(12)
        self.refresh_button = Gtk.Button(label="Refresh")
        self.refresh_button.add_css_class("suggested-action")
        self.refresh_button.connect("clicked", lambda *_: self.refresh_health())
        top.append(self.refresh_button)
        smart = Gtk.Button(label="Full SMART report")
        smart.connect("clicked", self.run_full_smart)
        top.append(smart)
        top.append(Gtk.Box(hexpand=True))
        self.auto_switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.auto_switch.set_active(bool(self.settings.get("auto_refresh", True)))
        self.auto_switch.connect("state-set", self._auto_changed)
        top.append(Gtk.Label(label="Auto refresh", valign=Gtk.Align.CENTER))
        top.append(self.auto_switch)
        toolbar.append(top)

        options = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        options.set_margin_start(12); options.set_margin_end(12); options.set_margin_bottom(12)
        options.append(Gtk.Label(label="Refresh every", valign=Gtk.Align.CENTER))
        self.refresh_spin = Gtk.SpinButton.new_with_range(30, 1800, 10)
        self.refresh_spin.set_value(int(self.settings.get("refresh_interval_sec", 60)))
        self.refresh_spin.connect("value-changed", self._options_changed)
        options.append(self.refresh_spin)
        options.append(Gtk.Label(label="seconds", valign=Gtk.Align.CENTER))
        options.append(Gtk.Box(hexpand=True))
        options.append(Gtk.Label(label="Alert at", valign=Gtk.Align.CENTER))
        self.alert_spin = Gtk.SpinButton.new_with_range(30, 100, 1)
        self.alert_spin.set_value(int(self.settings.get("alert_temp_c", 60)))
        self.alert_spin.connect("value-changed", self._options_changed)
        options.append(self.alert_spin)
        options.append(Gtk.Label(label="°C", valign=Gtk.Align.CENTER))
        toolbar.append(options)
        page.append(toolbar)

        self.summary = Gtk.Label(label="Waiting for scan…", xalign=0)
        self.summary.add_css_class("dim-label")
        self.summary.set_margin_start(4); self.summary.set_margin_top(2)
        page.append(self.summary)

        split = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, vexpand=True)
        split.set_position(440)
        list_card = self._card()
        list_card.set_margin_end(8)
        list_title = Gtk.Label(label="Drives", xalign=0)
        list_title.add_css_class("heading")
        list_title.set_margin_start(14); list_title.set_margin_top(12)
        list_card.append(list_title)
        self.disk_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.disk_list.add_css_class("boxed-list")
        self.disk_list.connect("row-selected", self._disk_selected)
        list_scroll = Gtk.ScrolledWindow(vexpand=True)
        list_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        list_scroll.set_margin_start(12); list_scroll.set_margin_end(12)
        list_scroll.set_margin_bottom(12)
        list_scroll.set_child(self.disk_list)
        list_card.append(list_scroll)
        split.set_start_child(list_card)

        detail_card = self._card()
        detail_card.set_margin_start(8)
        detail_title = Gtk.Label(label="Drive details", xalign=0)
        detail_title.add_css_class("heading")
        detail_title.set_margin_start(14); detail_title.set_margin_top(12)
        detail_card.append(detail_title)
        self.details = Gtk.TextView(editable=False, cursor_visible=False, monospace=True, wrap_mode=Gtk.WrapMode.NONE)
        self.details.set_left_margin(14); self.details.set_right_margin(14)
        self.details.set_top_margin(12); self.details.set_bottom_margin(12)
        detail_scroll = Gtk.ScrolledWindow(vexpand=True)
        detail_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        detail_scroll.set_margin_start(6); detail_scroll.set_margin_end(6); detail_scroll.set_margin_bottom(6)
        detail_scroll.set_child(self.details)
        detail_card.append(detail_scroll)
        split.set_end_child(detail_card)
        page.append(split)
        return page

    def _trends_page(self) -> Gtk.Widget:
        page = self._page("Temperature history", "Snapshots are saved locally as health scans run.")
        card = self._card()
        card.set_margin_top(8)
        self.trends = Gtk.TextView(editable=False, cursor_visible=False, monospace=True, wrap_mode=Gtk.WrapMode.NONE)
        self.trends.set_left_margin(16); self.trends.set_right_margin(16)
        self.trends.set_top_margin(14); self.trends.set_bottom_margin(14)
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.trends)
        card.append(scroll)
        page.append(card)
        return page

    def _set_text(self, view: Gtk.TextView, text: str):
        view.get_buffer().set_text(text)

    def _set_status(self, message: str):
        self.status.set_text(message)

    def refresh_health(self, *_):
        if self.refresh_button:
            self.refresh_button.set_sensitive(False)
        self._set_status("Checking SMART and NVMe health…")
        threshold = int(self.alert_spin.get_value()) if self.alert_spin else int(self.settings.get("alert_temp_c", 60))

        def worker():
            rows = read_all_disk_health(alert_temp_c=threshold)
            GLib.idle_add(self._render_health, rows)

        threading.Thread(target=worker, daemon=True).start()

    def _render_health(self, rows):
        self.rows = list(rows)
        child = self.disk_list.get_first_child()
        while child:
            following = child.get_next_sibling()
            self.disk_list.remove(child)
            child = following
        for index, data in enumerate(self.rows):
            row = Gtk.ListBoxRow()
            row.set_name(str(index))
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            box.set_margin_start(12); box.set_margin_end(12); box.set_margin_top(10); box.set_margin_bottom(10)
            title = Gtk.Label(label=f"{data.model}  ·  {data.device}", xalign=0)
            title.add_css_class("heading")
            detail = Gtk.Label(label=f"{data.size}  ·  {data.protocol}  ·  {data.health}", xalign=0)
            detail.add_css_class("dim-label")
            temp = "N/A" if data.temp_c is None else f"{data.temp_c} °C"
            alerts = f"{len(data.alerts)} alert(s)" if data.alerts else "No alerts"
            status = Gtk.Label(label=f"{temp}  ·  {alerts}", xalign=0)
            status.add_css_class("dim-label")
            box.append(title); box.append(detail); box.append(status)
            row.set_child(box)
            self.disk_list.append(row)
        total_alerts = sum(len(item.alerts) for item in self.rows)
        threshold = int(self.settings.get("alert_temp_c", 60))
        self.summary.set_text(f"{len(self.rows)} drive(s)  ·  {total_alerts} alert(s)  ·  temperature threshold {threshold} °C")
        history = self.settings.get("history", {})
        if not isinstance(history, dict):
            history = {}
        timestamp = GLib.DateTime.new_now_local().format("%Y-%m-%d %H:%M:%S")
        for item in self.rows:
            points = history.get(item.device, [])
            if not isinstance(points, list): points = []
            points.append({"ts": timestamp, "temp": item.temp_c, "health": item.health})
            history[item.device] = points[-200:]
        self.settings["history"] = history
        save_settings(self.settings)
        self._render_trends()
        if self.rows:
            self.disk_list.select_row(self.disk_list.get_row_at_index(0))
        else:
            self._set_text(self.details, "No drives found. Check that lsblk and smartmontools are installed.")
        if self.refresh_button:
            self.refresh_button.set_sensitive(True)
        self._set_status("Disk health refreshed")
        return GLib.SOURCE_REMOVE

    def _disk_selected(self, _list, row):
        if row is None: return
        index = int(row.get_name())
        if index >= len(self.rows): return
        data = self.rows[index]
        text = (
            f"Device: {data.device}\nModel: {data.model}\nProtocol: {data.protocol}\nSize: {data.size}\n"
            f"Health: {data.health}\nTemperature: {data.temp_c if data.temp_c is not None else 'N/A'} °C\n"
            f"Power-on hours: {data.power_on_hours if data.power_on_hours is not None else 'N/A'}\n"
            f"Alerts: {', '.join(data.alerts) if data.alerts else 'none'}\n\nRaw SMART output:\n{data.details}"
        )
        self._set_text(self.details, text)
        self._set_status(f"Selected {data.device}")

    def _render_trends(self):
        history = self.settings.get("history", {})
        lines = []
        if isinstance(history, dict):
            for device in sorted(history):
                lines.append(f"[{device}]")
                points = history.get(device, [])
                if isinstance(points, list):
                    for point in points[-60:]:
                        temp = point.get("temp")
                        temp = "N/A" if temp is None else f"{temp} °C"
                        lines.append(f"  {point.get('ts', '?')}  ·  {point.get('health', '?')}  ·  {temp}")
                lines.append("")
        self._set_text(self.trends, "\n".join(lines).strip() or "No history yet. Refresh drive health to begin collecting snapshots.")

    def run_full_smart(self, *_):
        row = self.disk_list.get_selected_row() if self.disk_list else None
        if row is None:
            self._set_status("Select a drive first")
            return
        device = self.rows[int(row.get_name())].device
        ok, message = launch_in_terminal(f"sudo smartctl -x {device} || sudo nvme smart-log {device}", title=f"SMART Report: {device}")
        self._set_status(message if ok else f"Could not open terminal: {message}")

    def _options_changed(self, *_):
        if self.refresh_spin: self.settings["refresh_interval_sec"] = int(self.refresh_spin.get_value())
        if self.alert_spin: self.settings["alert_temp_c"] = int(self.alert_spin.get_value())
        save_settings(self.settings)
        self._schedule_auto()

    def _auto_changed(self, _switch, state):
        self.settings["auto_refresh"] = bool(state)
        save_settings(self.settings)
        self._schedule_auto()
        return False

    def _schedule_auto(self):
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = 0
        if self.settings.get("auto_refresh", True):
            interval = max(30, int(self.settings.get("refresh_interval_sec", 60)))
            self.timer_id = GLib.timeout_add_seconds(interval, self._auto_refresh_tick)

    def _auto_refresh_tick(self):
        self.refresh_health()
        return GLib.SOURCE_CONTINUE


if __name__ == "__main__":
    sys.exit(DiskHealthGtk().run(sys.argv))
