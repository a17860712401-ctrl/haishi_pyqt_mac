from typing import Optional
from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtCore import QObject, pyqtSlot
from serial.tools import list_ports
from app.services.origin_monitor import OriginMonitor
from app.models.config import SerialConfig
from app.models.packet import UdpPacket
from app.models.statistics import RuntimeStatistics
from app.services.frame_assembler import FrameAssembler
from app.services.message_decoder import (
    MessageDecodeError,
    MessageDecoder,
)
from PyQt6.QtCore import (
    QObject,
    QTimer,
    pyqtSlot,
)
from app.services.udp_sender import (
    UdpSendError,
    UdpSender,
)
from app.ui.main_window import MainWindow
from app.workers.serial_worker import SerialWorker
from app.services.settings_manager import (
    SettingsManager,
    SettingsManagerError,
)

class MainController(QObject):
    """协调界面、串口线程、分帧、解码和 UDP 发送。"""
    AUTO_CONNECT_RETRY_INTERVAL_MS = 3000
    AUTO_CONNECT_MAX_ATTEMPTS = 20
    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)

        self._window = window
        self._statistics = RuntimeStatistics()
        self._frame_assembler = FrameAssembler()
        self._settings_manager = SettingsManager()

        self._origin_folder_count = 0
        self._origin_file_count = 0
        self._origin_monitor = OriginMonitor(self)

        self._serial_worker: Optional[SerialWorker] = None
        self._serial_config: Optional[SerialConfig] = None
        self._udp_sender: Optional[UdpSender] = None

        self._manual_stop = False
        self._serial_had_error = False
        self._last_serial_error = ""
        self._shutting_down = False

        self._auto_connect_active = False
        self._auto_connect_attempts = 0

        self._auto_connect_timer = QTimer(self)
        self._auto_connect_timer.setSingleShot(
            True
        )
        self._auto_connect_timer.setInterval(
            self.AUTO_CONNECT_RETRY_INTERVAL_MS
        )
        self._auto_connect_timer.timeout.connect(
            self._try_auto_connect
        )

        self._connect_signals()

        self._window.update_statistics(
            self._statistics
        )
        self._window.set_serial_state(
            "disconnected",
            "未连接",
        )
        self._window.set_udp_state(
            "等待发送",
            "disconnected",
        )
        self._origin_monitor.start()
        self.refresh_ports()
        self._restore_settings()

    def _connect_signals(self) -> None:
        self._window.refresh_ports_requested.connect(
            self.refresh_ports
        )
        self._window.toggle_serial_requested.connect(
            self.toggle_serial
        )
        self._window.reset_statistics_requested.connect(
            self.reset_statistics
        )
        self._window.closing.connect(
            self.shutdown
        )

        self._frame_assembler.frame_ready.connect(
            self._handle_complete_frame
        )
        self._origin_monitor.counts_changed.connect(
            self._on_origin_counts_changed
        )
        self._origin_monitor.log_message.connect(
            self._window.append_log
        )

    def _restore_settings(self) -> None:
        try:
            settings = (
                self._settings_manager.load()
            )

        except SettingsManagerError as error:
            self._window.append_log(
                str(error),
                "ERROR",
            )
            self._window.append_log(
                "将继续使用界面默认配置",
                "WARNING",
            )
            return

        if settings is None:
            self._window.append_log(
                "没有找到已保存的软件配置，"
                "当前使用界面默认配置",
                "INFO",
            )
            return

        self._window.apply_configs(
            settings.serial,
            settings.udp,
        )

        self._window.append_log(
            "已恢复软件配置："
            f"串口 {settings.serial.port}，"
            f"波特率 {settings.serial.baud_rate}，"
            f"UDP {settings.udp.host}:"
            f"{settings.udp.port}",
            "INFO",
        )       
    @pyqtSlot()
    def refresh_ports(self) -> None:
        try:
            port_infos = sorted(
                list_ports.comports(),
                key=lambda info: (
                    not info.device.startswith("/dev/cu."),
                    info.device,
                ),
            )

            ports = []

            for info in port_infos:
                description = info.description

                if description == "n/a":
                    description = ""

                ports.append(
                    (info.device, description)
                )

            self._window.set_serial_ports(ports)
            self._window.append_log(
                f"发现 {len(ports)} 个串口"
            )

        except Exception as error:
            self._window.set_serial_ports([])
            self._window.append_log(
                f"刷新串口失败：{error}",
                "ERROR",
            )

    @pyqtSlot()
    def start_auto_connect(self) -> None:
        if self._shutting_down:
            return

        if (
            self._serial_worker is not None
            and self._serial_worker.isRunning()
        ):
            return

        self._auto_connect_timer.stop()
        self._auto_connect_active = True
        self._auto_connect_attempts = 0

        self._window.append_log(
            "检测到Windows开机自启动，"
            "开始自动打开串口",
            "INFO",
        )

        self._try_auto_connect()


    @pyqtSlot()
    def _try_auto_connect(self) -> None:
        if (
            not self._auto_connect_active
            or self._shutting_down
        ):
            return

        if (
            self._serial_worker is not None
            and self._serial_worker.isRunning()
        ):
            return

        if (
            self._auto_connect_attempts
            >= self.AUTO_CONNECT_MAX_ATTEMPTS
        ):
            self._auto_connect_active = False

            self._window.append_log(
                "自动打开串口失败："
                "已达到最大尝试次数",
                "ERROR",
            )
            return

        self._auto_connect_attempts += 1

        self._window.append_log(
            "正在进行自动连接："
            f"第 {self._auto_connect_attempts}/"
            f"{self.AUTO_CONNECT_MAX_ATTEMPTS} 次",
            "INFO",
        )

        started = self.open_serial(
            save_settings=False
        )

        if not started:
            self._schedule_auto_retry()


    def _schedule_auto_retry(self) -> None:
        if (
            not self._auto_connect_active
            or self._shutting_down
        ):
            return

        if (
            self._auto_connect_attempts
            >= self.AUTO_CONNECT_MAX_ATTEMPTS
        ):
            self._auto_connect_active = False
            self._auto_connect_timer.stop()

            self._window.append_log(
                "自动打开串口失败："
                "已完成20次尝试",
                "ERROR",
            )
            return

        if self._auto_connect_timer.isActive():
            return

        next_attempt = (
            self._auto_connect_attempts + 1
        )

        self._window.append_log(
            "串口暂时不可用，3秒后重试："
            f"下一次为第 {next_attempt}/"
            f"{self.AUTO_CONNECT_MAX_ATTEMPTS} 次",
            "WARNING",
        )

        self._auto_connect_timer.start()

    def _cancel_auto_connect(
        self,
        reason: str = "",
    ) -> None:
        was_active = (
            self._auto_connect_active
            or self._auto_connect_timer.isActive()
        )

        self._auto_connect_active = False
        self._auto_connect_timer.stop()

        if was_active and reason:
            self._window.append_log(
                reason,
                "INFO",
            )

    

    @pyqtSlot()
    def toggle_serial(self) -> None:
        self._cancel_auto_connect(
                "检测到用户手动操作，"
                "已取消自动连接重试"
            )
        if (
            self._serial_worker is not None
            and self._serial_worker.isRunning()
        ):
            self.close_serial()
        else:
            self.open_serial()

    def open_serial(
        self,
        save_settings: bool = True,
    ) -> bool:
        try:
            serial_config = (
                self._window.get_serial_config()
            )
            udp_config = self._window.get_udp_config()

            serial_config.validate()
            udp_config.validate()

            if save_settings:
                try:
                    self._settings_manager.save(
                        serial_config,
                        udp_config,
                    )

                except SettingsManagerError as error:
                    self._window.append_log(
                        str(error),
                        "ERROR",
                    )
                    self._window.append_log(
                        "配置保存失败，"
                        "但仍会继续尝试打开串口",
                        "WARNING",
                    )

                else:
                    self._window.append_log(
                        "软件配置已保存："
                        f"{self._settings_manager.settings_path}",
                        "INFO",
                    )

            udp_sender = UdpSender(udp_config)

        except (ValueError, OSError) as error:
            self._window.set_serial_state(
                "error",
                "配置错误",
            )
            self._window.set_udp_state(
                "配置错误",
                "error",
            )
            self._window.append_log(
                str(error),
                "ERROR",
            )
            return False

        if self._udp_sender is not None:
            self._udp_sender.close()

        self._serial_config = serial_config
        self._udp_sender = udp_sender
        self._manual_stop = False
        self._serial_had_error = False
        self._last_serial_error = ""

        self._frame_assembler.discard()
        self._frame_assembler.set_gap_ms(
            serial_config.frame_gap_ms
        )

        worker = SerialWorker(
            serial_config,
            self,
        )

        worker.port_opened.connect(
            self._on_serial_opened
        )
        worker.bytes_received.connect(
            self._frame_assembler.feed
        )
        worker.error_occurred.connect(
            self._on_serial_error
        )
        worker.port_closed.connect(
            self._on_serial_closed
        )
        worker.finished.connect(
            self._on_worker_finished
        )

        self._serial_worker = worker

        self._window.set_serial_state(
            "connecting",
            "正在连接",
        )
        self._window.set_udp_state(
            "等待串口数据",
            "disconnected",
        )
        self._window.append_log(
            f"正在打开串口 {serial_config.port}"
        )

        worker.start()
        return True

    def close_serial(self) -> None:
        worker = self._serial_worker

        if worker is None or not worker.isRunning():
            return

        self._manual_stop = True

        self._window.set_serial_state(
            "closing",
            "正在关闭",
        )
        self._window.append_log(
            "正在关闭串口"
        )

        worker.request_stop()

    @pyqtSlot(str)
    def _on_serial_opened(self, port: str) -> None:
        if self._auto_connect_active:
            attempts = (
                self._auto_connect_attempts
            )

            self._auto_connect_active = False
            self._auto_connect_timer.stop()

            self._window.append_log(
                "自动打开串口成功："
                f"共尝试 {attempts} 次",
                "INFO",
            )
        self._window.set_serial_state(
            "connected",
            "已连接",
        )
        self._window.append_log(
            f"串口已打开：{port}"
        )

    @pyqtSlot(str)
    def _on_serial_error(self, message: str) -> None:
        self._serial_had_error = True
        self._last_serial_error = message

        self._statistics.record_receive_failure()
        self._window.update_statistics(
            self._statistics
        )

        self._window.set_serial_state(
            "error",
            "串口异常",
        )
        self._window.append_log(
            f"串口异常：{message}",
            "ERROR",
        )

    @pyqtSlot()
    def _on_serial_closed(self) -> None:
        if (
            self._manual_stop
            and not self._serial_had_error
        ):
            self._frame_assembler.flush()
        else:
            self._frame_assembler.discard()

        if self._udp_sender is not None:
            self._udp_sender.close()
            self._udp_sender = None

        if not self._shutting_down:
            if self._serial_had_error:
                self._window.set_serial_state(
                    "error",
                    "连接失败",
                )
            else:
                self._window.set_serial_state(
                    "disconnected",
                    "未连接",
                )
                self._window.set_udp_state(
                    "等待发送",
                    "disconnected",
                )
                self._window.append_log(
                    "串口已关闭"
                )

        self._manual_stop = False

    @pyqtSlot()
    def _on_worker_finished(self) -> None:
        finished_worker = self.sender()

        if finished_worker is self._serial_worker:
            self._serial_worker = None

        if isinstance(finished_worker, SerialWorker):
            finished_worker.deleteLater()
        if (
            self._auto_connect_active
            and self._serial_had_error
            and not self._shutting_down
        ):
            self._schedule_auto_retry()

    @pyqtSlot(bytes)
    def _handle_complete_frame(
        self,
        raw_data: bytes,
    ) -> None:
        config = self._serial_config

        if config is None:
            return

        try:
            text = MessageDecoder.decode(
                raw_data,
                config.encoding,
            )
        except MessageDecodeError as error:
            self._statistics.record_receive_failure(
                len(raw_data)
            )
            self._window.update_statistics(
                self._statistics
            )
            self._window.set_udp_state(
                "未发送：解码失败",
                "error",
            )
            self._window.append_log(
                str(error),
                "ERROR",
            )
            return

        self._statistics.record_receive_success(
            len(raw_data)
        )
        self._window.append_received_message(
            text,
            len(raw_data),
        )

        packet = UdpPacket.from_serial_message(
            text=text,
            raw_data=raw_data,
            serial_port=config.port,
            encoding=config.encoding,
            origin_folder_count=(
                self._origin_folder_count
            ),
            origin_file_count=(
                self._origin_file_count
            ),
        )

        try:
            if self._udp_sender is None:
                raise UdpSendError(
                    "UDP 发送器未初始化"
                )

            sent_count = self._udp_sender.send(
                packet.to_bytes()
            )

            self._statistics.record_udp_success()
            self._window.set_udp_state(
                f"发送成功：{sent_count} bytes",
                "success",
            )
            self._window.append_log(
                f"UDP 发送成功：{sent_count} bytes"
            )

        except (UdpSendError, OSError) as error:
            self._statistics.record_udp_failure()
            self._window.set_udp_state(
                "发送失败",
                "error",
            )
            self._window.append_log(
                str(error),
                "ERROR",
            )

        self._window.update_statistics(
            self._statistics
        )

    @pyqtSlot(int, int)
    def _on_origin_counts_changed(
        self,
        folder_count: int,
        file_count: int,
    ) -> None:
        self._origin_folder_count = folder_count
        self._origin_file_count = file_count

        self._window.update_origin_counts(
            folder_count,
            file_count,
        )

    @pyqtSlot()
    def reset_statistics(self) -> None:
        self._statistics.reset()
        self._window.update_statistics(
            self._statistics
        )
        self._window.append_log(
            "运行统计已清零"
        )

    @pyqtSlot()
    def shutdown(self) -> None:
        if self._shutting_down:
            return

        self._shutting_down = True

        self._auto_connect_active = False
        self._auto_connect_timer.stop()

        self._origin_monitor.stop()
        self._frame_assembler.discard()

        worker = self._serial_worker

        if worker is not None and worker.isRunning():
            worker.request_stop()
            worker.wait(1500)

        if self._udp_sender is not None:
            self._udp_sender.close()
            self._udp_sender = None