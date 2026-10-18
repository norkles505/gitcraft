import sys

from PyQt6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.theme import STYLESHEET


def main() -> int:
    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("GitCraft")
    qt_app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    return qt_app.exec()


if __name__ == "__main__":
    sys.exit(main())
