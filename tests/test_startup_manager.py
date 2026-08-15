import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from app.services.startup_manager import (
    StartupManager,
    StartupManagerError,
)


class StartupManagerTest(unittest.TestCase):

    def create_fake_winreg(self):
        key = object()

        key_context = MagicMock()
        key_context.__enter__.return_value = key
        key_context.__exit__.return_value = False

        fake_winreg = SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            KEY_SET_VALUE=object(),
            REG_SZ=object(),
            CreateKeyEx=Mock(
                return_value=key_context
            ),
            SetValueEx=Mock(),
        )

        return fake_winreg, key

    def test_source_mode_uses_python_and_main_file(
        self,
    ) -> None:
        project_root = (
            Path(__file__).resolve().parents[1]
        )

        with (
            patch.object(
                sys,
                "frozen",
                False,
                create=True,
            ),
            patch.object(
                sys,
                "executable",
                r"C:\Python\python.exe",
            ),
        ):
            command = (
                StartupManager.get_startup_command()
            )

        expected = (
            r'"C:\Python\python.exe" '
            f'"{project_root / "main.py"}"'
        )

        self.assertEqual(command, expected)

    def test_packaged_mode_uses_executable_only(
        self,
    ) -> None:
        executable = (
            r"C:\Program Files\SerialUdpBridge"
            r"\SerialUdpBridge.exe"
        )

        with (
            patch.object(
                sys,
                "frozen",
                True,
                create=True,
            ),
            patch.object(
                sys,
                "executable",
                executable,
            ),
        ):
            command = (
                StartupManager.get_startup_command()
            )

        self.assertEqual(
            command,
            f'"{executable}"',
        )

    def test_non_windows_does_not_touch_registry(
        self,
    ) -> None:
        fake_winreg, _ = (
            self.create_fake_winreg()
        )

        with (
            patch.object(
                StartupManager,
                "is_windows",
                return_value=False,
            ),
            patch.dict(
                sys.modules,
                {"winreg": fake_winreg},
            ),
        ):
            StartupManager.ensure_enabled()

        fake_winreg.CreateKeyEx.assert_not_called()
        fake_winreg.SetValueEx.assert_not_called()

    def test_windows_writes_current_user_run_key(
        self,
    ) -> None:
        fake_winreg, key = (
            self.create_fake_winreg()
        )

        startup_command = (
            r'"C:\Program Files\SerialUdpBridge'
            r'\SerialUdpBridge.exe"'
        )

        with (
            patch.object(
                StartupManager,
                "is_windows",
                return_value=True,
            ),
            patch.object(
                StartupManager,
                "get_startup_command",
                return_value=startup_command,
            ),
            patch.dict(
                sys.modules,
                {"winreg": fake_winreg},
            ),
        ):
            StartupManager.ensure_enabled()

        fake_winreg.CreateKeyEx.assert_called_once_with(
            fake_winreg.HKEY_CURRENT_USER,
            StartupManager.RUN_KEY,
            0,
            fake_winreg.KEY_SET_VALUE,
        )

        fake_winreg.SetValueEx.assert_called_once_with(
            key,
            StartupManager.APP_NAME,
            0,
            fake_winreg.REG_SZ,
            startup_command,
        )

    def test_registry_error_is_wrapped(
        self,
    ) -> None:
        fake_winreg, _ = (
            self.create_fake_winreg()
        )
        fake_winreg.CreateKeyEx.side_effect = (
            OSError("拒绝访问")
        )

        with (
            patch.object(
                StartupManager,
                "is_windows",
                return_value=True,
            ),
            patch.dict(
                sys.modules,
                {"winreg": fake_winreg},
            ),
            self.assertRaisesRegex(
                StartupManagerError,
                "拒绝访问",
            ),
        ):
            StartupManager.ensure_enabled()


if __name__ == "__main__":
    unittest.main()