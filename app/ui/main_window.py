from datetime import datetime
from typing import List, Tuple

from PyQt6.QtGui import QCloseEvent

from app.models.config import (
    Parity,
    SerialConfig,
    TextEncoding,
    UdpConfig,
)
from app.models.statistics import RuntimeStatistics


from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    DEFAULT_SERIAL_PORT = "COM6"
    refresh_ports_requested = pyqtSignal()
    toggle_serial_requested = pyqtSignal()
    reset_statistics_requested = pyqtSignal()
    closing = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("串口数据监测与 UDP 转发")
        self.resize(1100, 760)
        self.setMinimumSize(900, 650)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        config_layout = QHBoxLayout()
        config_layout.addWidget(
            self._create_serial_group(),
            stretch=2,
        )
        config_layout.addWidget(
            self._create_udp_group(),
            stretch=1,
        )

        main_layout.addLayout(config_layout)
        main_layout.addWidget(self._create_statistics_group())
        main_layout.addWidget(
            self._create_monitor_area(),
            stretch=1,
        )

        self.statusBar().showMessage("就绪")

        self._connect_ui_signals()
        self._apply_style()

    def _create_serial_group(self) -> QGroupBox:
        group = QGroupBox("串口配置")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)

        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(220)

        self.refresh_port_button = QPushButton("刷新")

        self.baud_rate_combo = QComboBox()
        self.baud_rate_combo.setEditable(True)
        self.baud_rate_combo.addItems(
            [
                "9600",
                "19200",
                "38400",
                "57600",
                "115200",
                "230400",
                "460800",
                "921600",
            ]
        )
        self.baud_rate_combo.setCurrentText("115200")

        self.data_bits_combo = QComboBox()
        self.data_bits_combo.addItems(
            ["8", "7", "6", "5"]
        )

        self.stop_bits_combo = QComboBox()
        self.stop_bits_combo.addItems(
            ["1", "1.5", "2"]
        )

        self.parity_combo = QComboBox()
        self.parity_combo.addItem("无校验", "N")
        self.parity_combo.addItem("奇校验", "O")
        self.parity_combo.addItem("偶校验", "E")
        self.parity_combo.addItem("Mark", "M")
        self.parity_combo.addItem("Space", "S")

        self.encoding_combo = QComboBox()
        self.encoding_combo.addItem("GBK", "gbk")
        self.encoding_combo.addItem("UTF-8", "utf-8")
        

        self.frame_gap_spin = QSpinBox()
        self.frame_gap_spin.setRange(100, 10000)
        self.frame_gap_spin.setValue(800)
        self.frame_gap_spin.setSuffix("ms")

        self.serial_button = QPushButton("打开串口")
        self.serial_button.setObjectName("primaryButton")

        self.serial_status_label = QLabel("未连接")
        self.serial_status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.serial_status_label.setObjectName("statusLabel")

        layout.addWidget(QLabel("串口"), 0, 0)
        layout.addWidget(self.port_combo, 0, 1, 1, 2)
        layout.addWidget(self.refresh_port_button, 0, 3)

        layout.addWidget(QLabel("波特率"), 1, 0)
        layout.addWidget(self.baud_rate_combo, 1, 1)
        layout.addWidget(QLabel("数据位"), 1, 2)
        layout.addWidget(self.data_bits_combo, 1, 3)

        layout.addWidget(QLabel("停止位"), 2, 0)
        layout.addWidget(self.stop_bits_combo, 2, 1)
        layout.addWidget(QLabel("校验位"), 2, 2)
        layout.addWidget(self.parity_combo, 2, 3)

        layout.addWidget(QLabel("字符编码"), 3, 0)
        layout.addWidget(self.encoding_combo, 3, 1)
        layout.addWidget(QLabel("静默时间"), 3, 2)
        layout.addWidget(self.frame_gap_spin, 3, 3)

        layout.addWidget(self.serial_status_label, 4, 0)
        layout.addWidget(self.serial_button, 4, 1, 1, 3)

        return group

    def _create_udp_group(self) -> QGroupBox:
        group = QGroupBox("UDP 目标")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(10)

        self.udp_host_edit = QLineEdit("127.0.0.1")

        self.udp_port_spin = QSpinBox()
        self.udp_port_spin.setRange(1, 65535)
        self.udp_port_spin.setValue(9000)

        self.udp_status_label = QLabel("等待发送")
        self.udp_status_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self.udp_status_label.setObjectName("statusLabel")

        layout.addWidget(QLabel("目标 IP"), 0, 0)
        layout.addWidget(self.udp_host_edit, 0, 1)

        layout.addWidget(QLabel("目标端口"), 1, 0)
        layout.addWidget(self.udp_port_spin, 1, 1)

        layout.addWidget(self.udp_status_label, 2, 0, 1, 2)
        layout.setRowStretch(3, 1)

        return group

    def _create_statistics_group(self) -> QGroupBox:
        group = QGroupBox("运行统计")
        layout = QHBoxLayout(group)

        self.received_bytes_label = QLabel("接收字节：0")
        self.receive_success_label = QLabel("接收成功：0")
        self.receive_failure_label = QLabel("接收失败：0")
        self.udp_success_label = QLabel("UDP 成功：0")
        self.udp_failure_label = QLabel("UDP 失败：0")
        self.origin_folder_count_label = QLabel(
            "Origin 文件夹：0"
        )
        self.origin_file_count_label = QLabel(
            "Origin 文件：0"
        )
        

        for label in (
            self.received_bytes_label,
            self.receive_success_label,
            self.receive_failure_label,
            self.udp_success_label,
            self.udp_failure_label,
            self.origin_folder_count_label,
            self.origin_file_count_label,
        ):
            layout.addWidget(label)

        layout.addStretch()

        self.reset_statistics_button = QPushButton("清零统计")
        layout.addWidget(self.reset_statistics_button)

        return group

    def _create_monitor_area(self) -> QSplitter:
        splitter = QSplitter(Qt.Orientation.Vertical)

        data_group = QGroupBox("接收数据")
        data_layout = QVBoxLayout(data_group)

        self.data_view = QPlainTextEdit()
        self.data_view.setReadOnly(True)
        self.data_view.setPlaceholderText(
            "完整串口消息将在这里显示……"
        )

        self.clear_data_button = QPushButton("清空数据")
        data_layout.addWidget(self.data_view)
        data_layout.addWidget(
            self.clear_data_button,
            alignment=Qt.AlignmentFlag.AlignRight,
        )

        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(2000)
        self.log_view.setPlaceholderText(
            "串口和 UDP 状态将在这里显示……"
        )

        self.clear_log_button = QPushButton("清空日志")
        log_layout.addWidget(self.log_view)
        log_layout.addWidget(
            self.clear_log_button,
            alignment=Qt.AlignmentFlag.AlignRight,
        )

        splitter.addWidget(data_group)
        splitter.addWidget(log_group)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        return splitter

    def _connect_ui_signals(self) -> None:
        self.refresh_port_button.clicked.connect(
            self.refresh_ports_requested
        )
        self.serial_button.clicked.connect(
            self.toggle_serial_requested
        )
        self.reset_statistics_button.clicked.connect(
            self.reset_statistics_requested
        )
        self.clear_data_button.clicked.connect(
            self.data_view.clear
        )
        self.clear_log_button.clicked.connect(
            self.log_view.clear
        )
    def get_serial_config(self) -> SerialConfig:
        return SerialConfig(
            port=self.port_combo.currentData() or "",
            baud_rate=int(self.baud_rate_combo.currentText()),
            data_bits=int(self.data_bits_combo.currentText()),
            stop_bits=float(self.stop_bits_combo.currentText()),
            parity=Parity(self.parity_combo.currentData()),
            encoding=TextEncoding(
                self.encoding_combo.currentData()
            ),
            frame_gap_ms=self.frame_gap_spin.value(),
        )

    def get_udp_config(self) -> UdpConfig:
        return UdpConfig(
            host=self.udp_host_edit.text().strip(),
            port=self.udp_port_spin.value(),
        )


    def apply_configs(
        self,
        serial_config: SerialConfig,
        udp_config: UdpConfig,
    ) -> None:
        port_index = self.port_combo.findData(
            serial_config.port
        )

        if port_index < 0:
            self.port_combo.addItem(
                f"{serial_config.port}（未检测到）",
                serial_config.port,
            )
            port_index = (
                self.port_combo.count() - 1
            )

        self.port_combo.setCurrentIndex(
            port_index
        )

        self.baud_rate_combo.setCurrentText(
            str(serial_config.baud_rate)
        )
        self.data_bits_combo.setCurrentText(
            str(serial_config.data_bits)
        )
        self.stop_bits_combo.setCurrentText(
            f"{serial_config.stop_bits:g}"
        )

        parity_index = self.parity_combo.findData(
            serial_config.parity.value
        )

        if parity_index >= 0:
            self.parity_combo.setCurrentIndex(
                parity_index
            )

        encoding_index = (
            self.encoding_combo.findData(
                serial_config.encoding.value
            )
        )

        if encoding_index >= 0:
            self.encoding_combo.setCurrentIndex(
                encoding_index
            )

        self.frame_gap_spin.setValue(
            serial_config.frame_gap_ms
        )

        self.udp_host_edit.setText(
            udp_config.host
        )
        self.udp_port_spin.setValue(
            udp_config.port
        )

    def set_serial_ports(
        self,
        ports: List[Tuple[str, str]],
    ) -> None:
        previous_port = self.port_combo.currentData()
        self.port_combo.clear()

        for device, description in ports:
            display_text = device

            if description:
                display_text += f" — {description}"

            self.port_combo.addItem(display_text, device)

        default_index = self.port_combo.findData(
            self.DEFAULT_SERIAL_PORT
        )

        if default_index < 0:
            self.port_combo.addItem(
                f"{self.DEFAULT_SERIAL_PORT}（未检测到）",
                self.DEFAULT_SERIAL_PORT,
            )
            default_index = (
                self.port_combo.count() - 1
            )

        previous_index = self.port_combo.findData(
            previous_port
        )

        if previous_index >= 0:
            self.port_combo.setCurrentIndex(
                previous_index
            )
            return

        self.port_combo.setCurrentIndex(
            default_index
        )

    def set_serial_state(
        self,
        state: str,
        message: str,
    ) -> None:
        is_connected = state == "connected"
        is_busy = state in ("connecting", "closing")
        configuration_enabled = not (
            is_connected or is_busy
        )

        configuration_widgets = (
            self.port_combo,
            self.refresh_port_button,
            self.baud_rate_combo,
            self.data_bits_combo,
            self.stop_bits_combo,
            self.parity_combo,
            self.encoding_combo,
            self.frame_gap_spin,
            self.udp_host_edit,
            self.udp_port_spin,
        )

        for widget in configuration_widgets:
            widget.setEnabled(configuration_enabled)

        self.serial_button.setEnabled(not is_busy)

        button_texts = {
            "disconnected": "打开串口",
            "connecting": "正在打开……",
            "connected": "关闭串口",
            "closing": "正在关闭……",
            "error": "重新打开串口",
        }

        self.serial_button.setText(
            button_texts.get(state, "打开串口")
        )
        self._set_status_label(
            self.serial_status_label,
            message,
            state,
        )

    def set_udp_state(
        self,
        message: str,
        state: str,
    ) -> None:
        self._set_status_label(
            self.udp_status_label,
            message,
            state,
        )

    def update_statistics(
        self,
        statistics: RuntimeStatistics,
    ) -> None:
        self.received_bytes_label.setText(
            f"接收字节：{statistics.received_bytes}"
        )
        self.receive_success_label.setText(
            f"接收成功：{statistics.receive_success}"
        )
        self.receive_failure_label.setText(
            f"接收失败：{statistics.receive_failure}"
        )
        self.udp_success_label.setText(
            f"UDP 成功：{statistics.udp_send_success}"
        )
        self.udp_failure_label.setText(
            f"UDP 失败：{statistics.udp_send_failure}"
        )
    def update_origin_counts(
        self,
        folder_count: int,
        file_count: int,
    ) -> None:
        self.origin_folder_count_label.setText(
            f"Origin 文件夹：{folder_count}"
        )
        self.origin_file_count_label.setText(
            f"Origin 文件：{file_count}"
        )
    def append_received_message(
        self,
        text: str,
        byte_count: int,
    ) -> None:
        timestamp = datetime.now().strftime(
            "%H:%M:%S.%f"
        )[:-3]

        self.data_view.appendPlainText(
            f"[{timestamp}] [{byte_count} bytes]\n"
            f"{text}\n"
        )

    def append_log(
        self,
        message: str,
        level: str = "INFO",
    ) -> None:
        timestamp = datetime.now().strftime(
            "%H:%M:%S.%f"
        )[:-3]

        self.log_view.appendPlainText(
            f"[{timestamp}] [{level}] {message}"
        )

    def _set_status_label(
        self,
        label: QLabel,
        message: str,
        state: str,
    ) -> None:
        label.setText(message)
        label.setProperty("state", state)

        label.style().unpolish(label)
        label.style().polish(label)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #f4f6f8;
            }

            QGroupBox {
                background-color: white;
                border: 1px solid #d8dde3;
                border-radius: 8px;
                margin-top: 10px;
                padding: 12px;
                font-weight: 600;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 5px;
            }

            QComboBox,
            QLineEdit,
            QSpinBox,
            QPlainTextEdit {
                border: 1px solid #c8ced6;
                border-radius: 5px;
                padding: 5px;
                background-color: white;
            }

            QPushButton {
                min-height: 28px;
                padding: 2px 14px;
                border: 1px solid #b8c0ca;
                border-radius: 5px;
                background-color: #ffffff;
            }

            QPushButton:hover {
                background-color: #eef3f8;
            }

            QPushButton#primaryButton {
                color: white;
                border: none;
                background-color: #1976d2;
            }

            QPushButton#primaryButton:hover {
                background-color: #1565c0;
            }

            QLabel#statusLabel {
                padding: 6px;
                border-radius: 5px;
                color: #52606d;
                background-color: #edf1f5;
            }

            QLabel#statusLabel[state="connected"],
            QLabel#statusLabel[state="success"] {
                color: #176b3a;
                background-color: #dff5e8;
            }

            QLabel#statusLabel[state="error"] {
                color: #a12622;
                background-color: #fde7e6;
            }

            QLabel#statusLabel[state="connecting"],
            QLabel#statusLabel[state="closing"] {
                color: #875500;
                background-color: #fff2cc;
            }

            QPlainTextEdit {
                font-family: Menlo, Monaco, monospace;
            }
            """
        )
    def closeEvent(
        self,
        event: QCloseEvent,
    ) -> None:
        self.closing.emit()
        super().closeEvent(event)