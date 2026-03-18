import unittest

from settings_manager import SettingsManager


class SettingsManagerHelpersTests(unittest.TestCase):
    def test_linux_exec_value_quotes_spaces(self):
        parts = ["/opt/Perf Monitor/bin/python", "/home/user/My Tools/perf/main.py"]
        rendered = SettingsManager._linux_exec_value(parts)
        self.assertEqual(
            rendered,
            "'/opt/Perf Monitor/bin/python' '/home/user/My Tools/perf/main.py'",
        )

    def test_windows_run_value_quotes_spaces(self):
        parts = [r"C:\\Program Files\\Perf Monitor\\PerfMonitor.exe"]
        rendered = SettingsManager._windows_run_value(parts)
        self.assertTrue(rendered.startswith('"'))
        self.assertTrue(rendered.endswith('"'))
        self.assertIn(r"Program Files", rendered)


if __name__ == "__main__":
    unittest.main()
