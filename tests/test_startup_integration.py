import unittest
from unittest.mock import Mock, patch

import main as main_module
from app.services.startup_manager import StartupManagerError
from main import ensure_windows_startup


class StartupIntegrationTest(unittest.TestCase):

    def setUp(self) -> None:
        self.window = Mock()

    @patch("main.StartupManager.ensure_enabled")
    @patch(
        "main.StartupManager.is_windows",
        return_value=False,
    )
    def test_non_windows_skips_registration(
        self,
        is_windows_mock,
        ensure_enabled_mock,
    ) -> None:
        ensure_windows_startup(self.window)

        is_windows_mock.assert_called_once_with()
        ensure_enabled_mock.assert_not_called()
        self.window.append_log.assert_not_called()

    @patch("main.QMessageBox.warning")
    @patch("main.StartupManager.ensure_enabled")
    @patch(
        "main.StartupManager.is_windows",
        return_value=True,
    )
    def test_windows_registration_success_is_logged(
        self,
        is_windows_mock,
        ensure_enabled_mock,
        warning_mock,
    ) -> None:
        ensure_windows_startup(self.window)

        ensure_enabled_mock.assert_called_once_with()
        warning_mock.assert_not_called()
        self.window.append_log.assert_called_once_with(
            "已确保 Windows 登录自启动"
        )

    @patch("main.QMessageBox.warning")
    @patch(
        "main.StartupManager.ensure_enabled",
        side_effect=StartupManagerError(
            "设置自动启动失败：拒绝访问"
        ),
    )
    @patch(
        "main.StartupManager.is_windows",
        return_value=True,
    )
    def test_registration_failure_warns_but_does_not_stop(
        self,
        is_windows_mock,
        ensure_enabled_mock,
        warning_mock,
    ) -> None:
        # 如果异常继续向外抛出，本测试会直接失败。
        ensure_windows_startup(self.window)

        ensure_enabled_mock.assert_called_once_with()

        self.window.append_log.assert_called_once_with(
            "设置自动启动失败：拒绝访问",
            "ERROR",
        )

        warning_mock.assert_called_once()
        warning_arguments = warning_mock.call_args.args

        self.assertIs(warning_arguments[0], self.window)
        self.assertEqual(
            warning_arguments[1],
            "开机自启动设置失败",
        )
        self.assertIn(
            "软件将继续运行",
            warning_arguments[2],
        )
        self.assertIn(
            "拒绝访问",
            warning_arguments[2],
        )

    def test_main_ensures_startup_before_showing_window(
        self,
    ) -> None:
        events = []

        fake_application = Mock()
        fake_application.exec.return_value = 0

        fake_window = Mock()
        fake_window.show.side_effect = (
            lambda: events.append("show")
        )

        fake_controller = Mock()

        with (
            patch(
                "main.QApplication",
                return_value=fake_application,
            ),
            patch(
                "main.MainWindow",
                return_value=fake_window,
            ),
            patch(
                "main.MainController",
                return_value=fake_controller,
            ),
            patch(
                "main.ensure_windows_startup",
                side_effect=lambda window: events.append(
                    "startup"
                ),
            ) as startup_mock,
        ):
            result = main_module.main()

        startup_mock.assert_called_once_with(
            fake_window
        )
        fake_window.show.assert_called_once_with()

        self.assertLess(
            events.index("startup"),
            events.index("show"),
        )
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()