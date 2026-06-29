from __future__ import annotations

import json
import unittest
from pathlib import Path

from eml_viewer.i18n.translator import LOCALES_DIR, current_language, set_language, tr


class I18nTest(unittest.TestCase):

    def setUp(self):
        # Store current language to restore it after each test
        self.original_lang = current_language()

    def tearDown(self):
        # Restore original language
        set_language(self.original_lang)

    def test_locale_files_exist_and_load(self):
        """Verify that the locale JSON files exist and are valid JSON."""
        ko_path = LOCALES_DIR / "ko.json"
        en_path = LOCALES_DIR / "en.json"
        self.assertTrue(ko_path.exists(), "ko.json should exist")
        self.assertTrue(en_path.exists(), "en.json should exist")

        with open(ko_path, "r", encoding="utf-8") as f:
            ko_data = json.load(f)
            self.assertIsInstance(ko_data, dict)
            self.assertIn("app.pyside_missing", ko_data)

        with open(en_path, "r", encoding="utf-8") as f:
            en_data = json.load(f)
            self.assertIsInstance(en_data, dict)
            self.assertIn("app.pyside_missing", en_data)

    def test_english_and_korean_translations(self):
        """Verify that expected translations are returned for Korean and English."""
        set_language("ko")
        self.assertEqual(current_language(), "ko")
        self.assertEqual(tr("button.close"), "닫기")

        set_language("en")
        self.assertEqual(current_language(), "en")
        self.assertEqual(tr("button.close"), "Close")

    def test_unsupported_language_fallback(self):
        """Verify that set_language with an unsupported language falls back to Korean."""
        set_language("fr")  # French is not supported
        self.assertEqual(current_language(), "ko")
        self.assertEqual(tr("button.close"), "닫기")

    def test_missing_active_language_key_fallback(self):
        """Verify that a missing key in the active language falls back to Korean."""
        from eml_viewer.i18n.translator import _translations

        # Ensure locales are loaded
        set_language("en")

        # Inject key to 'ko' but not 'en'
        _translations["ko"]["test.mock.only_ko"] = "한국어 전용"
        if "test.mock.only_ko" in _translations["en"]:
            del _translations["en"]["test.mock.only_ko"]

        try:
            self.assertEqual(tr("test.mock.only_ko"), "한국어 전용")
        finally:
            # Clean up injected key
            if "test.mock.only_ko" in _translations["ko"]:
                del _translations["ko"]["test.mock.only_ko"]

    def test_missing_everywhere_fallback(self):
        """Verify that a key missing everywhere falls back to the key itself."""
        set_language("en")
        self.assertEqual(tr("nonexistent.key.name"), "nonexistent.key.name")

    def test_placeholder_formatting(self):
        """Verify placeholder formatting works with correct and incorrect placeholders."""
        set_language("ko")
        # Correct formatting
        formatted = tr("attachment.saved_many", count=3, destination_dir="C:/Temp")
        self.assertIn("첨부파일 3개를 저장했습니다.", formatted)
        self.assertIn("C:/Temp", formatted)

        # Incorrect/missing placeholders should fallback to unformatted translation safely.
        safe_fallback = tr("attachment.saved_many", wrong_placeholder=3)
        self.assertEqual(
            safe_fallback, "첨부파일 {count}개를 저장했습니다.\n\n{destination_dir}"
        )

    def test_locale_keys_consistency(self):
        """Verify that all locale files have identical sets of translation keys."""
        ko_path = LOCALES_DIR / "ko.json"
        en_path = LOCALES_DIR / "en.json"

        with open(ko_path, "r", encoding="utf-8") as f:
            ko_keys = set(json.load(f).keys())

        with open(en_path, "r", encoding="utf-8") as f:
            en_keys = set(json.load(f).keys())

        missing_in_en = ko_keys - en_keys
        missing_in_ko = en_keys - ko_keys

        self.assertEqual(
            missing_in_en, set(), f"Keys missing in en.json: {missing_in_en}"
        )
        self.assertEqual(
            missing_in_ko, set(), f"Keys missing in ko.json: {missing_in_ko}"
        )
