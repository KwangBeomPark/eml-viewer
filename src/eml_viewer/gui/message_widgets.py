from __future__ import annotations

import mimetypes
import re
import tempfile
from pathlib import Path
from urllib.parse import unquote

from PySide6.QtWidgets import QTabWidget, QTextBrowser, QVBoxLayout, QWidget

from eml_viewer.models.email_data import ParsedEmail


class MessageBodyWidget(QWidget):
    """Plain Text와 HTML 본문을 나눠서 보여주는 화면입니다."""

    _cid_pattern = re.compile(r"cid:([^\"'\s>)]+)", re.IGNORECASE)
    _invalid_filename_chars = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
    _reserved_windows_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._inline_temp_dir: tempfile.TemporaryDirectory[str] | None = None

        self._tabs = QTabWidget(self)
        self._plain_browser = QTextBrowser(self)
        self._html_browser = QTextBrowser(self)

        self._plain_browser.setOpenExternalLinks(False)
        self._html_browser.setOpenExternalLinks(False)

        self._tabs.addTab(self._plain_browser, "Plain Text")
        self._tabs.addTab(self._html_browser, "HTML")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._tabs)

        self.clear()

    def clear(self) -> None:
        self._clear_inline_temp_dir()
        self._plain_browser.setPlainText("EML 파일을 열면 본문이 여기에 표시됩니다.")
        self._html_browser.setPlainText("HTML 본문이 여기에 표시됩니다.")
        self._tabs.setCurrentIndex(0)

    def set_email(self, email: ParsedEmail) -> None:
        plain_text = email.plain_body.strip() or "Plain Text 본문이 없습니다."
        html_text = email.html_body.strip()

        self._plain_browser.setPlainText(plain_text)
        if html_text:
            self._html_browser.setHtml(self._prepare_html(email))
            self._tabs.setCurrentIndex(1)
        else:
            self._clear_inline_temp_dir()
            self._html_browser.setPlainText("HTML 본문이 없습니다.")
            self._tabs.setCurrentIndex(0)

    def _prepare_html(self, email: ParsedEmail) -> str:
        self._clear_inline_temp_dir()
        if not email.inline_resources:
            return email.html_body

        self._inline_temp_dir = tempfile.TemporaryDirectory(prefix="eml-viewer-inline-")
        temp_root = Path(self._inline_temp_dir.name)
        cid_to_uri: dict[str, str] = {}

        for index, resource in enumerate(email.inline_resources, start=1):
            extension = mimetypes.guess_extension(resource.content_type) or ""
            filename = self._safe_filename(resource.filename or f"inline-{index}{extension}")
            if not Path(filename).suffix and extension:
                filename = f"{filename}{extension}"
            filename = f"{index}-{filename}"
            target_path = temp_root / filename
            target_path.write_bytes(resource.payload)
            cid_to_uri[resource.content_id.lower()] = target_path.as_uri()

        def replace_match(match: re.Match[str]) -> str:
            content_id = unquote(match.group(1)).strip().strip("<>").lower()
            return cid_to_uri.get(content_id, match.group(0))

        return self._cid_pattern.sub(replace_match, email.html_body)

    def _safe_filename(self, filename: str) -> str:
        cleaned = self._invalid_filename_chars.sub("_", filename).strip(" .")
        if cleaned and Path(cleaned).stem.upper() in self._reserved_windows_names:
            cleaned_path = Path(cleaned)
            cleaned = f"{cleaned_path.stem}_{cleaned_path.suffix}" if cleaned_path.suffix else f"{cleaned}_"
        return cleaned or "inline-resource"

    def _clear_inline_temp_dir(self) -> None:
        if self._inline_temp_dir is not None:
            self._inline_temp_dir.cleanup()
            self._inline_temp_dir = None
