from threading import Event
from typing import Optional

import serial
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from app.models.config import SerialConfig


class SerialWorker(QThread):
    """使用阻塞式读取方式运行的串口后台线程。"""

    port_opened = pyqtSignal(str)
    bytes_received = pyqtSignal(bytes)
    error_occurred = pyqtSignal(str)
    port_closed = pyqtSignal()

    def __init__(
        self,
        config: SerialConfig,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._stop_event = Event()

    def request_stop(self) -> None:
        """请求线程退出；读取超时后线程会检查这个标志。"""

        self._stop_event.set()

    def run(self) -> None:
        serial_port: Optional[serial.Serial] = None

        try:
            self._config.validate()

            serial_port = serial.Serial(
                port=self._config.port,
                baudrate=self._config.baud_rate,
                bytesize=self._config.data_bits,
                stopbits=self._config.stop_bits,
                parity=self._config.parity.value,
                timeout=0.1,
            )

            self.port_opened.emit(self._config.port)

            while not self._stop_event.is_set():
                waiting_count = serial_port.in_waiting

                # 没有缓存数据时读取一个字节，最多阻塞 0.1 秒。
                read_size = waiting_count if waiting_count > 0 else 1
                data = serial_port.read(read_size)

                if data:
                    self.bytes_received.emit(data)

        except (ValueError, serial.SerialException, OSError) as error:
            self.error_occurred.emit(str(error))

        finally:
            if serial_port is not None and serial_port.is_open:
                try:
                    serial_port.close()
                except (serial.SerialException, OSError) as error:
                    self.error_occurred.emit(f"关闭串口失败：{error}")

            self.port_closed.emit()