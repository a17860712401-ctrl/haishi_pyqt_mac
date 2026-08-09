from app.models.config import TextEncoding


class MessageDecodeError(ValueError):
    """串口数据无法按指定编码解码。"""


class MessageDecoder:
    """将一个完整串口字节帧解码为字符串。"""

    @staticmethod
    def decode(
        frame: bytes,
        encoding: TextEncoding,
    ) -> str:
        if not frame:
            raise MessageDecodeError("不能解码空数据")

        try:
            return frame.decode(
                encoding.value,
                errors="strict",
            )
        except UnicodeDecodeError as error:
            raise MessageDecodeError(
                f"无法使用 {encoding.value} 解码串口数据：{error}"
            ) from error