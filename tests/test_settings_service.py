from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eml_viewer.models.app_settings import AppSettings
from eml_viewer.services.settings_service import SettingsService


class SettingsServiceTest(unittest.TestCase):
    def test_save_and_load_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            service = SettingsService(settings_path)
            expected = AppSettings(window_x=10, window_y=20, window_width=800, window_height=600)

            service.save_settings(expected)
            actual = service.load_settings()

            self.assertEqual(actual, expected)

    def test_invalid_settings_file_returns_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text("{invalid json", encoding="utf-8")

            actual = SettingsService(settings_path).load_settings()

            self.assertEqual(actual, AppSettings())


if __name__ == "__main__":
    unittest.main()
