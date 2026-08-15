import sys

from PyQt6.QtWidgets import QApplication, QMessageBox

from app.controllers.main_controller import MainController
from app.ui.main_window import MainWindow
from app.services.startup_manager import (
    StartupManager,
    StartupManagerError,
)

def ensure_windows_startup(
    window: MainWindow,
) -> None:
    """
    确保软件已经注册为 Windows 登录自启动。

    注册失败时记录错误并提示用户，但不阻止软件继续运行。
    """

    if not StartupManager.is_windows():
        return

    try:
        StartupManager.ensure_enabled()

    except StartupManagerError as error:
        window.append_log(
            str(error),
            "ERROR",
        )

        QMessageBox.warning(
            window,
            "开机自启动设置失败",
            f"{error}\n\n"
            "软件将继续运行，但本次未能完成"
            "开机自启动设置。",
        )
        return

    window.append_log(
        "已确保 Windows 登录自启动"
    )
def main() -> int:
    application = QApplication(sys.argv)

    window = MainWindow()
    controller = MainController(window)

    application.aboutToQuit.connect(
        controller.shutdown
    )
    ensure_windows_startup(window)
    window.show()

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())