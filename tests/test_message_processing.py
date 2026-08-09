import json
import unittest

from app.models.config import TextEncoding
from app.models.packet import UdpPacket
from app.services.message_decoder import (
    MessageDecodeError,
    MessageDecoder,
)


class MessageDecoderTest(unittest.TestCase):

    def test_decode_utf8_chinese(self) -> None:
        raw_data = "上海设备正常".encode("utf-8")

        text = MessageDecoder.decode(
            raw_data,
            TextEncoding.UTF8,
        )

        self.assertEqual(text, "上海设备正常")

    def test_decode_gbk_chinese(self) -> None:
        raw_data = "上海设备正常".encode("gbk")

        text = MessageDecoder.decode(
            raw_data,
            TextEncoding.GBK,
        )

        self.assertEqual(text, "上海设备正常")

    def test_wrong_encoding_raises_error(self) -> None:
        gbk_data = "中文数据".encode("gbk")

        with self.assertRaises(MessageDecodeError):
            MessageDecoder.decode(
                gbk_data,
                TextEncoding.UTF8,
            )


class UdpPacketTest(unittest.TestCase):

    def test_packet_is_utf8_json(self) -> None:
        text = "上海设备正常"
        raw_data = text.encode("gbk")

        packet = UdpPacket.from_serial_message(
            text=text,
            raw_data=raw_data,
            serial_port="/dev/cu.test",
            encoding=TextEncoding.GBK,
        )

        udp_bytes = packet.to_bytes()
        decoded_json = json.loads(
            udp_bytes.decode("utf-8")
        )

        self.assertEqual(decoded_json["protocol_version"], 1)
        self.assertEqual(decoded_json["text"], text)
        self.assertEqual(decoded_json["source_encoding"], "gbk")
        self.assertEqual(
            decoded_json["byte_count"],
            len(raw_data),
        )
        self.assertTrue(decoded_json["message_id"])
        self.assertTrue(decoded_json["received_at"])


if __name__ == "__main__":
    unittest.main()