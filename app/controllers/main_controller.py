from typing import Optional

from PyQt6.QtCore import QObject, pyqtSlot
from serial.tools import list_ports

from app.models.config import SerialConfig
from app.models.packet import UdpPacket
from app.models.statistics import RuntimeStatistics
from app.services.frame_assembler import FrameAssembler
from app.services.message_decoder import (
    MessageDecodeError,
    MessageDecoder,
)
from app.services.udp_sender import (
    UdpSendError,
    UdpSender,
)
from app.ui.main_window import MainWindow
from app.workers.serial_worker import SerialWorker


class MainController(QObject):
    """协调界面、串口线程、分帧、解码和 UDP 发送。"""

    def __init__(self, window: MainWindow) -> None:
        super().__init__(window)

        self._window = window
        self._statistics = RuntimeStatistics()
        self._frame_assembler = FrameAssembler()

        self._serial_worker: Optional[SerialWorker] = None
        self._serial_config: Optional[SerialConfig] = None
        self._udp_sender: Optional[UdpSender] = None

        self._manual_stop = False
        self._serial_had_error = False
        self._last_serial_error = ""
        self._shutting_down = False

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

        self.refresh_ports()

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
    def toggle_serial(self) -> None:
        if (
            self._serial_worker is not None
            and self._serial_worker.isRunning()
        ):
            self.close_serial()
        else:
            self.open_serial()

    def open_serial(self) -> None:
        try:
            serial_config = (
                self._window.get_serial_config()
            )
            udp_config = self._window.get_udp_config()

            serial_config.validate()
            udp_config.validate()

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
            return

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

        self._frame_assembler.discard()

        worker = self._serial_worker

        if worker is not None and worker.isRunning():
            worker.request_stop()
            worker.wait(1500)

        if self._udp_sender is not None:
            self._udp_sender.close()
            self._udp_sender = None