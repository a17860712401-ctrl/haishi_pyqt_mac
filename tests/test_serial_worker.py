import time
import unittest
from unittest.mock import patch

import serial
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtTest import QSignalSpy

from app.models.config import Parity, SerialConfig
from app.workers.serial_worker import SerialWorker


class FakeSerial:
    """测试用假串口，不依赖真实硬件。"""

    last_instance = None

    def __init__(self, **kwargs) -> None:
        FakeSerial.last_instance = self
        self.arguments = kwargs
        self.is_open = True
        self.closed = False
        self._chunks = ["上海数据".encode("utf-8")]

    @property
    def in_waiting(self) -> int:
        if not self._chunks:
            return 0
        return len(self._chunks[0])

    def read(self, size: int) -> bytes:
        if self._chunks:
            return self._chunks.pop(0)

        time.sleep(0.01)
        return b""

    def close(self) -> None:
        self.is_open = False
        self.closed = True


class SerialWorkerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.application = (
            QCoreApplication.instance()
            or QCoreApplication([])
        )

    def test_reads_bytes_and_uses_config(self) -> None:
        config = SerialConfig(
            port="/dev/cu.test",
            baud_rate=9600,
            data_bits=8,
            stop_bits=1.0,
            parity=Parity.NONE,
        )
        worker = SerialWorker(config)

        opened_spy = QSignalSpy(worker.port_opened)
        data_spy = QSignalSpy(worker.bytes_received)
        error_spy = QSignalSpy(worker.error_occurred)

        with patch(
            "app.workers.serial_worker.serial.Serial",
            FakeSerial,
        ):
            worker.start()

            if len(data_spy) == 0:
                self.assertTrue(data_spy.wait(500))

            worker.request_stop()
            self.assertTrue(worker.wait(1000))

        QCoreApplication.processEvents()

        self.assertEqual(len(opened_spy), 1)
        self.assertEqual(
            bytes(data_spy[0][0]),
            "上海数据".encode("utf-8"),
        )
        self.assertEqual(len(error_spy), 0)

        fake_serial = FakeSerial.last_instance
        self.assertIsNotNone(fake_serial)
        self.assertTrue(fake_serial.closed)
        self.assertEqual(fake_serial.arguments["baudrate"], 9600)
        self.assertEqual(fake_serial.arguments["parity"], "N")
        self.assertEqual(fake_serial.arguments["timeout"], 0.1)

    def test_reports_open_error(self) -> None:
        config = SerialConfig(port="/dev/cu.missing")
        worker = SerialWorker(config)
        error_spy = QSignalSpy(worker.error_occurred)

        with patch(
            "app.workers.serial_worker.serial.Serial",
            side_effect=serial.SerialException("无法打开串口"),
        ):
            worker.start()

            if len(error_spy) == 0:
                self.assertTrue(error_spy.wait(500))

            self.assertTrue(worker.wait(1000))

        self.assertIn("无法打开串口", str(error_spy[0][0]))


if __name__ == "__main__":
    unittest.main()