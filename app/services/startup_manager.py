import platform
import sys
from pathlib import Path


class StartupManagerError(RuntimeError):
    """配置 Windows 自动启动失败。"""


class StartupManager:
    APP_NAME = "SerialUdpBridge"

    RUN_KEY = (
        r"Software\Microsoft\Windows"
        r"\CurrentVersion\Run"
    )

    @staticmethod
    def is_windows() -> bool:
        return platform.system() == "Windows"

    @classmethod
    def get_startup_command(cls) -> str:
        if getattr(sys, "frozen", False):
            # PyInstaller 打包后的 EXE。
            return f'"{sys.executable}"'

        # Windows 源码开发环境。
        project_root = Path(__file__).resolve().parents[2]
        main_file = project_root / "main.py"

        return f'"{sys.executable}" "{main_file}"'

    @classmethod
    def ensure_enabled(cls) -> None:
        """
        确保当前程序已经注册为 Windows 登录自启动。

        macOS 开发环境中不执行任何操作。
        """

        if not cls.is_windows():
            return

        import winreg

        try:
            with winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                cls.RUN_KEY,
                0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.SetValueEx(
                    key,
                    cls.APP_NAME,
                    0,
                    winreg.REG_SZ,
                    cls.get_startup_command(),
                )

        except OSError as error:
            raise StartupManagerError(
                f"设置自动启动失败：{error}"
            ) from error