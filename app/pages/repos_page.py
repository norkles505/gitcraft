from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# Datos de ejemplo: se reemplazan luego por la API de GitHub.
SAMPLE_REPOS = [
    ("gitcraft", "Privado", "Python", "hace 5 min"),
    ("mantenimiento-ordenes", "Privado", "TypeScript", "hace 2 días"),
    ("keyboardmovil", "Público", "C#", "hace 1 semana"),
    ("drawengine", "Público", "Python", "hace 2 semanas"),
    ("tribunal-digital", "Privado", "Python", "hace 1 mes"),
    ("el-sepulturero-juan", "Privado", "PHP", "hace 3 meses"),
]


class ReposPage(QWidget):
    new_repo_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        title = QLabel("Repositorios")
        title.setObjectName("pageTitle")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("pageSubtitle")
        titles.addWidget(title)
        titles.addWidget(self.subtitle)
        header.addLayout(titles, 1)
        new_button = QPushButton("Nuevo repositorio")
        new_button.setObjectName("primary")
        new_button.setCursor(Qt.CursorShape.PointingHandCursor)
        new_button.clicked.connect(self.new_repo_requested.emit)
        header.addWidget(new_button, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar repositorios...")
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Nombre", "Visibilidad", "Lenguaje", "Actualizado"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 3):
            header_view.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)

        for row in SAMPLE_REPOS:
            self._append_row(*row)
        self._update_subtitle()

    def _append_row(self, name: str, visibility: str, language: str, updated: str) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        for column, value in enumerate((name, visibility, language, updated)):
            self.table.setItem(row, column, QTableWidgetItem(value))

    def add_repo(self, name: str, visibility: str = "Privado") -> None:
        self.table.insertRow(0)
        for column, value in enumerate((name, visibility, "-", "ahora")):
            self.table.setItem(0, column, QTableWidgetItem(value))
        self._update_subtitle()

    def _filter(self, text: str) -> None:
        text = text.strip().lower()
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text().lower()
            self.table.setRowHidden(row, bool(text) and text not in name)

    def _update_subtitle(self) -> None:
        self.subtitle.setText(f"{self.table.rowCount()} repositorios (datos de ejemplo)")
