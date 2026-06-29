from __future__ import annotations

import json
import re
import threading
import urllib.parse
import urllib.request


SUPPORTED_TRANSLATION_TARGETS: dict[str, str] = {
    "ko": "Korean",
    "en": "English",
    "pl": "Polish",
}


class TranslationError(Exception):
    """Raised when body translation cannot be completed."""


class TranslationCanceled(Exception):
    """Raised when the user cancels translation."""


class TranslationChunker:
    def __init__(self, max_chars: int = 4000, max_encoded_chars: int = 12000) -> None:
        self.max_chars = max(100, int(max_chars))
        self.max_encoded_chars = max(self.max_chars, int(max_encoded_chars))

    def chunk_text(self, text: str) -> list[str]:
        chunks: list[str] = []
        pending = ""
        for part in self._paragraph_parts(text):
            for piece in self._split_oversized(part):
                pending = self._append_or_flush(pending, piece, chunks)
        if pending.strip():
            chunks.append(pending.strip())
        return [chunk for chunk in chunks if chunk.strip()]

    def _paragraph_parts(self, text: str) -> list[str]:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        return [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]

    def _split_oversized(self, text: str) -> list[str]:
        if self._fits(text):
            return [text]

        pieces: list[str] = []
        for sentence in self._sentence_parts(text):
            if self._fits(sentence):
                pieces.append(sentence)
                continue
            pieces.extend(self._force_split(sentence))
        return pieces

    def _sentence_parts(self, text: str) -> list[str]:
        parts = re.split(r"(?<=[.!?。！？])\s+", text)
        return [part.strip() for part in parts if part.strip()]

    def _force_split(self, text: str) -> list[str]:
        pieces: list[str] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + self.max_chars)
            piece = text[start:end].strip()
            if piece:
                pieces.append(piece)
            start = end
        return pieces

    def _append_or_flush(self, pending: str, piece: str, chunks: list[str]) -> str:
        if not pending:
            return piece

        candidate = f"{pending}\n\n{piece}"
        if self._fits(candidate):
            return candidate

        chunks.append(pending.strip())
        return piece

    def _fits(self, text: str) -> bool:
        if len(text) > self.max_chars:
            return False
        return len(urllib.parse.urlencode({"q": text})) <= self.max_encoded_chars


class TranslationService:
    _endpoint = "https://translate.googleapis.com/translate_a/single"

    def __init__(
        self,
        opener=None,
        chunker: TranslationChunker | None = None,
        timeout_seconds: int = 20,
    ) -> None:
        self._opener = opener or urllib.request.urlopen
        self._chunker = chunker or TranslationChunker()
        self._timeout_seconds = timeout_seconds

    def translate_text(
        self,
        text: str,
        target_language: str,
        progress_callback=None,
        cancel_event: threading.Event | None = None,
    ) -> str:
        target_language = target_language.strip().lower()
        if target_language not in SUPPORTED_TRANSLATION_TARGETS:
            raise TranslationError(f"Unsupported translation target: {target_language}")

        chunks = self._chunker.chunk_text(text)
        if not chunks:
            return ""

        translated_chunks: list[str] = []
        total = len(chunks)
        for index, chunk in enumerate(chunks, start=1):
            if cancel_event is not None and cancel_event.is_set():
                raise TranslationCanceled()
            translated_chunks.append(self._translate_chunk(chunk, target_language))
            if progress_callback is not None:
                progress_callback(index, total)
        return "\n\n".join(translated_chunks)

    def _translate_chunk(self, chunk: str, target_language: str) -> str:
        params = urllib.parse.urlencode(
            {
                "client": "gtx",
                "sl": "auto",
                "tl": target_language,
                "dt": "t",
                "q": chunk,
            }
        )
        request = urllib.request.Request(
            f"{self._endpoint}?{params}",
            headers={"User-Agent": "Mozilla/5.0 EML Viewer"},
        )
        try:
            with self._opener(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except TranslationError:
            raise
        except Exception as exc:
            raise TranslationError(f"Translation request failed: {exc}") from exc

        return self._parse_response(payload)

    def _parse_response(self, payload: object) -> str:
        if not isinstance(payload, list) or not payload or not isinstance(payload[0], list):
            raise TranslationError("Translation response was not in the expected format.")

        translated_parts: list[str] = []
        for segment in payload[0]:
            if isinstance(segment, list) and segment and isinstance(segment[0], str):
                translated_parts.append(segment[0])

        translated = "".join(translated_parts).strip()
        if not translated:
            raise TranslationError("Translation response was empty.")
        return translated
