from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot


class FrameAssembler(QObject):
    """
    根据串口静默时间组装完整数据。

    每次收到新字节都会重新启动计时器；
    连续 gap_ms 毫秒没有新数据时，输出一个完整字节帧。
    """

    frame_ready = pyqtSignal(bytes)
    buffer_size_changed = pyqtSignal(int)

    def __init__(
        self,
        gap_ms: int = 1000,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        if gap_ms <= 0:
            raise ValueError("静默时间必须大于 0")

        self._buffer = bytearray()

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(gap_ms)
        self._timer.timeout.connect(self._finish_frame)

    @property
    def gap_ms(self) -> int:
        return self._timer.interval()

    @property
    def buffered_byte_count(self) -> int:
        return len(self._buffer)

    @pyqtSlot(bytes)
    def feed(self, data: bytes) -> None:
        """接收串口线程送来的新字节。"""

        if not data:
            return

        self._buffer.extend(data)
        self.buffer_size_changed.emit(len(self._buffer))

        # QTimer 已运行时，再次调用 start() 会重新开始计时。
        self._timer.start()

    def set_gap_ms(self, gap_ms: int) -> None:
        if gap_ms <= 0:
            raise ValueError("静默时间必须大于 0")

        self._timer.setInterval(gap_ms)

        if self._buffer:
            self._timer.start()

    @pyqtSlot()
    def flush(self) -> None:
        """
        立即输出缓冲区。

        关闭串口时可以调用，防止最后一条已接收数据被直接丢弃。
        """

        self._timer.stop()
        self._finish_frame()

    @pyqtSlot()
    def discard(self) -> None:
        """放弃当前未完成的数据，不产生 frame_ready 信号。"""

        self._timer.stop()
        self._buffer.clear()
        self.buffer_size_changed.emit(0)

    @pyqtSlot()
    def _finish_frame(self) -> None:
        if not self._buffer:
            return

        frame = bytes(self._buffer)
        self._buffer.clear()

        self.buffer_size_changed.emit(0)
        self.frame_ready.emit(frame)