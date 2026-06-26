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
            expected = AppSettings(
                window_x=10,
                window_y=20,
                window_width=800,
                window_height=600,
                language="en",
                theme="dark",
            )

            service.save_settings(expected)
            actual = service.load_settings()

            self.assertEqual(actual, expected)

    def test_invalid_settings_file_returns_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            settings_path.write_text("{invalid json", encoding="utf-8")

            actual = SettingsService(settings_path).load_settings()

            self.assertEqual(actual, AppSettings())

    def test_window_geometry_save_preserves_language_and_theme(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "settings.json"
            service = SettingsService(settings_path)
            service.save_settings(AppSettings(language="en", theme="dark"))

            service.save_window_geometry(x=1, y=2, width=3, height=4)
            actual = service.load_settings()

            self.assertEqual(actual.language, "en")
            self.assertEqual(actual.theme, "dark")
            self.assertEqual(actual.window_x, 1)
            self.assertEqual(actual.window_height, 4)

    def test_invalid_language_and_theme_fall_back_to_defaults(self) -> None:
        actual = AppSettings.from_dict({"language": "bad", "theme": "bad"})

        self.assertEqual(actual.language, "ko")
        self.assertEqual(actual.theme, "system")


if __name__ == "__main__":
    unittest.main()
