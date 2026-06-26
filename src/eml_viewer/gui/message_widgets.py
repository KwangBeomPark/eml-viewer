from __future__ import annotations

import mimetypes
import re
import tempfile
from pathlib import Path
from urllib.parse import unquote

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from eml_viewer.models.email_data import ParsedEmail


class ZoomTextBrowser(QTextBrowser):
    """QTextBrowser with Ctrl+mouse-wheel zoom requests."""

    zoom_delta_requested = Signal(int)

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta:
                self.zoom_delta_requested.emit(1 if delta > 0 else -1)
                event.accept()
                return

        super().wheelEvent(event)


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
        self._current_email: ParsedEmail | None = None
        self._base_point_size = self.font().pointSizeF() or 10.0
        self._zoom_percent = 100

        self._tabs = QTabWidget(self)
        self._plain_browser = ZoomTextBrowser(self)
        self._html_browser = ZoomTextBrowser(self)
        self._zoom_out_button = QPushButton("-", self)
        self._zoom_in_button = QPushButton("+", self)
        self._zoom_reset_button = QPushButton("100%", self)
        self._zoom_label = QLabel("100%", self)

        self._plain_browser.setOpenExternalLinks(False)
        self._html_browser.setOpenExternalLinks(False)
        self._plain_browser.zoom_delta_requested.connect(self._change_zoom_by_steps)
        self._html_browser.zoom_delta_requested.connect(self._change_zoom_by_steps)
        self._zoom_out_button.clicked.connect(lambda: self._change_zoom_by_steps(-1))
        self._zoom_in_button.clicked.connect(lambda: self._change_zoom_by_steps(1))
        self._zoom_reset_button.clicked.connect(self.reset_zoom)

        reset_shortcut = QShortcut(QKeySequence("Ctrl+0"), self)
        reset_shortcut.activated.connect(self.reset_zoom)
        self._reset_zoom_shortcut = reset_shortcut

        for button in (self._zoom_out_button, self._zoom_in_button, self._zoom_reset_button):
            button.setFixedWidth(52)
        self._zoom_label.setMinimumWidth(46)
        self._zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._tabs.addTab(self._plain_browser, "Plain Text")
        self._tabs.addTab(self._html_browser, "HTML")

        zoom_layout = QHBoxLayout()
        zoom_layout.addStretch(1)
        zoom_layout.addWidget(self._zoom_out_button)
        zoom_layout.addWidget(self._zoom_label)
        zoom_layout.addWidget(self._zoom_in_button)
        zoom_layout.addWidget(self._zoom_reset_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(zoom_layout)
        layout.addWidget(self._tabs)

        self.clear()

    def clear(self) -> None:
        self._current_email = None
        self._clear_inline_temp_dir()
        self._zoom_percent = 100
        self._apply_zoom_controls()
        self._plain_browser.setPlainText("EML 파일을 열면 본문이 여기에 표시됩니다.")
        self._html_browser.setPlainText("HTML 본문이 여기에 표시됩니다.")
        self._tabs.setCurrentIndex(0)

    def set_email(self, email: ParsedEmail) -> None:
        self._current_email = email
        self._render_email()

    @property
    def zoom_percent(self) -> int:
        return self._zoom_percent

    def reset_zoom(self) -> None:
        self.set_zoom_percent(100)

    def set_zoom_percent(self, percent: int) -> None:
        percent = max(50, min(200, int(percent)))
        if percent == self._zoom_percent:
            self._apply_zoom_controls()
            return

        self._zoom_percent = percent
        self._apply_zoom_controls()
        if self._current_email is not None:
            self._render_email()

    def _change_zoom_by_steps(self, steps: int) -> None:
        self.set_zoom_percent(self._zoom_percent + (steps * 25))

    def _render_email(self) -> None:
        if self._current_email is None:
            return

        email = self._current_email
        plain_text = email.plain_body.strip() or "Plain Text 본문이 없습니다."
        html_text = email.html_body.strip()

        self._plain_browser.setPlainText(plain_text)
        if html_text:
            self._html_browser.setHtml(self._zoomed_html(self._prepare_html(email)))
            self._tabs.setCurrentIndex(1)
        else:
            self._clear_inline_temp_dir()
            self._html_browser.setPlainText("HTML 본문이 없습니다.")
            self._tabs.setCurrentIndex(0)

    def _apply_zoom_controls(self) -> None:
        self._zoom_label.setText(f"{self._zoom_percent}%")
        self._zoom_out_button.setEnabled(self._zoom_percent > 50)
        self._zoom_in_button.setEnabled(self._zoom_percent < 200)
        point_size = self._base_point_size * self._zoom_percent / 100
        style = f"QTextBrowser {{ font-size: {point_size:.1f}pt; }}"
        self._plain_browser.setStyleSheet(style)
        self._html_browser.setStyleSheet(style)

    def _zoomed_html(self, html: str) -> str:
        style = f"<style>body {{ font-size: {self._zoom_percent}%; }}</style>"
        if re.search(r"</head>", html, re.IGNORECASE):
            return re.sub(r"</head>", f"{style}</head>", html, count=1, flags=re.IGNORECASE)
        return f"{style}{html}"

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
