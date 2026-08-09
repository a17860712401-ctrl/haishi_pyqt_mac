import unittest

from app.models.statistics import RuntimeStatistics


class RuntimeStatisticsTest(unittest.TestCase):

    def test_record_statistics(self) -> None:
        statistics = RuntimeStatistics()

        statistics.record_receive_success(12)
        statistics.record_receive_failure(6)
        statistics.record_udp_success()
        statistics.record_udp_failure()

        self.assertEqual(statistics.received_bytes, 18)
        self.assertEqual(statistics.receive_success, 1)
        self.assertEqual(statistics.receive_failure, 1)
        self.assertEqual(statistics.udp_send_success, 1)
        self.assertEqual(statistics.udp_send_failure, 1)

    def test_reset_statistics(self) -> None:
        statistics = RuntimeStatistics(
            received_bytes=100,
            receive_success=5,
            receive_failure=2,
            udp_send_success=4,
            udp_send_failure=1,
        )

        statistics.reset()

        self.assertEqual(statistics, RuntimeStatistics())

    def test_negative_byte_count_is_rejected(self) -> None:
        statistics = RuntimeStatistics()

        with self.assertRaises(ValueError):
            statistics.record_receive_success(-1)


if __name__ == "__main__":
    unittest.main()