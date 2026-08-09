from dataclasses import dataclass
from enum import Enum
from ipaddress import ip_address


class TextEncoding(str, Enum):
    """串口文本编码。"""

    UTF8 = "utf-8"
    GBK = "gbk"


class Parity(str, Enum):
    """校验位，值与 pyserial 的定义保持一致。"""

    NONE = "N"
    ODD = "O"
    EVEN = "E"
    MARK = "M"
    SPACE = "S"


@dataclass(frozen=True)
class SerialConfig:
    """打开串口时使用的配置快照。"""

    port: str = ""
    baud_rate: int = 115200
    data_bits: int = 8
    stop_bits: float = 1.0
    parity: Parity = Parity.NONE
    encoding: TextEncoding = TextEncoding.UTF8
    frame_gap_ms: int = 1000

    def validate(self) -> None:
        if not self.port:
            raise ValueError("请选择串口")

        if self.baud_rate <= 0:
            raise ValueError("波特率必须大于 0")

        if self.data_bits not in (5, 6, 7, 8):
            raise ValueError("数据位只能是 5、6、7 或 8")

        if self.stop_bits not in (1.0, 1.5, 2.0):
            raise ValueError("停止位只能是 1、1.5 或 2")

        if self.frame_gap_ms <= 0:
            raise ValueError("帧间静默时间必须大于 0")


@dataclass(frozen=True)
class UdpConfig:
    """UDP 目标地址配置。"""

    host: str = "127.0.0.1"
    port: int = 9000

    def validate(self) -> None:
        host = self.host.strip()

        if not host:
            raise ValueError("UDP 目标地址不能为空")

        try:
            ip_address(host)
        except ValueError as error:
            raise ValueError("UDP 目标地址不是有效的 IP 地址") from error

        if not 1 <= self.port <= 65535:
            raise ValueError("UDP 端口必须在 1～65535 之间")