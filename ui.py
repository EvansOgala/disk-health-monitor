import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from disk_ops import launch_in_terminal, read_all_disk_health
from settings import load_settings, save_settings

THEMES = {
    "dark": {
        "root": "#0f172a",
        "panel": "#111827",
        "card": "#0b1220",
        "line": "#1f2937",
        "text": "#e2e8f0",
        "muted": "#94a3b8",
        "entry": "#020617",
        "entry_fg": "#dbeafe",
        "accent": "#2563eb",
        "accent_hover": "#3b82f6",
        "accent_press": "#1d4ed8",
        "accent_text": "#eff6ff",
        "select": "#2563eb",
        "warn": "#f87171",
    },
    "light": {
        "root": "#f1f5f9",
        "panel": "#ffffff",
        "card": "#f8fafc",
        "line": "#dbe3ee",
        "text": "#0f172a",
        "muted": "#475569",
        "entry": "#ffffff",
        "entry_fg": "#0f172a",
        "accent": "#2563eb",
        "accent_hover": "#3b82f6",
        "accent_press": "#1d4ed8",
        "accent_text": "#eff6ff",
        "select": "#93c5fd",
        "warn": "#dc2626",
    },
}


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, width=120, height=34, radius=14):
        super().__init__(parent, width=width, height=height, bd=0, highlightthickness=0, relief="flat", cursor="hand2")
        self.command = command
        self.text = text
        self.width = width
        self.height = height
        self.radius = radius
        self.pressed = False
        self.enabled = True
        self.colors = {
            "bg": "#2563eb",
            "hover": "#3b82f6",
            "press": "#1d4ed8",
            "fg": "#eff6ff",
            "container": "#0f172a",
            "disabled": "#475569",
        }
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self._draw()

    def configure_theme(self, palette, container_bg):
        self.colors.update(
            {
                "bg": palette["accent"],
                "hover": palette["accent_hover"],
                "press": palette["accent_press"],
                "fg": palette["accent_text"],
                "container": container_bg,
            }
        )
        self._draw()

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self._draw()

    def _rounded(self, color):
        w, h, r = self.width, self.height, self.radius
        self.create_arc(0, 0, 2 * r, 2 * r, start=90, extent=90, fill=color, outline=color)
        self.create_arc(w - 2 * r, 0, w, 2 * r, start=0, extent=90, fill=color, outline=color)
        self.create_arc(0, h - 2 * r, 2 * r, h, start=180, extent=90, fill=color, outline=color)
        self.create_arc(w - 2 * r, h - 2 * r, w, h, start=270, extent=90, fill=color, outline=color)
        self.create_rectangle(r, 0, w - r, h, fill=color, outline=color)
        self.create_rectangle(0, r, w, h - r, fill=color, outline=color)

    def _draw(self):
        self.delete("all")
        self.configure(bg=self.colors["container"])
        color = self.colors["disabled"] if not self.enabled else (self.colors["press"] if self.pressed else self.colors["bg"])
        self._rounded(color)
        self.create_text(self.width // 2, self.height // 2, text=self.text, fill=self.colors["fg"], font=("Adwaita Sans", 10, "bold"))

    def _on_enter(self, _event):
        if self.enabled and not self.pressed:
            self.delete("all")
            self.configure(bg=self.colors["container"])
            self._rounded(self.colors["hover"])
            self.create_text(self.width // 2, self.height // 2, text=self.text, fill=self.colors["fg"], font=("Adwaita Sans", 10, "bold"))

    def _on_leave(self, _event):
        self.pressed = False
        self._draw()

    def _on_press(self, _event):
        if not self.enabled:
            return
        self.pressed = True
        self._draw()

    def _on_release(self, _event):
        if not self.enabled:
            return
        run = self.pressed
        self.pressed = False
        self._draw()
        if run:
            self.command()


class DiskHealthApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Disk Health Monitor")
        self.root.geometry("1240x820")
        self.root.minsize(1020, 680)

        self.settings = load_settings()
        self.theme_var = tk.StringVar(value=self.settings.get("theme", "dark"))
        self.refresh_var = tk.IntVar(value=int(self.settings.get("refresh_interval_sec", 60)))
        self.alert_temp_var = tk.IntVar(value=int(self.settings.get("alert_temp_c", 60)))
        self.auto_refresh_var = tk.BooleanVar(value=bool(self.settings.get("auto_refresh", True)))

        self.last_rows = []
        self.round_buttons: list[RoundedButton] = []
        self.auto_job = None

        self._build_ui()
        self.apply_theme(self.theme_var.get())
        self.refresh_health()
        self._schedule_auto()

    def _btn(self, b: RoundedButton):
        self.round_buttons.append(b)
        return b

    def _build_ui(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self.header = tk.Frame(self.root, padx=14, pady=12)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.columnconfigure(1, weight=1)

        self.title = tk.Label(self.header, text="Disk Health Monitor", font=("Adwaita Sans", 24, "bold"))
        self.title.grid(row=0, column=0, sticky="w")

        self.subtitle = tk.Label(
            self.header,
            text="SMART/NVMe status, temperature trends, and alerting",
            font=("Adwaita Sans", 10),
        )
        self.subtitle.grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.theme_box = ttk.Combobox(self.header, textvariable=self.theme_var, values=("dark", "light"), state="readonly", width=10, style="App.TCombobox")
        self.theme_box.grid(row=0, column=2, rowspan=2, sticky="e")
        self.theme_box.bind("<<ComboboxSelected>>", lambda _e: self.apply_theme(self.theme_var.get()))

        self.tabs = ttk.Notebook(self.root)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 12))

        self._build_health_tab()
        self._build_trends_tab()

        self.status_var = tk.StringVar(value="Ready")
        self.status = tk.Label(self.root, textvariable=self.status_var, anchor="w", padx=14, pady=8, font=("Adwaita Sans", 10))
        self.status.grid(row=2, column=0, sticky="ew")

    def _build_health_tab(self):
        tab = tk.Frame(self.tabs)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)
        tab.rowconfigure(3, weight=1)
        self.tabs.add(tab, text="Health")
        self.tab_health = tab

        controls = tk.Frame(tab, padx=12, pady=10)
        controls.grid(row=0, column=0, sticky="ew")
        self.controls = controls

        self.btn_refresh = self._btn(RoundedButton(controls, "Refresh", self.refresh_health, width=92))
        self.btn_refresh.pack(side="left")

        self.btn_smart = self._btn(RoundedButton(controls, "Full SMART", self.run_full_smart, width=112))
        self.btn_smart.pack(side="left", padx=(8, 12))

        self.lbl_interval = tk.Label(controls, text="Refresh(s)", font=("Adwaita Sans", 10, "bold"))
        self.lbl_interval.pack(side="left")
        self.spin_interval = ttk.Spinbox(controls, from_=30, to=1800, increment=10, textvariable=self.refresh_var, width=7, style="App.TSpinbox", command=self._save_options)
        self.spin_interval.pack(side="left", padx=(6, 10))
        self.spin_interval.bind("<Return>", lambda _e: self._save_options())

        self.lbl_alert = tk.Label(controls, text="Temp Alert(C)", font=("Adwaita Sans", 10, "bold"))
        self.lbl_alert.pack(side="left")
        self.spin_alert = ttk.Spinbox(controls, from_=30, to=100, increment=1, textvariable=self.alert_temp_var, width=6, style="App.TSpinbox", command=self._save_options)
        self.spin_alert.pack(side="left", padx=(6, 10))
        self.spin_alert.bind("<Return>", lambda _e: self._save_options())

        self.chk_auto = tk.Checkbutton(controls, text="Auto refresh", variable=self.auto_refresh_var, onvalue=True, offvalue=False, font=("Adwaita Sans", 10), command=self._save_options)
        self.chk_auto.pack(side="left")

        self.summary = tk.Label(tab, text="", font=("Adwaita Sans", 10), anchor="w", padx=12)
        self.summary.grid(row=1, column=0, sticky="ew")

        tree_wrap = tk.Frame(tab, padx=12, pady=6)
        tree_wrap.grid(row=2, column=0, sticky="nsew")
        tree_wrap.columnconfigure(0, weight=1)
        tree_wrap.rowconfigure(0, weight=1)
        self.tree_wrap = tree_wrap

        self.disk_tree = ttk.Treeview(
            tree_wrap,
            columns=("device", "model", "protocol", "size", "health", "temp", "poh", "alerts"),
            show="headings",
            style="App.Treeview",
        )
        for col, title, width in (
            ("device", "Device", 130),
            ("model", "Model", 220),
            ("protocol", "Protocol", 110),
            ("size", "Size", 90),
            ("health", "Health", 90),
            ("temp", "Temp C", 80),
            ("poh", "PowerOnHours", 130),
            ("alerts", "Alerts", 190),
        ):
            self.disk_tree.heading(col, text=title)
            self.disk_tree.column(col, width=width, anchor="w")
        self.disk_tree.grid(row=0, column=0, sticky="nsew")
        self.disk_tree.bind("<<TreeviewSelect>>", lambda _e: self._show_selected_details())

        s1 = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.disk_tree.yview)
        self.disk_tree.configure(yscrollcommand=s1.set)
        s1.grid(row=0, column=1, sticky="ns")

        details = tk.LabelFrame(tab, text="Disk Details", padx=8, pady=8)
        details.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 8))
        details.columnconfigure(0, weight=1)
        details.rowconfigure(0, weight=1)
        self.details_frame = details

        self.details_text = tk.Text(details, wrap="word", font=("Adwaita Mono", 10), state="disabled")
        self.details_text.grid(row=0, column=0, sticky="nsew")
        s2 = ttk.Scrollbar(details, orient="vertical", command=self.details_text.yview)
        self.details_text.configure(yscrollcommand=s2.set)
        s2.grid(row=0, column=1, sticky="ns")

    def _build_trends_tab(self):
        tab = tk.Frame(self.tabs)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)
        self.tabs.add(tab, text="Trends")
        self.tab_trends = tab

        frame = tk.LabelFrame(tab, text="Temperature and Health Trend Summary", padx=8, pady=8)
        frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=10)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        self.trend_frame = frame

        self.trend_text = tk.Text(frame, wrap="word", font=("Adwaita Mono", 10), state="disabled")
        self.trend_text.grid(row=0, column=0, sticky="nsew")
        s3 = ttk.Scrollbar(frame, orient="vertical", command=self.trend_text.yview)
        self.trend_text.configure(yscrollcommand=s3.set)
        s3.grid(row=0, column=1, sticky="ns")

    def _set_text(self, widget: tk.Text, text: str):
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _save_options(self):
        try:
            interval = int(self.refresh_var.get())
        except Exception:  # noqa: BLE001
            interval = 60
        interval = max(30, min(1800, interval))
        self.refresh_var.set(interval)

        try:
            temp = int(self.alert_temp_var.get())
        except Exception:  # noqa: BLE001
            temp = 60
        temp = max(30, min(100, temp))
        self.alert_temp_var.set(temp)

        self.settings["refresh_interval_sec"] = interval
        self.settings["alert_temp_c"] = temp
        self.settings["auto_refresh"] = bool(self.auto_refresh_var.get())
        save_settings(self.settings)

        self._schedule_auto()

    def _schedule_auto(self):
        if self.auto_job is not None:
            self.root.after_cancel(self.auto_job)
            self.auto_job = None

        if not self.auto_refresh_var.get():
            return

        delay = int(self.refresh_var.get()) * 1000

        def tick():
            if self.auto_refresh_var.get():
                self.refresh_health(set_status=False)
            self._schedule_auto()

        self.auto_job = self.root.after(delay, tick)

    def refresh_health(self, set_status: bool = True):
        self._save_options()
        alert_temp = int(self.alert_temp_var.get())
        if set_status:
            self.status_var.set("Reading disk health...")

        def task():
            rows = read_all_disk_health(alert_temp_c=alert_temp)
            self.root.after(0, lambda: self._render_health(rows, set_status))

        threading.Thread(target=task, daemon=True).start()

    def _render_health(self, rows, set_status: bool):
        self.last_rows = rows
        selected_device = self._selected_device()

        for item in self.disk_tree.get_children():
            self.disk_tree.delete(item)

        total_alerts = 0
        for idx, row in enumerate(rows):
            total_alerts += len(row.alerts)
            temp_s = str(row.temp_c) if row.temp_c is not None else "-"
            poh_s = str(row.power_on_hours) if row.power_on_hours is not None else "-"
            alert_s = ", ".join(row.alerts) if row.alerts else "-"

            tags = ("warn",) if row.alerts else ()
            self.disk_tree.insert(
                "",
                "end",
                iid=f"disk-{idx}",
                values=(row.device, row.model, row.protocol, row.size, row.health, temp_s, poh_s, alert_s),
                tags=tags,
            )

        self.summary.configure(text=f"Disks: {len(rows)} | Alerts: {total_alerts} | Temp alert threshold: {self.alert_temp_var.get()} C")
        self.disk_tree.tag_configure("warn", foreground=THEMES[self.theme_var.get()]["warn"])

        if selected_device:
            for item in self.disk_tree.get_children():
                values = self.disk_tree.item(item, "values")
                if values and values[0] == selected_device:
                    self.disk_tree.selection_set(item)
                    self.disk_tree.focus(item)
                    break

        self._show_selected_details()
        self._update_history(rows)
        self._render_trends()

        if set_status:
            self.status_var.set("Disk health updated")

    def _selected_device(self) -> str:
        selected = self.disk_tree.selection()
        if not selected:
            return ""
        values = self.disk_tree.item(selected[0], "values")
        return str(values[0]) if values else ""

    def _show_selected_details(self):
        device = self._selected_device()
        if not device:
            self._set_text(self.details_text, "Select a disk to see details.")
            return

        for row in self.last_rows:
            if row.device == device:
                detail = row.details or "No details available."
                self._set_text(self.details_text, detail)
                return

        self._set_text(self.details_text, "No details available.")

    def _update_history(self, rows):
        history = self.settings.setdefault("history", {})
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for row in rows:
            records = history.setdefault(row.device, [])
            records.append(
                {
                    "timestamp": now,
                    "temp_c": row.temp_c,
                    "health": row.health,
                    "alerts": row.alerts,
                }
            )
            history[row.device] = records[-500:]

        self.settings["history"] = history
        save_settings(self.settings)

    def _render_trends(self):
        history = self.settings.get("history", {})
        if not history:
            self._set_text(self.trend_text, "No history yet. Refresh health to collect snapshots.")
            return

        lines = []
        for device in sorted(history.keys()):
            recs = history.get(device, [])
            if not recs:
                continue
            temps = [r.get("temp_c") for r in recs if isinstance(r.get("temp_c"), int)]
            latest = recs[-1]
            latest_temp = latest.get("temp_c")
            latest_health = latest.get("health", "Unknown")
            latest_alerts = ", ".join(latest.get("alerts", [])) if latest.get("alerts") else "-"
            lines.append(f"[{device}]")
            lines.append(f"Snapshots: {len(recs)}")
            lines.append(f"Latest: {latest.get('timestamp', '-')} | Health={latest_health} | Temp={latest_temp if latest_temp is not None else '-'} C | Alerts={latest_alerts}")
            if temps:
                lines.append(f"Temp min/max/avg: {min(temps)} / {max(temps)} / {sum(temps)/len(temps):.1f} C")
            else:
                lines.append("Temp min/max/avg: n/a")
            lines.append("-" * 72)

        self._set_text(self.trend_text, "\n".join(lines) if lines else "No trend entries yet.")

    def run_full_smart(self):
        device = self._selected_device()
        if not device:
            messagebox.showinfo("Full SMART", "Select a disk first.")
            return

        ok, msg = launch_in_terminal(f"sudo smartctl -x {device}", title=f"SMART Report {device}")
        if ok:
            self.status_var.set(msg)
            return

        self.status_var.set("Failed to launch SMART terminal")
        messagebox.showerror("Terminal Launch Failed", msg)

    def apply_theme(self, theme_name: str):
        if theme_name not in THEMES:
            theme_name = "dark"
        self.theme_var.set(theme_name)

        self.settings["theme"] = theme_name
        save_settings(self.settings)

        p = THEMES[theme_name]

        self.style.configure("App.TCombobox", fieldbackground=p["entry"], foreground=p["entry_fg"], bordercolor=p["line"], padding=4, font=("Adwaita Sans", 10))
        self.style.map("App.TCombobox", fieldbackground=[("readonly", p["entry"])], foreground=[("readonly", p["entry_fg"])])
        self.style.configure("App.TSpinbox", fieldbackground=p["entry"], foreground=p["entry_fg"], bordercolor=p["line"], padding=4, font=("Adwaita Sans", 10))
        self.style.configure("App.Treeview", background=p["card"], fieldbackground=p["card"], foreground=p["text"], rowheight=28, borderwidth=0, font=("Adwaita Sans", 10))
        self.style.map("App.Treeview", background=[("selected", p["select"])], foreground=[("selected", p["text"])])

        self.root.configure(bg=p["root"])
        self.header.configure(bg=p["root"])
        self.title.configure(bg=p["root"], fg=p["text"])
        self.subtitle.configure(bg=p["root"], fg=p["muted"])
        self.status.configure(bg=p["root"], fg=p["muted"])

        self.tab_health.configure(bg=p["panel"])
        self.controls.configure(bg=p["panel"])
        self.lbl_interval.configure(bg=p["panel"], fg=p["text"])
        self.lbl_alert.configure(bg=p["panel"], fg=p["text"])
        self.chk_auto.configure(bg=p["panel"], fg=p["text"], selectcolor=p["panel"], activebackground=p["panel"], activeforeground=p["text"])
        self.summary.configure(bg=p["panel"], fg=p["muted"])
        self.tree_wrap.configure(bg=p["panel"])
        self.details_frame.configure(bg=p["panel"], fg=p["text"])
        self.details_text.configure(bg=p["card"], fg=p["text"], insertbackground=p["text"])

        self.tab_trends.configure(bg=p["panel"])
        self.trend_frame.configure(bg=p["panel"], fg=p["text"])
        self.trend_text.configure(bg=p["card"], fg=p["text"], insertbackground=p["text"])

        for b in self.round_buttons:
            b.configure_theme(p, b.master.cget("bg"))
