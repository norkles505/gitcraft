"""Ajustes: inicio de sesión con GitHub usando GitHub CLI (`gh`)."""

import re
import shutil

from PyQt6.QtCore import QProcess, QProcessEnvironment, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices, QGuiApplication
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

HOST = "github.com"
DEVICE_URL = "https://github.com/login/device"
CODE_RE = re.compile(r"\b([A-Z0-9]{4}-[A-Z0-9]{4})\b")

# Instalación oficial de GitHub CLI para Debian/Ubuntu/Mint (se ejecuta como root con pkexec).
INSTALL_GH_SCRIPT = r"""
set -e
mkdir -p -m 755 /etc/apt/keyrings
if command -v wget >/dev/null 2>&1; then
  wget -qO /etc/apt/keyrings/githubcli-archive-keyring.gpg https://cli.github.com/packages/githubcli-archive-keyring.gpg
else
  curl -fsSL -o /etc/apt/keyrings/githubcli-archive-keyring.gpg https://cli.github.com/packages/githubcli-archive-keyring.gpg
fi
chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list
apt-get update
apt-get install -y gh
"""


class SettingsPage(QWidget):
    # Se emite con el nombre de usuario, o "" si no hay sesión.
    session_changed = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        self._user = ""
        self._code = ""
        self._busy = 0
        self._cancelled = False
        self._install_offered = False
        self._login_proc: QProcess | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.setSpacing(14)

        title = QLabel("Ajustes")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Conecta tu cuenta de GitHub.")
        subtitle.setObjectName("pageSubtitle")
        outer.addWidget(title)
        outer.addWidget(subtitle)

        # ---------- Tarjeta: inicio de sesión ----------
        card = QFrame()
        card.setObjectName("card")
        card.setMaximumWidth(640)
        form = QVBoxLayout(card)
        form.setContentsMargins(20, 18, 20, 18)
        form.setSpacing(10)

        section = QLabel("Cuenta de GitHub")
        section.setObjectName("sectionTitle")
        form.addWidget(section)

        self.status = QLabel()
        self.status.setWordWrap(True)
        form.addWidget(self.status)

        # Código de un solo uso (visible solo mientras se autoriza en el navegador)
        self.code_box = QWidget()
        code_layout = QVBoxLayout(self.code_box)
        code_layout.setContentsMargins(0, 0, 0, 0)
        code_layout.setSpacing(6)
        code_hint = QLabel(
            "Se abrió GitHub en tu navegador. Pega este código si te lo pide "
            "(ya lo copiamos al portapapeles):"
        )
        code_hint.setObjectName("muted")
        code_hint.setWordWrap(True)
        self.code_label = QLabel()
        self.code_label.setStyleSheet("font-size: 26px; font-weight: 700; letter-spacing: 4px;")
        self.code_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        code_buttons = QHBoxLayout()
        copy_btn = QPushButton("Copiar código")
        copy_btn.clicked.connect(self._copy_code)
        open_btn = QPushButton("Abrir GitHub otra vez")
        open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DEVICE_URL)))
        code_buttons.addWidget(copy_btn)
        code_buttons.addWidget(open_btn)
        code_buttons.addStretch(1)
        code_layout.addWidget(code_hint)
        code_layout.addWidget(self.code_label)
        code_layout.addLayout(code_buttons)
        form.addWidget(self.code_box)

        buttons = QHBoxLayout()
        self.install_btn = QPushButton("Instalar GitHub CLI")
        self.install_btn.setObjectName("primary")
        self.install_btn.clicked.connect(self._install_gh)
        buttons.addWidget(self.install_btn)
        self.login_btn = QPushButton("Iniciar sesión con GitHub")
        self.login_btn.setObjectName("primary")
        self.login_btn.clicked.connect(self._on_login_clicked)
        self.logout_btn = QPushButton("Cerrar sesión")
        self.logout_btn.setObjectName("danger")
        self.logout_btn.clicked.connect(self._on_logout_clicked)
        buttons.addWidget(self.login_btn)
        buttons.addWidget(self.logout_btn)
        buttons.addStretch(1)
        form.addLayout(buttons)

        self.message = QLabel()
        self.message.setObjectName("muted")
        self.message.setWordWrap(True)
        self.message.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addWidget(self.message)

        outer.addWidget(card)

        # ---------- Tarjeta: alternativa con token ----------
        self.token_card = QFrame()
        self.token_card.setObjectName("card")
        self.token_card.setMaximumWidth(640)
        token_form = QVBoxLayout(self.token_card)
        token_form.setContentsMargins(20, 18, 20, 18)
        token_form.setSpacing(10)

        token_title = QLabel("Alternativa: token de acceso personal")
        token_title.setObjectName("sectionTitle")
        token_hint = QLabel(
            "Si no puedes usar el navegador. Se crea en GitHub: Settings > Developer settings > "
            "Personal access tokens (con permiso 'repo'). Se guarda en gh, no en esta app."
        )
        token_hint.setObjectName("muted")
        token_hint.setWordWrap(True)
        self.token = QLineEdit()
        self.token.setEchoMode(QLineEdit.EchoMode.Password)
        self.token.setPlaceholderText("ghp_...")
        self.token_btn = QPushButton("Usar token")
        self.token_btn.clicked.connect(self._on_token_clicked)
        token_form.addWidget(token_title)
        token_form.addWidget(token_hint)
        token_form.addWidget(self.token)
        token_form.addWidget(self.token_btn)
        outer.addWidget(self.token_card)

        outer.addStretch(1)

        self._render()
        QTimer.singleShot(0, self.refresh_session)

    # ---------- ejecución de gh ----------
    def _start(self, args, done, stdin: str | None = None, on_output=None, program: str | None = None) -> QProcess:
        """Lanza `gh <args>` (o `program`) sin bloquear la interfaz. `done(ok, salida)` al terminar."""
        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("NO_COLOR", "1")
        env.insert("GH_NO_UPDATE_NOTIFIER", "1")
        proc.setProcessEnvironment(env)
        out: list[str] = []

        def read_output() -> None:
            out.append(bytes(proc.readAllStandardOutput()).decode("utf-8", "replace"))
            if on_output:
                on_output("".join(out))

        def finished(code: int, _status) -> None:
            read_output()
            proc.deleteLater()
            done(code == 0, "".join(out).strip())

        def errored(error) -> None:
            if error == QProcess.ProcessError.FailedToStart:
                proc.deleteLater()
                QTimer.singleShot(0, lambda: done(False, "No se pudo ejecutar gh. ¿Está instalado?"))

        proc.readyReadStandardOutput.connect(read_output)
        proc.finished.connect(finished)
        proc.errorOccurred.connect(errored)
        proc.start(program or shutil.which("gh") or "gh", list(args))
        if stdin is not None:
            proc.write(stdin.encode())
        proc.closeWriteChannel()
        return proc

    def _run(self, args, done, stdin: str | None = None, program: str | None = None) -> None:
        """Como _start, pero marca la página como ocupada mientras corre."""
        self._busy += 1
        self._render()

        def finish(ok: bool, out: str) -> None:
            self._busy -= 1
            done(ok, out)
            self._render()

        self._start(args, finish, stdin=stdin, program=program)

    # ---------- instalación automática de gh ----------
    @staticmethod
    def _can_auto_install() -> bool:
        return bool(shutil.which("apt-get") and shutil.which("pkexec"))

    def _offer_install(self) -> None:
        """Una sola vez por ejecución: pregunta si quiere instalar gh ahora."""
        if self._install_offered or shutil.which("gh") or not self._can_auto_install():
            return
        self._install_offered = True
        answer = QMessageBox.question(
            self,
            "Instalar GitHub CLI",
            "GitCraft usa GitHub CLI (gh) para iniciar sesión y conectarse a GitHub, "
            "y no está instalado.\n\n¿Instalarlo ahora? Te pedirá tu contraseña de administrador.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._install_gh()

    def _install_gh(self) -> None:
        if shutil.which("gh") or self._busy:
            return
        if not self._can_auto_install():
            self.message.setText(
                "No puedo instalarlo automáticamente en este sistema. "
                "Instálalo desde https://cli.github.com y reinicia la app."
            )
            return
        self.message.setText("Instalando GitHub CLI... puede tardar un minuto. Escribe tu contraseña cuando la pida.")
        self._run(["sh", "-c", INSTALL_GH_SCRIPT], self._install_done, program="pkexec")

    def _install_done(self, ok: bool, out: str) -> None:
        if ok and shutil.which("gh"):
            self.message.setText("GitHub CLI instalado. Ya puedes iniciar sesión.")
            self.refresh_session()
        elif not ok and ("dismissed" in out.lower() or "not authorized" in out.lower()):
            self.message.setText("Instalación cancelada: no se confirmó la contraseña.")
        else:
            self.message.setText("No se pudo instalar GitHub CLI.\n" + out[-400:])

    # ---------- sesión ----------
    def refresh_session(self) -> None:
        if not shutil.which("gh"):
            self._set_user("")
            QTimer.singleShot(400, self._offer_install)
            return
        self._run(["api", "user", "--jq", ".login"], self._session_done)

    def _session_done(self, ok: bool, out: str) -> None:
        lines = out.splitlines()
        self._set_user(lines[-1].strip() if ok and lines else "")

    def _set_user(self, user: str) -> None:
        self._user = user
        self._render()
        self.session_changed.emit(user)

    # ---------- inicio de sesión por navegador ----------
    def _on_login_clicked(self) -> None:
        if self._login_proc is not None:
            self._cancelled = True
            self._login_proc.kill()
            return
        self._cancelled = False
        self._code = ""
        self.message.setText("")
        self._login_proc = self._start(
            ["auth", "login", "--hostname", HOST, "--git-protocol", "https", "--web"],
            self._login_done,
            stdin="\n",
            on_output=self._on_login_output,
        )
        self._render()

    def _on_login_output(self, text: str) -> None:
        match = CODE_RE.search(text)
        if match and not self._code:
            self._code = match.group(1)
            self.code_label.setText(self._code)
            QGuiApplication.clipboard().setText(self._code)
            QDesktopServices.openUrl(QUrl(DEVICE_URL))
            self._render()

    def _login_done(self, ok: bool, out: str) -> None:
        self._login_proc = None
        self._code = ""
        if ok:
            self.message.setText("Autorizado. Configurando git para usar tu sesión...")
            self._run(["auth", "setup-git", "--hostname", HOST], self._after_setup_git)
        elif self._cancelled:
            self.message.setText("Inicio de sesión cancelado.")
            self._render()
        else:
            self.message.setText("No se pudo iniciar sesión.\n" + out[-400:])
            self._render()

    def _after_setup_git(self, ok: bool, out: str) -> None:
        self.message.setText("Sesión iniciada." if ok else "Sesión iniciada, pero git no quedó configurado:\n" + out[-400:])
        self.refresh_session()

    def _copy_code(self) -> None:
        if self._code:
            QGuiApplication.clipboard().setText(self._code)

    # ---------- cerrar sesión ----------
    def _on_logout_clicked(self) -> None:
        self._run(["auth", "logout", "--hostname", HOST], self._logout_done)

    def _logout_done(self, ok: bool, out: str) -> None:
        self.message.setText("Sesión cerrada." if ok else "No se pudo cerrar la sesión.\n" + out[-400:])
        self.refresh_session()

    # ---------- token ----------
    def _on_token_clicked(self) -> None:
        token = self.token.text().strip()
        if not token:
            self.message.setText("Pega un token primero.")
            return
        self.token.clear()
        self._run(
            ["auth", "login", "--hostname", HOST, "--git-protocol", "https", "--with-token"],
            self._token_done,
            stdin=token + "\n",
        )

    def _token_done(self, ok: bool, out: str) -> None:
        if ok:
            self.message.setText("Token aceptado. Configurando git...")
            self._run(["auth", "setup-git", "--hostname", HOST], self._after_setup_git)
        else:
            self.message.setText("El token no se aceptó.\n" + out[-400:])

    # ---------- interfaz ----------
    def _render(self) -> None:
        has_gh = bool(shutil.which("gh"))
        logging_in = self._login_proc is not None
        idle = self._busy == 0 and not logging_in

        if not has_gh and self._busy:
            status = "Instalando GitHub CLI..."
        elif not has_gh and self._can_auto_install():
            status = "GitHub CLI (gh) no está instalado. Instálalo con el botón de abajo para poder iniciar sesión."
        elif not has_gh:
            status = "No se encontró GitHub CLI (gh). Instálalo desde https://cli.github.com y reinicia la app."
        elif logging_in:
            status = "Esperando la autorización en el navegador..."
        elif self._user:
            status = f"Sesión iniciada como {self._user}"
        else:
            status = "Sin sesión iniciada."
        self.status.setText(status)

        self.install_btn.setVisible(not has_gh and self._can_auto_install())
        self.install_btn.setEnabled(idle)
        self.code_box.setVisible(logging_in and bool(self._code))
        self.login_btn.setText("Cancelar" if logging_in else "Iniciar sesión con GitHub")
        self.login_btn.setVisible(has_gh and (logging_in or not self._user))
        self.login_btn.setEnabled(has_gh and (logging_in or idle))
        self.logout_btn.setVisible(bool(self._user) and not logging_in)
        self.logout_btn.setEnabled(has_gh and idle)
        self.token_card.setEnabled(has_gh and idle)
