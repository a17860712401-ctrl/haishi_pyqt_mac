import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.models.config import (
    Parity,
    SerialConfig,
    TextEncoding,
    UdpConfig,
)


@dataclass(frozen=True)
class ApplicationSettings:
    serial: SerialConfig
    udp: UdpConfig


class SettingsManagerError(RuntimeError):
    """读取或保存软件配置失败。"""


class SettingsManager:
    VERSION = 1
    APPLICATION_NAME = "SerialUdpBridge"
    FILE_NAME = "application_settings.json"

    def __init__(
        self,
        settings_path: Optional[Path] = None,
    ) -> None:
        if settings_path is None:
            local_app_data = os.environ.get(
                "LOCALAPPDATA",
                str(Path.home()),
            )

            settings_path = (
                Path(local_app_data)
                / self.APPLICATION_NAME
                / self.FILE_NAME
            )

        self._settings_path = settings_path

    @property
    def settings_path(self) -> Path:
        return self._settings_path

    def load(
        self,
    ) -> Optional[ApplicationSettings]:
        if not self._settings_path.exists():
            return None

        try:
            data = json.loads(
                self._settings_path.read_text(
                    encoding="utf-8",
                )
            )

            if not isinstance(data, dict):
                raise ValueError(
                    "配置文件根节点必须是对象"
                )

            if data.get("version") != self.VERSION:
                raise ValueError(
                    "配置文件版本不受支持"
                )

            serial_data = data.get("serial")
            udp_data = data.get("udp")

            if not isinstance(serial_data, dict):
                raise ValueError(
                    "缺少有效的串口配置"
                )

            if not isinstance(udp_data, dict):
                raise ValueError(
                    "缺少有效的UDP配置"
                )

            serial_config = SerialConfig(
                port=str(serial_data["port"]),
                baud_rate=int(
                    serial_data["baud_rate"]
                ),
                data_bits=int(
                    serial_data["data_bits"]
                ),
                stop_bits=float(
                    serial_data["stop_bits"]
                ),
                parity=Parity(
                    str(serial_data["parity"])
                ),
                encoding=TextEncoding(
                    str(serial_data["encoding"])
                ),
                frame_gap_ms=int(
                    serial_data["frame_gap_ms"]
                ),
            )

            udp_config = UdpConfig(
                host=str(udp_data["host"]),
                port=int(udp_data["port"]),
            )

            serial_config.validate()
            udp_config.validate()

            return ApplicationSettings(
                serial=serial_config,
                udp=udp_config,
            )

        except (
            OSError,
            KeyError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as error:
            raise SettingsManagerError(
                f"无法读取软件配置：{error}"
            ) from error

    def save(
        self,
        serial_config: SerialConfig,
        udp_config: UdpConfig,
    ) -> None:
        try:
            serial_config.validate()
            udp_config.validate()

        except ValueError as error:
            raise SettingsManagerError(
                f"软件配置无效：{error}"
            ) from error

        data = {
            "version": self.VERSION,
            "serial": {
                "port": serial_config.port,
                "baud_rate": (
                    serial_config.baud_rate
                ),
                "data_bits": (
                    serial_config.data_bits
                ),
                "stop_bits": (
                    serial_config.stop_bits
                ),
                "parity": (
                    serial_config.parity.value
                ),
                "encoding": (
                    serial_config.encoding.value
                ),
                "frame_gap_ms": (
                    serial_config.frame_gap_ms
                ),
            },
            "udp": {
                "host": udp_config.host,
                "port": udp_config.port,
            },
        }

        temporary_path = (
            self._settings_path.with_suffix(
                ".tmp"
            )
        )

        try:
            self._settings_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            temporary_path.write_text(
                json.dumps(
                    data,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            temporary_path.replace(
                self._settings_path
            )

        except OSError as error:
            raise SettingsManagerError(
                f"无法保存软件配置：{error}"
            ) from error