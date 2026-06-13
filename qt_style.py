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
    font-size: 22px;
    font-weight: 500;
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
    border-radius: 6px;
}}

QSpinBox,
QComboBox,
QTextEdit {{
    background: {theme["input"]};
    color: {theme["text"]};
    border: 1px solid {theme["border"]};
    border-radius: 5px;
    min-height: 32px;
    padding: 4px 9px;
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
    border-radius: 5px;
    min-height: 32px;
    padding: 5px 12px;
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
    border-radius: 5px;
    padding: 7px 10px;
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
    background: {theme["surface"]};
    color: {theme["text"]};
    border: 1px solid {theme["border"]};
    border-radius: 5px;
    outline: 0;
    padding: 6px;
}}

QListWidget#resultList::item {{
    border-radius: 5px;
    padding: 8px;
}}

QListWidget#resultList::item:selected {{
    background: {theme["selection"]};
    color: #ffffff;
}}

QSplitter::handle {{
    background: {theme["window"]};
    height: 8px;
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
