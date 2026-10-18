from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QVBoxLayout, QWidget

# Datos de ejemplo.
STATS = [("Commits (30 días)", "128"), ("Pull requests", "7"), ("Issues abiertos", "14")]
EVENTS = [
    "Commit en gitcraft: \"Agrega interfaz base\"",
    "Pull request #12 abierto en mantenimiento-ordenes",
    "Issue #5 cerrado en keyboardmovil",
    "Commit en drawengine: \"Corrige herramienta de borrador\"",
    "Release v1.2.0 publicado en tribunal-digital",
    "Rama feature/portal eliminada en el-sepulturero-juan",
]


class ActivityPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel("Actividad")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Resumen de tus proyectos (datos de ejemplo).")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        stats_row = QHBoxLayout()
        for label, value in STATS:
            stats_row.addWidget(self._stat_card(label, value))
        layout.addLayout(stats_row)

        recent = QLabel("Reciente")
        recent.setObjectName("sectionTitle")
        layout.addWidget(recent)

        events = QListWidget()
        events.addItems(EVENTS)
        layout.addWidget(events, 1)

    @staticmethod
    def _stat_card(label: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        box = QVBoxLayout(card)
        box.setContentsMargins(16, 14, 16, 14)
        number = QLabel(value)
        number.setStyleSheet("font-size: 26px; font-weight: 700;")
        caption = QLabel(label)
        caption.setObjectName("muted")
        box.addWidget(number)
        box.addWidget(caption)
        return card
