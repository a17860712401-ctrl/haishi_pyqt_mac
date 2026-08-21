import socket
from ipaddress import ip_address
from typing import Optional

from app.models.config import UdpConfig


class UdpSendError(RuntimeError):
    """UDP 数据无法发送。"""


class UdpSender:
    """负责向固定目标地址发送 UDP 数据包。"""

    MAX_DATAGRAM_SIZE = 65507
    SOURCE_PORT = 9001

    def __init__(self, config: UdpConfig) -> None:
        config.validate()

        self._config = config
        self._target_ip = ip_address(config.host.strip())

        socket_family = (
            socket.AF_INET6
            if self._target_ip.version == 6
            else socket.AF_INET
        )

        self._socket: Optional[socket.socket] = socket.socket(
            socket_family,
            socket.SOCK_DGRAM,
        )

        source_host = (
            "::"
            if socket_family == socket.AF_INET6
            else "0.0.0.0"
        )

        try:
            self._socket.bind(
                (source_host, self.SOURCE_PORT)
            )
        except OSError:
            self._socket.close()
            self._socket = None
            raise

    @property
    def is_closed(self) -> bool:
        return self._socket is None

    def send(self, payload: bytes) -> int:
        if self._socket is None:
            raise UdpSendError("UDP 发送器已经关闭")

        if not payload:
            raise UdpSendError("不能发送空 UDP 数据包")

        if len(payload) > self.MAX_DATAGRAM_SIZE:
            raise UdpSendError(
                "UDP 数据包过大："
                f"{len(payload)} 字节，"
                f"最大允许 {self.MAX_DATAGRAM_SIZE} 字节"
            )

        target = (
            str(self._target_ip),
            self._config.port,
        )

        try:
            sent_count = self._socket.sendto(
                payload,
                target,
            )
        except OSError as error:
            raise UdpSendError(
                f"UDP 发送失败：{error}"
            ) from error

        if sent_count != len(payload):
            raise UdpSendError(
                f"UDP 数据发送不完整："
                f"计划发送 {len(payload)} 字节，"
                f"实际发送 {sent_count} 字节"
            )

        return sent_count

    def close(self) -> None:
        if self._socket is None:
            return

        self._socket.close()
        self._socket = None

