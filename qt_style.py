from __future__ import annotations

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication


THEMES = {
    "dark": {
        "window": "#1f2326",
        "surface": "#15191c",
        "panel": "#111518",
        "sidebar": "#121619",
        "border": "#343a40",
        "text": "#f0f2f4",
        "muted": "#a8b0b8",
        "accent": "#d90404",
        "accent_hover": "#ef2424",
        "selection": "#2f6fdb",
        "input": "#101417",
    },
    "light": {
        "window": "#eef1f4",
        "surface": "#ffffff",
        "panel": "#f7f8fa",
        "sidebar": "#e7ebef",
        "border": "#cbd2da",
        "text": "#1d2329",
        "muted": "#64707c",
        "accent": "#d90404",
        "accent_hover": "#bd0303",
        "selection": "#2f6fdb",
        "input": "#ffffff",
    },
    "nord": {
        "window": "#242933", "surface": "#2e3440", "panel": "#303846", "sidebar": "#202630",
        "border": "#454e5e", "text": "#eceff4", "muted": "#aab4c4", "accent": "#88c0d0",
        "accent_hover": "#9bd2e2", "selection": "#455c73", "input": "#252c37",
    },
    "sunset": {
        "window": "#241b24", "surface": "#30232e", "panel": "#392832", "sidebar": "#1e1720",
        "border": "#59404b", "text": "#fff0e8", "muted": "#c7a9a1", "accent": "#ff8a5b",
        "accent_hover": "#ffa078", "selection": "#70464b", "input": "#241c25",
    },
    "forest": {
        "window": "#19231f", "surface": "#202e28", "panel": "#26372f", "sidebar": "#151e1a",
        "border": "#3d5548", "text": "#e8f2e9", "muted": "#a6bdab", "accent": "#75c69a",
        "accent_hover": "#8bd9ae", "selection": "#365b49", "input": "#1b2821",
    },
}


def apply_qt_theme(app: QApplication, theme_name: str):
    theme = THEMES.get(theme_name, THEMES["dark"])
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, theme["window"])
    palette.setColor(QPalette.ColorRole.WindowText, theme["text"])
    palette.setColor(QPalette.ColorRole.Base, theme["input"])
    palette.setColor(QPalette.ColorRole.AlternateBase, theme["panel"])
    palette.setColor(QPalette.ColorRole.Text, theme["text"])
    palette.setColor(QPalette.ColorRole.Button, theme["panel"])
    palette.setColor(QPalette.ColorRole.ButtonText, theme["text"])
    palette.setColor(QPalette.ColorRole.Highlight, theme["selection"])
    palette.setColor(QPalette.ColorRole.HighlightedText, "#ffffff")
    app.setPalette(palette)
    app.setStyle("Fusion")
    app.setStyleSheet(_stylesheet(theme))


def _stylesheet(theme: dict[str, str]) -> str:
    return f"""
QWidget#appRoot {{
    background: {theme["window"]};
    color: {theme["text"]};
    font-size: 14px;
}}

QFrame#sidebar {{
    background: {theme["sidebar"]};
    border-right: 1px solid {theme["border"]};
}}

QFrame#sidebarLine {{
    color: {theme["border"]};
    background: {theme["border"]};
    max-height: 1px;
}}

QWidget#content {{
    background: {theme["window"]};
}}

QLabel#brandTitle {{
    color: {theme["text"]};
    font-size: 20px;
    font-weight: 600;
    padding: 2px 4px 8px 4px;
}}

QLabel#pageTitle {{
    color: {theme["text"]};
    font-size: 28px;
    font-weight: 700;
}}

QLabel#sectionTitle {{
    color: {theme["text"]};
    font-size: 15px;
    font-weight: 700;
}}

QLabel#mutedText,
QLabel#sidebarLabel,
QLabel#statusLabel,
QLabel#summaryLabel {{
    color: {theme["muted"]};
}}

QFrame#panel {{
    background: {theme["panel"]};
    border: 1px solid {theme["border"]};
    border-radius: 12px;
}}

QSpinBox,
QComboBox,
QTextEdit {{
    background: {theme["input"]};
    color: {theme["text"]};
    border: 1px solid {theme["border"]};
    border-radius: 8px;
    min-height: 36px;
    padding: 5px 10px;
}}

QTextEdit#textView {{
    font-family: "JetBrains Mono", "Cascadia Mono", "Consolas", monospace;
    font-size: 13px;
}}

QSpinBox:focus,
QComboBox:focus,
QTextEdit:focus {{
    border-color: {theme["selection"]};
}}

QCheckBox {{
    color: {theme["text"]};
    spacing: 7px;
}}

QPushButton {{
    background: {theme["panel"]};
    color: {theme["text"]};
    border: 1px solid {theme["border"]};
    border-radius: 8px;
    min-height: 36px;
    padding: 6px 14px;
    font-weight: 600;
}}

QPushButton:hover {{
    border-color: {theme["muted"]};
}}

QPushButton[primary="true"] {{
    background: {theme["accent"]};
    border-color: {theme["accent"]};
    color: #ffffff;
    font-weight: 600;
}}

QPushButton[primary="true"]:hover {{
    background: {theme["accent_hover"]};
    border-color: {theme["accent_hover"]};
}}

QPushButton#navButton {{
    text-align: left;
    background: transparent;
    border: 0;
    border-radius: 8px;
    padding: 9px 12px;
}}

QPushButton#navButton:hover {{
    background: {theme["panel"]};
}}

QPushButton#navButton:checked {{
    background: {theme["accent"]};
    color: #ffffff;
    font-weight: 600;
}}

QListWidget#resultList {{
    background: transparent;
    color: {theme["text"]};
    border: 0;
    outline: 0;
    padding: 6px;
}}

QListWidget#resultList::item {{
    background: {theme["surface"]};
    border: 1px solid {theme["border"]};
    border-radius: 10px;
    padding: 10px;
    margin: 3px 0;
}}

QListWidget#resultList::item:selected {{
    background: {theme["selection"]};
    color: #ffffff;
}}

QSplitter::handle {{
    background: {theme["window"]};
    height: 8px;
}}

QLabel#eyebrow {{
    color: {theme["accent"]};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}}

QLabel#diskTitle {{ color: {theme["text"]}; font-size: 14px; font-weight: 700; }}
QLabel#diskMeta {{ color: {theme["muted"]}; font-size: 12px; }}
QLabel#healthBadge {{ color: {theme["accent"]}; font-weight: 700; }}
QTextEdit#textView {{ border-radius: 8px; }}

QFrame#diskRow {{
    background: {theme["surface"]};
    border: 1px solid {theme["border"]};
    border-radius: 9px;
}}

QFrame#diskRow[selected="true"] {{ border-color: {theme["accent"]}; }}

QLabel#summaryLabel {{
    font-size: 13px;
    font-weight: 600;
    padding: 3px 2px;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: {theme["border"]};
    border-radius: 5px;
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""
