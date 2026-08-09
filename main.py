import sys

from PyQt6.QtWidgets import QApplication

from app.controllers.main_controller import MainController
from app.ui.main_window import MainWindow


def main() -> int:
    application = QApplication(sys.argv)

    window = MainWindow()
    controller = MainController(window)

    application.aboutToQuit.connect(
        controller.shutdown
    )

    window.show()

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())