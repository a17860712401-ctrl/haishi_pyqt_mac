from dataclasses import dataclass


@dataclass
class RuntimeStatistics:
    """保存本次程序运行期间的串口和 UDP 统计数据。"""

    received_bytes: int = 0
    receive_success: int = 0
    receive_failure: int = 0
    udp_send_success: int = 0
    udp_send_failure: int = 0

    def record_receive_success(self, byte_count: int) -> None:
        self._validate_byte_count(byte_count)
        self.received_bytes += byte_count
        self.receive_success += 1

    def record_receive_failure(self, byte_count: int = 0) -> None:
        self._validate_byte_count(byte_count)
        self.received_bytes += byte_count
        self.receive_failure += 1

    def record_udp_success(self) -> None:
        self.udp_send_success += 1

    def record_udp_failure(self) -> None:
        self.udp_send_failure += 1

    def reset(self) -> None:
        self.received_bytes = 0
        self.receive_success = 0
        self.receive_failure = 0
        self.udp_send_success = 0
        self.udp_send_failure = 0

    @staticmethod
    def _validate_byte_count(byte_count: int) -> None:
        if byte_count < 0:
            raise ValueError("字节数不能小于 0")