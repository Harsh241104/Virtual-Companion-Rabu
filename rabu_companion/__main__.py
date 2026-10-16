import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from .window import RabuWindow


def main() -> None:
    # Enable high DPI scaling for better appearance on modern displays
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)

    app = QApplication(sys.argv)

    window = RabuWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
