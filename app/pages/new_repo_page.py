from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from app import git_ops
from app.workers import Worker

GITIGNORES = ["Ninguno", "Python", "Node", "Android", "Laravel", "Unity"]
LICENSES = ["Ninguna", "MIT", "Apache 2.0", "GPL v3"]


class NewRepoPage(QWidget):
    created = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        self._worker: Worker | None = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(14)

        title = QLabel("Nuevo repositorio")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Crea el repositorio en GitHub y súbelo desde tu carpeta local.")
        subtitle.setObjectName("pageSubtitle")
        outer.addWidget(title)
        outer.addWidget(subtitle)

        card = QFrame()
        card.setObjectName("card")
        card.setMaximumWidth(640)
        form = QVBoxLayout(card)
        form.setContentsMargins(20, 18, 20, 18)
        form.setSpacing(10)

        form.addWidget(self._label("Nombre del repositorio"))
        self.name = QLineEdit()
        self.name.setPlaceholderText("mi-proyecto")
        form.addWidget(self.name)

        form.addWidget(self._label("Descripción (opcional)"))
        self.description = QLineEdit()
        form.addWidget(self.description)

        form.addWidget(self._label("Carpeta local"))
        folder_row = QHBoxLayout()
        self.folder = QLineEdit()
        self.folder.setPlaceholderText("/home/usuario/proyectos/mi-proyecto")
        browse = QPushButton("Examinar...")
        browse.clicked.connect(self._browse)
        folder_row.addWidget(self.folder, 1)
        folder_row.addWidget(browse)
        form.addLayout(folder_row)

        form.addWidget(self._label("Visibilidad"))
        vis_row = QHBoxLayout()
        self.private_radio = QRadioButton("Privado")
        self.private_radio.setChecked(True)
        self.public_radio = QRadioButton("Público")
        vis_row.addWidget(self.private_radio)
        vis_row.addWidget(self.public_radio)
        vis_row.addStretch(1)
        form.addLayout(vis_row)

        extras = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(self._label(".gitignore"))
        self.gitignore = QComboBox()
        self.gitignore.addItems(GITIGNORES)
        left.addWidget(self.gitignore)
        right = QVBoxLayout()
        right.addWidget(self._label("Licencia"))
        self.license = QComboBox()
        self.license.addItems(LICENSES)
        right.addWidget(self.license)
        extras.addLayout(left, 1)
        extras.addLayout(right, 1)
        form.addLayout(extras)

        self.readme = QCheckBox("Agregar README.md")
        self.readme.setChecked(True)
        self.push = QCheckBox("Hacer el primer commit y push")
        self.push.setChecked(True)
        form.addWidget(self.readme)
        form.addWidget(self.push)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        clear = QPushButton("Limpiar")
        clear.clicked.connect(self._clear)
        create = QPushButton("Crear repositorio")
        create.setObjectName("primary")
        create.setCursor(Qt.CursorShape.PointingHandCursor)
        create.clicked.connect(self._submit)
        self.create_btn = create
        self.clear_btn = clear
        buttons.addWidget(clear)
        buttons.addWidget(create)
        form.addSpacing(6)
        form.addLayout(buttons)

        outer.addWidget(card)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumWidth(640)
        self.log.setMaximumHeight(140)
        self.log.setPlaceholderText("El resultado aparecerá aquí.")
        self.log.setStyleSheet('font-family: "DejaVu Sans Mono", "Monospace"; font-size: 12px;')
        outer.addWidget(self.log)
        outer.addStretch(1)

    @staticmethod
    def _label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    def _browse(self) -> None:
        from PyQt6.QtWidgets import QFileDialog

        path = QFileDialog.getExistingDirectory(self, "Elegir carpeta del proyecto")
        if path:
            self.folder.setText(path)

    def _clear(self) -> None:
        self.name.clear()
        self.description.clear()
        self.folder.clear()
        self.private_radio.setChecked(True)
        self.gitignore.setCurrentIndex(0)
        self.license.setCurrentIndex(0)
        self.readme.setChecked(True)
        self.push.setChecked(True)

    def _submit(self) -> None:
        if self._worker is not None:
            return
        name = self.name.text().strip()
        if not name or " " in name:
            QMessageBox.warning(
                self, "Nombre inválido", "Escribe un nombre sin espacios (usa guiones)."
            )
            return
        folder = self.folder.text().strip()
        if not folder:
            QMessageBox.warning(self, "Falta la carpeta", "Elige la carpeta local del proyecto.")
            return

        private = self.private_radio.isChecked()
        push = self.push.isChecked()
        text = f"Se creará el repositorio '{name}' ({'privado' if private else 'público'}) en tu cuenta de GitHub."
        if push:
            text += f"\n\nSe subirán todos los archivos de:\n{folder}"
            if not private:
                text += "\n\nSerá público: revisa que la carpeta no tenga contraseñas, claves ni archivos .env."
        answer = QMessageBox.question(
            self,
            "Crear repositorio",
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        worker = Worker(
            git_ops.create_repo,
            folder,
            name,
            self.description.text(),
            private,
            self.gitignore.currentText(),
            self.license.currentText(),
            self.readme.isChecked(),
            push,
            parent=self,
        )
        worker.finished.connect(worker.deleteLater)
        worker.done.connect(lambda result: self._on_done(name, result))
        self._worker = worker
        self._set_busy(True)
        self.log.setPlainText("Creando el repositorio en GitHub...")
        worker.start()

    def _on_done(self, name: str, result: git_ops.Result) -> None:
        self._worker = None
        self._set_busy(False)
        self.log.setPlainText(result.output or ("Listo." if result.ok else "Falló sin detalles."))
        if result.ok:
            self.created.emit(name)
            self._clear()

    def _set_busy(self, busy: bool) -> None:
        self.create_btn.setEnabled(not busy)
        self.clear_btn.setEnabled(not busy)
        self.create_btn.setText("Creando..." if busy else "Crear repositorio")
