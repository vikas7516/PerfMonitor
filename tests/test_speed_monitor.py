import unittest

from speed_monitor import SpeedMonitor


class SpeedMonitorTests(unittest.TestCase):
    def setUp(self):
        self.monitor = SpeedMonitor()

    def test_format_speed_zero(self):
        value, unit = self.monitor._format_speed(0.0)
        self.assertEqual(value, "0.0")
        self.assertEqual(unit, "KB/s")

    def test_format_speed_bytes(self):
        value, unit = self.monitor._format_speed(512.0)
        self.assertEqual(value, "512")
        self.assertEqual(unit, "B/s")

    def test_format_speed_kilobytes(self):
        value, unit = self.monitor._format_speed(2048.0)
        self.assertEqual(value, "2.0")
        self.assertEqual(unit, "KB/s")

    def test_format_speed_megabytes(self):
        value, unit = self.monitor._format_speed(3 * 1024 * 1024)
        self.assertEqual(value, "3.00")
        self.assertEqual(unit, "MB/s")

    def test_ignores_loopback_interface(self):
        self.assertFalse(self.monitor._is_relevant_iface("lo"))
        self.assertFalse(self.monitor._is_relevant_iface("loopback0"))

    def test_accepts_regular_interface(self):
        self.assertTrue(self.monitor._is_relevant_iface("eth0"))
        self.assertTrue(self.monitor._is_relevant_iface("wlan0"))


if __name__ == "__main__":
    unittest.main()
