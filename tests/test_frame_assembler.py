import unittest

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtTest import QSignalSpy, QTest

from app.services.frame_assembler import FrameAssembler


class FrameAssemblerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.application = (
            QCoreApplication.instance()
            or QCoreApplication([])
        )

    def test_emits_frame_after_inactivity(self) -> None:
        assembler = FrameAssembler(gap_ms=50)
        spy = QSignalSpy(assembler.frame_ready)

        raw_data = "上海串口数据".encode("utf-8")
        assembler.feed(raw_data)

        self.assertTrue(spy.wait(300))
        self.assertEqual(len(spy), 1)
        self.assertEqual(bytes(spy[0][0]), raw_data)

    def test_new_data_restarts_timer(self) -> None:
        assembler = FrameAssembler(gap_ms=120)
        spy = QSignalSpy(assembler.frame_ready)

        assembler.feed(b"A")
        QTest.qWait(60)

        assembler.feed(b"B")
        QTest.qWait(80)

        # 距离最后一次 feed 还没有达到 120ms。
        self.assertEqual(len(spy), 0)

        self.assertTrue(spy.wait(200))
        self.assertEqual(bytes(spy[0][0]), b"AB")

    def test_flush_outputs_current_buffer(self) -> None:
        assembler = FrameAssembler(gap_ms=1000)
        spy = QSignalSpy(assembler.frame_ready)

        assembler.feed("未完成数据".encode("utf-8"))
        assembler.flush()

        self.assertEqual(len(spy), 1)
        self.assertEqual(
            bytes(spy[0][0]),
            "未完成数据".encode("utf-8"),
        )
        self.assertEqual(assembler.buffered_byte_count, 0)

    def test_invalid_gap_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            FrameAssembler(gap_ms=0)


if __name__ == "__main__":
    unittest.main()