from __future__ import annotations

import json
import sys
import threading
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eml_viewer.services.translation_service import (
    TranslationCanceled,
    TranslationChunker,
    TranslationError,
    TranslationService,
)


class FakeResponse:
    def __init__(self, payload: object) -> None:
        self._data = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return self._data


class TranslationChunkerTest(unittest.TestCase):
    def test_chunks_do_not_exceed_4000_characters(self) -> None:
        chunker = TranslationChunker(max_chars=4000)

        chunks = chunker.chunk_text("a" * 9500)

        self.assertTrue(chunks)
        self.assertTrue(all(len(chunk) <= 4000 for chunk in chunks))

    def test_paragraph_order_is_preserved(self) -> None:
        chunker = TranslationChunker(max_chars=4000)
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."

        chunks = chunker.chunk_text(text)

        self.assertEqual(chunks, [text])

    def test_long_sentences_are_force_split(self) -> None:
        chunker = TranslationChunker(max_chars=4000)
        text = "Long " + ("word" * 1200)

        chunks = chunker.chunk_text(text)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 4000 for chunk in chunks))


class TranslationServiceTest(unittest.TestCase):
    def test_translate_text_merges_google_response_chunks(self) -> None:
        calls: list[str] = []

        def fake_opener(request, timeout):
            calls.append(request.full_url)
            return FakeResponse([[["Translated", "Original"], [" text", " text"]]])

        service = TranslationService(opener=fake_opener, chunker=TranslationChunker(max_chars=100))
        progress: list[tuple[int, int]] = []
        text = ("a" * 80) + "\n\n" + ("b" * 80)

        translated = service.translate_text(
            text,
            "ko",
            progress_callback=lambda done, total: progress.append((done, total)),
        )

        self.assertIn("tl=ko", calls[0])
        self.assertEqual(translated, "Translated text\n\nTranslated text")
        self.assertEqual(progress[-1], (2, 2))

    def test_supported_target_languages_are_allowed(self) -> None:
        def fake_opener(request, timeout):
            return FakeResponse([[["ok", "x"]]])

        service = TranslationService(opener=fake_opener)

        self.assertEqual(service.translate_text("hello", "ko"), "ok")
        self.assertEqual(service.translate_text("hello", "en"), "ok")
        self.assertEqual(service.translate_text("hello", "pl"), "ok")

    def test_unsupported_target_language_raises_translation_error(self) -> None:
        service = TranslationService(opener=lambda request, timeout: FakeResponse([[["ok", "x"]]]))

        with self.assertRaises(TranslationError):
            service.translate_text("hello", "ja")

    def test_http_error_becomes_translation_error(self) -> None:
        def fake_opener(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", None, None)

        service = TranslationService(opener=fake_opener)

        with self.assertRaises(TranslationError):
            service.translate_text("hello", "ko")

    def test_malformed_json_becomes_translation_error(self) -> None:
        class BadResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback) -> None:
                return None

            def read(self) -> bytes:
                return b"{bad json"

        service = TranslationService(opener=lambda request, timeout: BadResponse())

        with self.assertRaises(TranslationError):
            service.translate_text("hello", "ko")

    def test_empty_response_becomes_translation_error(self) -> None:
        service = TranslationService(opener=lambda request, timeout: FakeResponse([[["", "x"]]]))

        with self.assertRaises(TranslationError):
            service.translate_text("hello", "ko")

    def test_cancel_event_stops_before_next_request(self) -> None:
        cancel_event = threading.Event()
        calls = 0

        def fake_opener(request, timeout):
            nonlocal calls
            calls += 1
            cancel_event.set()
            return FakeResponse([[["ok", "x"]]])

        service = TranslationService(opener=fake_opener, chunker=TranslationChunker(max_chars=100))

        with self.assertRaises(TranslationCanceled):
            service.translate_text(("a" * 80) + "\n\n" + ("b" * 80), "ko", cancel_event=cancel_event)
        self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
