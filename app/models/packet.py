import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from app.models.config import TextEncoding


@dataclass(frozen=True)
class UdpPacket:
    """发送给目标软件的 JSON 数据包。"""

    protocol_version: int
    message_id: str
    received_at: str
    serial_port: str
    source_encoding: str
    byte_count: int
    text: str
    origin_folder_count: int = 0
    origin_file_count: int = 0

    @classmethod
    def from_serial_message(
        cls,
        text: str, 
        raw_data: bytes,
        serial_port: str,
        encoding: TextEncoding,
        origin_folder_count: int = 0,
        origin_file_count: int = 0,
    ) -> "UdpPacket":
        return cls(
            protocol_version=1,
            message_id=str(uuid4()),
            received_at=datetime.now().astimezone().isoformat(
                timespec="milliseconds"
            ),
            serial_port=serial_port,
            source_encoding=encoding.value,
            byte_count=len(raw_data),
            text=text,
            origin_folder_count=origin_folder_count,
            origin_file_count=origin_file_count,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def to_bytes(self) -> bytes:
        return self.to_json().encode("utf-8")