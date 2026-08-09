import socket
import unittest

from app.models.config import UdpConfig
from app.services.udp_sender import (
    UdpSendError,
    UdpSender,
)


class UdpSenderTest(unittest.TestCase):

    def setUp(self) -> None:
        self.receiver = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM,
        )
        self.receiver.bind(("127.0.0.1", 0))
        self.receiver.settimeout(1.0)

        receiver_host, receiver_port = (
            self.receiver.getsockname()
        )

        self.config = UdpConfig(
            host=receiver_host,
            port=receiver_port,
        )

    def tearDown(self) -> None:
        self.receiver.close()

    def test_sends_utf8_payload_to_receiver(self) -> None:
        sender = UdpSender(self.config)
        self.addCleanup(sender.close)

        payload = "上海设备运行正常".encode("utf-8")

        sent_count = sender.send(payload)
        received_data, sender_address = (
            self.receiver.recvfrom(65535)
        )

        self.assertEqual(sent_count, len(payload))
        self.assertEqual(received_data, payload)
        self.assertEqual(
            sender_address[0],
            "127.0.0.1",
        )

    def test_rejects_oversized_datagram(self) -> None:
        sender = UdpSender(self.config)
        self.addCleanup(sender.close)

        oversized_payload = bytes(
            UdpSender.MAX_DATAGRAM_SIZE + 1
        )

        with self.assertRaises(UdpSendError):
            sender.send(oversized_payload)

    def test_rejects_empty_payload(self) -> None:
        sender = UdpSender(self.config)
        self.addCleanup(sender.close)

        with self.assertRaises(UdpSendError):
            sender.send(b"")

    def test_cannot_send_after_close(self) -> None:
        sender = UdpSender(self.config)
        sender.close()

        with self.assertRaises(UdpSendError):
            sender.send(b"test")


if __name__ == "__main__":
    unittest.main()