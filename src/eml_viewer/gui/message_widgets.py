from __future__ import annotations

import html
import mimetypes
import re
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse

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

    _resource_attr_pattern = re.compile(
        r"(?P<prefix>\b(?:src|background)\s*=\s*)(?P<quote>[\"'])(?P<value>.*?)(?P=quote)",
        re.IGNORECASE | re.DOTALL,
    )
    _css_url_pattern = re.compile(r"url\((?P<quote>[\"']?)(?P<value>.*?)(?P=quote)\)", re.IGNORECASE)
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
        self._plain_notice_label = QLabel("HTML 본문에서 자동 생성한 텍스트입니다.", self)

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
        self._tabs.currentChanged.connect(self._update_plain_notice_visibility)
        self._plain_notice_label.setVisible(False)
        self._plain_notice_label.setObjectName("plainNotice")

        zoom_layout = QHBoxLayout()
        zoom_layout.addStretch(1)
        zoom_layout.addWidget(self._zoom_out_button)
        zoom_layout.addWidget(self._zoom_label)
        zoom_layout.addWidget(self._zoom_in_button)
        zoom_layout.addWidget(self._zoom_reset_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(zoom_layout)
        layout.addWidget(self._plain_notice_label)
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
        self._update_plain_notice_visibility()

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
        self._update_plain_notice_visibility()
        if html_text:
            self._html_browser.setHtml(self._zoomed_html(self._prepare_html(email)))
            self._tabs.setCurrentIndex(1)
        else:
            self._clear_inline_temp_dir()
            self._html_browser.setPlainText("HTML 본문이 없습니다.")
            self._tabs.setCurrentIndex(0)
        self._update_plain_notice_visibility()

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

    def _update_plain_notice_visibility(self) -> None:
        is_plain_tab = self._tabs.currentWidget() == self._plain_browser
        is_generated = bool(self._current_email and self._current_email.plain_body_generated)
        self._plain_notice_label.setVisible(is_plain_tab and is_generated)

    def _prepare_html(self, email: ParsedEmail) -> str:
        self._clear_inline_temp_dir()
        if not email.inline_resources:
            return email.html_body

        self._inline_temp_dir = tempfile.TemporaryDirectory(prefix="eml-viewer-inline-")
        temp_root = Path(self._inline_temp_dir.name)
        resource_to_uri: dict[str, str] = {}

        for index, resource in enumerate(email.inline_resources, start=1):
            extension = mimetypes.guess_extension(resource.content_type) or ""
            filename = self._safe_filename(resource.filename or f"inline-{index}{extension}")
            if not Path(filename).suffix and extension:
                filename = f"{filename}{extension}"
            filename = f"{index}-{filename}"
            target_path = temp_root / filename
            target_path.write_bytes(resource.payload)
            for key in self._resource_keys(resource.content_id):
                resource_to_uri[key] = target_path.as_uri()
            for key in self._resource_keys(resource.content_location):
                resource_to_uri[key] = target_path.as_uri()
            for key in self._resource_keys(resource.filename):
                resource_to_uri[key] = target_path.as_uri()

        unresolved_refs: set[str] = set()

        def resolve_reference(value: str) -> str | None:
            for key in self._resource_keys(value):
                uri = resource_to_uri.get(key)
                if uri:
                    return uri
            if self._looks_like_embedded_reference(value):
                unresolved_refs.add(value)
            return None

        def replace_attr(match: re.Match[str]) -> str:
            value = match.group("value")
            uri = resolve_reference(value)
            if uri is None:
                return match.group(0)
            return f"{match.group('prefix')}{match.group('quote')}{uri}{match.group('quote')}"

        def replace_css_url(match: re.Match[str]) -> str:
            value = match.group("value")
            uri = resolve_reference(value)
            if uri is None:
                return match.group(0)
            quote = match.group("quote") or ""
            return f"url({quote}{uri}{quote})"

        prepared_html = self._resource_attr_pattern.sub(replace_attr, email.html_body)
        prepared_html = self._css_url_pattern.sub(replace_css_url, prepared_html)
        if unresolved_refs:
            prepared_html += self._unresolved_resource_notice(len(unresolved_refs))
        return prepared_html

    def _safe_filename(self, filename: str) -> str:
        cleaned = self._invalid_filename_chars.sub("_", filename).strip(" .")
        if cleaned and Path(cleaned).stem.upper() in self._reserved_windows_names:
            cleaned_path = Path(cleaned)
            cleaned = f"{cleaned_path.stem}_{cleaned_path.suffix}" if cleaned_path.suffix else f"{cleaned}_"
        return cleaned or "inline-resource"

    def _resource_keys(self, value: str) -> set[str]:
        if not value:
            return set()

        cleaned = html.unescape(unquote(str(value))).strip().strip("\"'<>")
        if not cleaned:
            return set()

        lowered = cleaned.lower()
        if lowered.startswith(("http://", "https://", "data:", "mailto:", "#")):
            return set()
        if lowered.startswith("cid:"):
            cleaned = cleaned[4:]
            lowered = cleaned.lower()

        parsed_path = urlparse(cleaned).path or cleaned
        candidates = {
            cleaned,
            lowered,
            cleaned.lstrip("./\\"),
            parsed_path,
            parsed_path.lstrip("./\\"),
            Path(parsed_path.replace("\\", "/")).name,
        }
        return {candidate.strip().strip("<>").lower() for candidate in candidates if candidate.strip()}

    def _looks_like_embedded_reference(self, value: str) -> bool:
        keys = self._resource_keys(value)
        if not keys:
            return False
        lowered = value.lower().strip()
        return lowered.startswith("cid:") or any(
            key.endswith((".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg")) for key in keys
        )

    def _unresolved_resource_notice(self, count: int) -> str:
        return (
            "<hr><p style=\"color:#a15c00; font-size:90%;\">"
            f"표시하지 못한 임베드 이미지 {count}개가 있습니다."
            "</p>"
        )

    def _clear_inline_temp_dir(self) -> None:
        if self._inline_temp_dir is not None:
            self._inline_temp_dir.cleanup()
            self._inline_temp_dir = None
