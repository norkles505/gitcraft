from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app import git_ops
from app.workers import Worker

MAX_RECIENTES = 10


class SyncPage(QWidget):
    repo_synced = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        self._settings = QSettings("GitCraft", "GitCraft")
        self._worker: Worker | None = None
        self._repo_ok = False
        self._changes = 0
        self._remotes: list[git_ops.Remote] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(14)

        title = QLabel("Sincronizar")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Sube tus cambios a GitHub o baja las actualizaciones de un repositorio.")
        subtitle.setObjectName("pageSubtitle")
        outer.addWidget(title)
        outer.addWidget(subtitle)

        # --- carpeta ---
        folder_card = QFrame()
        folder_card.setObjectName("card")
        fbox = QVBoxLayout(folder_card)
        fbox.setContentsMargins(16, 14, 16, 14)
        fbox.setSpacing(8)
        fbox.addWidget(self._section("Carpeta del repositorio"))
        row = QHBoxLayout()
        self.folder = QComboBox()
        self.folder.setEditable(True)
        self.folder.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.folder.lineEdit().setPlaceholderText("/home/usuario/proyectos/mi-repo")
        self.folder.lineEdit().returnPressed.connect(self._refresh)
        self.folder.activated.connect(lambda _index: self._refresh())
        self.browse_btn = QPushButton("Examinar...")
        self.browse_btn.clicked.connect(self._browse)
        self.check_btn = QPushButton("Revisar estado")
        self.check_btn.clicked.connect(self._refresh)
        row.addWidget(self.folder, 1)
        row.addWidget(self.browse_btn)
        row.addWidget(self.check_btn)
        fbox.addLayout(row)
        self.info = QLabel("Elige una carpeta para ver su estado.")
        self.info.setObjectName("muted")
        self.info.setWordWrap(True)
        fbox.addWidget(self.info)
        fbox.addWidget(self._section("Remoto vinculado"))
        self.remotes_label = QLabel("-")
        self.remotes_label.setObjectName("muted")
        self.remotes_label.setWordWrap(True)
        self.remotes_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.remotes_label.setStyleSheet('font-family: "DejaVu Sans Mono", "Monospace"; font-size: 12px;')
        fbox.addWidget(self.remotes_label)
        remote_row = QHBoxLayout()
        remote_row.addStretch(1)
        self.link_btn = QPushButton("Vincular remoto...")
        self.link_btn.clicked.connect(self._link_remote)
        self.unlink_btn = QPushButton("Desvincular remoto")
        self.unlink_btn.setObjectName("danger")
        self.unlink_btn.clicked.connect(self._unlink_remote)
        remote_row.addWidget(self.link_btn)
        remote_row.addWidget(self.unlink_btn)
        fbox.addLayout(remote_row)
        outer.addWidget(folder_card)

        # --- contadores ---
        stats = QHBoxLayout()
        card, self.lbl_changes = self._stat_card("Cambios locales")
        stats.addWidget(card)
        card, self.lbl_ahead = self._stat_card("Por subir")
        stats.addWidget(card)
        card, self.lbl_behind = self._stat_card("Por bajar")
        stats.addWidget(card)
        outer.addLayout(stats)

        # --- acciones ---
        actions = QFrame()
        actions.setObjectName("card")
        abox = QVBoxLayout(actions)
        abox.setContentsMargins(16, 14, 16, 14)
        abox.setSpacing(8)
        abox.addWidget(self._section("Mensaje del commit"))
        self.message = QLineEdit()
        self.message.setPlaceholderText("Ej: Agrega la pantalla de ajustes")
        self.message.returnPressed.connect(self._push)
        abox.addWidget(self.message)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.pull_btn = QPushButton("Bajar actualización")
        self.pull_btn.clicked.connect(self._pull)
        self.push_btn = QPushButton("Subir cambios")
        self.push_btn.setObjectName("primary")
        self.push_btn.clicked.connect(self._push)
        buttons.addWidget(self.pull_btn)
        buttons.addWidget(self.push_btn)
        abox.addLayout(buttons)
        outer.addWidget(actions)

        # --- registro ---
        outer.addWidget(self._section("Registro"))
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet('font-family: "DejaVu Sans Mono", "Monospace"; font-size: 12px;')
        outer.addWidget(self.log, 1)

        recientes = self._load_recientes()
        self._fill_combo(recientes[0] if recientes else "")
        self._update_buttons()

    # ---------- helpers de interfaz ----------
    @staticmethod
    def _section(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    @staticmethod
    def _stat_card(caption: str) -> tuple[QFrame, QLabel]:
        card = QFrame()
        card.setObjectName("card")
        box = QVBoxLayout(card)
        box.setContentsMargins(16, 12, 16, 12)
        value = QLabel("-")
        value.setStyleSheet("font-size: 24px; font-weight: 700;")
        label = QLabel(caption)
        label.setObjectName("muted")
        box.addWidget(value)
        box.addWidget(label)
        return card, value

    def _set_stats(self, changes: str, ahead: str, behind: str) -> None:
        self.lbl_changes.setText(changes)
        self.lbl_ahead.setText(ahead)
        self.lbl_behind.setText(behind)

    def _log(self, title: str, text: str = "") -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        body = text.strip()
        self.log.appendPlainText(f"[{stamp}] {title}" + (f"\n{body}" if body else "") + "\n")

    # ---------- carpetas recientes ----------
    def _load_recientes(self) -> list[str]:
        value = self._settings.value("recientes", [], type=list)
        return [str(item) for item in value]

    def _fill_combo(self, current: str) -> None:
        self.folder.blockSignals(True)
        self.folder.clear()
        self.folder.addItems(self._load_recientes())
        self.folder.setCurrentText(current)
        self.folder.blockSignals(False)

    def _remember(self, path: str) -> None:
        recientes = [p for p in self._load_recientes() if p != path]
        recientes.insert(0, path)
        self._settings.setValue("recientes", recientes[:MAX_RECIENTES])
        self._fill_combo(path)

    def _path(self) -> str:
        return self.folder.currentText().strip()

    def _browse(self) -> None:
        start = self._path() or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, "Elegir carpeta del repositorio", start)
        if path:
            self.folder.setCurrentText(path)
            self._refresh()

    # ---------- ejecución en segundo plano ----------
    def _run(self, func, *args, on_done) -> None:
        if self._worker is not None:
            return
        worker = Worker(func, *args, parent=self)
        worker.finished.connect(worker.deleteLater)
        worker.done.connect(lambda result: self._finish(on_done, result))
        self._worker = worker
        self._set_busy(True)
        worker.start()

    def _finish(self, on_done, result) -> None:
        self._worker = None
        self._set_busy(False)
        on_done(result)

    def _set_busy(self, busy: bool) -> None:
        for widget in (self.folder, self.browse_btn, self.check_btn, self.message):
            widget.setEnabled(not busy)
        self._update_buttons()

    def _update_buttons(self) -> None:
        enabled = self._repo_ok and self._worker is None
        self.pull_btn.setEnabled(enabled)
        self.push_btn.setEnabled(enabled)
        self.link_btn.setEnabled(enabled)
        self.unlink_btn.setEnabled(enabled and bool(self._remotes))

    # ---------- acciones ----------
    def _refresh(self) -> None:
        path = self._path()
        if not path:
            self._show_status(git_ops.RepoStatus(error="Elige una carpeta para ver su estado."))
            return
        self.info.setText("Revisando estado...")
        self._run(git_ops.get_status, path, True, on_done=self._on_status)

    def _on_status(self, st: git_ops.RepoStatus) -> None:
        self._show_status(st)
        if st.fetch_error:
            self._log("No se pudo consultar el remoto", st.fetch_error)

    def _show_status(self, st: git_ops.RepoStatus) -> None:
        self._repo_ok = st.is_repo
        self._changes = st.changes
        self._remotes = st.remotes
        if not st.is_repo:
            self._set_stats("-", "-", "-")
            self.remotes_label.setText("-")
            self.info.setText(st.error or "La carpeta no es un repositorio git.")
            self._update_buttons()
            return

        self._remember(self._path())
        info = f"Rama: {st.branch or '(sin rama)'}"
        if not st.remotes:
            info += "   ·   sin remoto: no se puede subir ni bajar hasta vincular uno"
        elif not st.remote:
            info += "\nNo hay un remoto llamado 'origin'; vincula uno para subir y bajar."
        elif not st.has_upstream:
            info += "\nLa rama aún no está enlazada al remoto: se enlazará al subir."
        self.info.setText(info)
        self.remotes_label.setText(self._format_remotes(st.remotes))
        if st.has_upstream:
            self._set_stats(str(st.changes), str(st.ahead), str(st.behind))
        else:
            self._set_stats(str(st.changes), "-", "-")
        self._update_buttons()

    @staticmethod
    def _format_remotes(remotes: list[git_ops.Remote]) -> str:
        if not remotes:
            return "Sin remoto vinculado"
        lines = []
        for remote in remotes:
            url = remote.fetch_url or remote.push_url
            line = f"{remote.name}  →  {url}"
            if remote.push_url and remote.push_url != url:
                line += f"   (push: {remote.push_url})"
            lines.append(line)
        return "\n".join(lines)

    def _pick_remote(self, prompt: str) -> str:
        names = [remote.name for remote in self._remotes]
        if len(names) == 1:
            return names[0]
        name, ok = QInputDialog.getItem(self, "Elegir remoto", prompt, names, 0, False)
        return name if ok else ""

    def _link_remote(self) -> None:
        if not self._repo_ok or self._worker is not None:
            return
        current = next((r.fetch_url for r in self._remotes if r.name == "origin"), "")
        url, ok = QInputDialog.getText(
            self,
            "Vincular remoto",
            "URL del repositorio en GitHub (se vincula como 'origin'):",
            QLineEdit.EchoMode.Normal,
            current,
        )
        if not ok or not url.strip():
            return
        self._run(
            git_ops.set_remote,
            self._path(),
            url,
            on_done=lambda r: self._after_action("Vincular remoto", r),
        )

    def _unlink_remote(self) -> None:
        if not self._repo_ok or self._worker is not None or not self._remotes:
            return
        name = self._pick_remote("¿Qué remoto quieres desvincular?")
        if not name:
            return
        url = next((r.fetch_url or r.push_url for r in self._remotes if r.name == name), "")
        answer = QMessageBox.question(
            self,
            "Desvincular remoto",
            f"¿Quitar el remoto '{name}' ({url})?\n\n"
            "Tus archivos y commits locales no se borran, y el repositorio en GitHub tampoco. "
            "Solo se quita el enlace: no podrás subir ni bajar hasta vincular otro remoto.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._run(
            git_ops.remove_remote,
            self._path(),
            name,
            on_done=lambda r: self._after_action("Desvincular remoto", r),
        )

    def _pull(self) -> None:
        path = self._path()
        self._run(git_ops.pull, path, on_done=lambda r: self._after_action("Bajar actualización", r))

    def _push(self) -> None:
        if not self._repo_ok or self._worker is not None:
            return
        message = self.message.text().strip()
        if self._changes and not message:
            QMessageBox.warning(
                self, "Falta el mensaje", "Hay cambios sin subir: escribe un mensaje de commit."
            )
            self.message.setFocus()
            return
        path = self._path()
        self._run(
            git_ops.commit_and_push,
            path,
            message,
            on_done=lambda r: self._after_action("Subir cambios", r),
        )

    def _after_action(self, title: str, result: git_ops.Result) -> None:
        self._log(f"{title}: {'correcto' if result.ok else 'falló'}", result.output or "Listo.")
        if result.ok:
            if title == "Subir cambios":
                self.message.clear()
            self.repo_synced.emit(f"{title}: listo")
        self._refresh()
