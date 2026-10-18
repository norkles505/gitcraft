"""Tema oscuro de GitCraft (colores en un solo lugar para cambiarlos fácil)."""

COLORS = {
    "bg": "#0d1117",
    "panel": "#161b22",
    "border": "#30363d",
    "text": "#e6edf3",
    "muted": "#8b949e",
    "accent": "#2f81f7",
    "accent_hover": "#4493f8",
    "green": "#238636",
    "green_hover": "#2ea043",
    "danger": "#f85149",
    "row_hover": "#1c2128",
}

STYLESHEET = f"""
* {{
    font-family: "Inter", "Segoe UI", "Ubuntu", sans-serif;
    font-size: 13px;
    color: {COLORS["text"]};
}}
QMainWindow, QWidget#root, QStackedWidget, QWidget#page {{
    background: {COLORS["bg"]};
}}

/* Barra lateral */
QFrame#sidebar {{
    background: {COLORS["panel"]};
    border-right: 1px solid {COLORS["border"]};
}}
QLabel#logo {{
    font-size: 18px;
    font-weight: 700;
    padding: 18px 16px 12px 16px;
}}
QLabel#userLabel {{
    color: {COLORS["muted"]};
    padding: 10px 16px 16px 16px;
}}
QPushButton#navButton {{
    background: transparent;
    border: none;
    border-radius: 6px;
    text-align: left;
    padding: 9px 12px;
    margin: 2px 10px;
    color: {COLORS["muted"]};
}}
QPushButton#navButton:hover {{
    background: {COLORS["row_hover"]};
    color: {COLORS["text"]};
}}
QPushButton#navButton:checked {{
    background: {COLORS["border"]};
    color: {COLORS["text"]};
    font-weight: 600;
}}

/* Títulos */
QLabel#pageTitle {{
    font-size: 22px;
    font-weight: 700;
}}
QLabel#pageSubtitle, QLabel#muted {{
    color: {COLORS["muted"]};
}}
QLabel#sectionTitle {{
    font-weight: 600;
    font-size: 14px;
}}

/* Campos */
QLineEdit, QTextEdit, QComboBox, QPlainTextEdit {{
    background: {COLORS["bg"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    padding: 7px 10px;
    selection-background-color: {COLORS["accent"]};
}}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
    border: 1px solid {COLORS["accent"]};
}}
QComboBox QAbstractItemView {{
    background: {COLORS["panel"]};
    border: 1px solid {COLORS["border"]};
    selection-background-color: {COLORS["accent"]};
}}
QCheckBox, QRadioButton {{
    spacing: 8px;
}}

/* Botones */
QPushButton {{
    background: {COLORS["panel"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    padding: 7px 14px;
}}
QPushButton:hover {{
    background: {COLORS["row_hover"]};
    border-color: {COLORS["muted"]};
}}
QPushButton#primary {{
    background: {COLORS["green"]};
    border: 1px solid rgba(240,246,252,0.1);
    color: white;
    font-weight: 600;
}}
QPushButton#primary:hover {{
    background: {COLORS["green_hover"]};
}}
QPushButton#danger {{
    color: {COLORS["danger"]};
}}

/* Tarjetas */
QFrame#card {{
    background: {COLORS["panel"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
}}
QFrame#card QLabel {{
    background: transparent;
}}

/* Tabla / listas */
QTableWidget, QListWidget {{
    background: {COLORS["panel"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    gridline-color: {COLORS["border"]};
    outline: 0;
}}
QTableWidget::item, QListWidget::item {{
    padding: 8px;
    border-bottom: 1px solid {COLORS["border"]};
}}
QTableWidget::item:selected, QListWidget::item:selected {{
    background: {COLORS["row_hover"]};
}}
QHeaderView::section {{
    background: {COLORS["bg"]};
    color: {COLORS["muted"]};
    border: none;
    border-bottom: 1px solid {COLORS["border"]};
    padding: 8px;
    font-weight: 600;
}}

/* Scroll */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS["border"]};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0;
}}
QStatusBar {{
    background: {COLORS["panel"]};
    color: {COLORS["muted"]};
    border-top: 1px solid {COLORS["border"]};
}}
"""
