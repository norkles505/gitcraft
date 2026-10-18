"""Hilo genérico para ejecutar tareas largas sin congelar la ventana."""

from PyQt6.QtCore import QThread, pyqtSignal

from app import git_ops


class Worker(QThread):
    """Ejecuta `func(*args)` en segundo plano y emite `done(resultado)`."""

    done = pyqtSignal(object)

    def __init__(self, func, *args, parent=None) -> None:
        super().__init__(parent)
        self._func = func
        self._args = args

    def run(self) -> None:
        try:
            result = self._func(*self._args)
        except Exception as exc:  # noqa: BLE001
            result = git_ops.Result(False, f"Error inesperado: {exc}")
        self.done.emit(result)
