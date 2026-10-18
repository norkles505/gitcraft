from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.pages.activity_page import ActivityPage
from app.pages.new_repo_page import NewRepoPage
from app.pages.repos_page import ReposPage
from app.pages.settings_page import SettingsPage
from app.pages.sync_page import SyncPage


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("GitCraft")
        self.resize(1100, 780)
        self.setMinimumSize(900, 700)

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        # El orden de las páginas debe coincidir con el de NAV_ITEMS.
        self.repos_page = ReposPage()
        self.new_repo_page = NewRepoPage()
        self.sync_page = SyncPage()
        self.activity_page = ActivityPage()
        self.settings_page = SettingsPage()
        for page in (
            self.repos_page,
            self.new_repo_page,
            self.sync_page,
            self.activity_page,
            self.settings_page,
        ):
            self.stack.addWidget(page)

        self.repos_page.new_repo_requested.connect(lambda: self._go_to(1))
        self.new_repo_page.created.connect(self._on_repo_created)
        self.sync_page.repo_synced.connect(lambda msg: self.statusBar().showMessage(msg, 5000))
        self.settings_page.session_changed.connect(self._on_session_changed)

        self._go_to(0)
        self.statusBar().showMessage("Sin conexión a GitHub (modo demostración)")

    # ---------- barra lateral ----------
    NAV_ITEMS = ["Repositorios", "Nuevo repositorio", "Sincronizar", "Actividad", "Ajustes"]

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)
        box = QVBoxLayout(sidebar)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(0)

        logo = QLabel("GitCraft")
        logo.setObjectName("logo")
        box.addWidget(logo)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for index, text in enumerate(self.NAV_ITEMS):
            button = QPushButton(text)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked, i=index: self._go_to(i))
            self.nav_group.addButton(button, index)
            box.addWidget(button)

        box.addStretch(1)
        user = QLabel("Sin sesión iniciada")
        user.setObjectName("userLabel")
        self.user_label = user
        box.addWidget(user)
        return sidebar

    def _go_to(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        button = self.nav_group.button(index)
        if button is not None:
            button.setChecked(True)

    def _on_session_changed(self, user: str) -> None:
        if user:
            self.user_label.setText(f"@{user}")
            self.statusBar().showMessage(f"Sesión iniciada como {user}", 5000)
        else:
            self.user_label.setText("Sin sesión iniciada")

    def _on_repo_created(self, name: str) -> None:
        self.repos_page.add_repo(name)
        self.statusBar().showMessage(f"Repositorio '{name}' creado en GitHub", 8000)
