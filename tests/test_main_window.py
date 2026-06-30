from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --disable-software-rasterizer --no-sandbox")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication

from eml_viewer.gui import dialogs
from eml_viewer.gui.i18n import set_language
from eml_viewer.gui.main_window import MainWindow
from eml_viewer.models.email_data import ParsedEmail
from eml_viewer.services.attachment_service import AttachmentService
from eml_viewer.services.eml_parser import EmlParser
from eml_viewer.services.file_operation_service import FileOperationService
from eml_viewer.services.settings_service import SettingsService
from eml_viewer.services.update_service import UpdateCheckResult


class FakeUpdateService:
    def __init__(self, result: UpdateCheckResult) -> None:
        self._result = result

    def check_for_updates(self) -> UpdateCheckResult:
        return self._result


class FakeTranslationService:
    def __init__(self, result: str | Exception) -> None:
        self._result = result
        self.calls: list[tuple[str, str, str]] = []

    def translate_text(self, text: str, target_language: str, progress_callback=None, cancel_event=None) -> str:
        self.calls.append(("text", text, target_language))
        if isinstance(self._result, Exception):
            raise self._result
        if progress_callback is not None:
            progress_callback(1, 1)
        return self._result

    def translate_html_text(self, text: str, target_language: str, progress_callback=None, cancel_event=None) -> str:
        self.calls.append(("html", text, target_language))
        if isinstance(self._result, Exception):
            raise self._result
        if progress_callback is not None:
            progress_callback(1, 1)
        return self._result


class MainWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        set_language("en")

    def tearDown(self) -> None:
        set_language("ko")

    def _window(
        self,
        update_result: UpdateCheckResult,
        translation_service: FakeTranslationService | None = None,
    ) -> MainWindow:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        parser = EmlParser()
        file_operations = FileOperationService()
        settings = SettingsService(Path(temp_dir.name) / "settings.json")
        window = MainWindow(
            parser=parser,
            attachment_service=AttachmentService(parser, file_operations),
            settings_service=settings,
            file_operation_service=file_operations,
            update_service=FakeUpdateService(update_result),
            translation_service=translation_service,
        )
        self.addCleanup(window.close)
        if window._update_check_thread is not None:
            window._update_check_thread.wait(5000)
            QApplication.processEvents()
        return window

    def test_update_banner_shows_only_when_update_is_available(self) -> None:
        window = self._window(UpdateCheckResult("0.1.4", "0.1.5", "https://example.com", None))

        self.assertFalse(window._update_banner.isHidden())
        self.assertIn("0.1.5", window._update_banner_label.text())

    def test_update_banner_stays_hidden_when_current_version_is_latest(self) -> None:
        window = self._window(UpdateCheckResult("0.1.4", "0.1.4", "https://example.com", None))

        self.assertTrue(window._update_banner.isHidden())

    def test_forward_button_enables_after_email_with_source_path_is_displayed(self) -> None:
        window = self._window(UpdateCheckResult("0.1.4", "0.1.4", "https://example.com", None))
        self.assertFalse(window._forward_button.isEnabled())

        email = ParsedEmail(
            subject="Hello",
            sender="sender@example.com",
            recipients="receiver@example.com",
            date="2026-06-27",
            plain_body="Body",
            html_body="",
            source_path=Path("sample.eml"),
        )

        window._display_email(email)

        self.assertTrue(window._forward_button.isEnabled())

    def test_english_language_updates_main_labels_and_menus(self) -> None:
        window = self._window(UpdateCheckResult("0.1.4", "0.1.4", "https://example.com", None))

        self.assertEqual(window._file_menu.title(), "File")
        self.assertEqual(window._help_menu.title(), "Help")
        self.assertEqual(window._open_button.text(), "Open EML file")
        self.assertEqual(window._subject_label.text(), "Subject")
        self.assertEqual(window._sender_label.text(), "Sender")
        self.assertEqual(window._metadata_group.title(), "Email information")
        self.assertEqual(window._body_widget._target_language_combo.currentData(), "en")

    def test_translate_button_enables_after_email_is_displayed(self) -> None:
        window = self._window(UpdateCheckResult("0.1.4", "0.1.4", "https://example.com", None))
        self.assertFalse(window._body_widget._translate_button.isEnabled())

        window._display_email(
            ParsedEmail(
                subject="Hello",
                sender="sender@example.com",
                recipients="receiver@example.com",
                date="2026-06-27",
                plain_body="Body",
                html_body="",
                source_path=Path("sample.eml"),
            )
        )

        self.assertTrue(window._body_widget._translate_button.isEnabled())

    def test_translation_service_result_populates_translation_tab(self) -> None:
        fake_translation = FakeTranslationService("Translated body")
        window = self._window(
            UpdateCheckResult("0.1.4", "0.1.4", "https://example.com", None),
            translation_service=fake_translation,
        )
        window._translation_privacy_confirmed = True
        window._display_email(
            ParsedEmail(
                subject="Hello",
                sender="sender@example.com",
                recipients="receiver@example.com",
                date="2026-06-27",
                plain_body="Body",
                html_body="",
                source_path=Path("sample.eml"),
            )
        )

        window._translate_body("Body", "pl")
        self._wait_for_translation(window)

        self.assertEqual(fake_translation.calls, [("text", "Body", "pl")])
        self.assertEqual(window._body_widget._last_translation_result, "Translated body")
        self.assertEqual(window._body_widget._last_translation_format, "text")
        self.assertEqual(window._body_widget._tabs.currentWidget(), window._body_widget._translation_view)
        self.assertTrue(window._body_widget._translate_button.isEnabled())

    def test_html_translation_uses_prepared_html_source(self) -> None:
        fake_translation = FakeTranslationService('<html><body><p>Translated</p><img src="file:///logo.png"></body></html>')
        window = self._window(
            UpdateCheckResult("0.1.4", "0.1.4", "https://example.com", None),
            translation_service=fake_translation,
        )
        window._translation_privacy_confirmed = True
        window._display_email(
            ParsedEmail(
                subject="Hello",
                sender="sender@example.com",
                recipients="receiver@example.com",
                date="2026-06-27",
                plain_body="Body",
                html_body='<html><body><p>Body</p><img src="https://example.com/logo.png"></body></html>',
                source_path=Path("sample.eml"),
            )
        )

        window._translate_body(
            window._body_widget.source_text_for_translation(),
            "pl",
            window._body_widget.source_format_for_translation(),
        )
        self._wait_for_translation(window)

        self.assertEqual(fake_translation.calls[0][0], "html")
        self.assertIn("data:image/gif", fake_translation.calls[0][1])
        self.assertEqual(window._body_widget._last_translation_format, "html")
        self.assertIn("Translated", window._body_widget._last_translation_result)

    def test_translation_failure_reenables_button_for_retry(self) -> None:
        fake_translation = FakeTranslationService(RuntimeError("network down"))
        window = self._window(
            UpdateCheckResult("0.1.4", "0.1.4", "https://example.com", None),
            translation_service=fake_translation,
        )
        window._translation_privacy_confirmed = True
        window._display_email(
            ParsedEmail(
                subject="Hello",
                sender="sender@example.com",
                recipients="receiver@example.com",
                date="2026-06-27",
                plain_body="Body",
                html_body="",
                source_path=Path("sample.eml"),
            )
        )
        errors: list[tuple[str, str]] = []
        original_show_error = dialogs.show_error
        dialogs.show_error = lambda parent, title, message: errors.append((title, message))
        self.addCleanup(lambda: setattr(dialogs, "show_error", original_show_error))

        window._translate_body("Body", "ko")
        self._wait_for_translation(window)

        self.assertTrue(window._body_widget._translate_button.isEnabled())
        self.assertEqual(fake_translation.calls, [("text", "Body", "ko")])
        self.assertTrue(errors)
        self.assertIn("try again", errors[0][1])

    def _wait_for_translation(self, window: MainWindow) -> None:
        thread = window._translation_thread
        if thread is None:
            return
        for _ in range(100):
            if not thread.isRunning():
                break
            thread.wait(20)
            QApplication.processEvents()
        QApplication.processEvents()


if __name__ == "__main__":
    unittest.main()
