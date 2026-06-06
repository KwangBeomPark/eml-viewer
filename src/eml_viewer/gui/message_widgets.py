from __future__ import annotations

from PySide6.QtWidgets import QTabWidget, QTextBrowser, QVBoxLayout, QWidget

from eml_viewer.models.email_data import ParsedEmail


class MessageBodyWidget(QWidget):
    """Plain Text와 HTML 본문을 나눠서 보여주는 화면입니다."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

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
        self._plain_browser.setPlainText("EML 파일을 열면 본문이 여기에 표시됩니다.")
        self._html_browser.setPlainText("HTML 본문이 여기에 표시됩니다.")
        self._tabs.setCurrentIndex(0)

    def set_email(self, email: ParsedEmail) -> None:
        plain_text = email.plain_body.strip() or "Plain Text 본문이 없습니다."
        html_text = email.html_body.strip()

        self._plain_browser.setPlainText(plain_text)
        if html_text:
            self._html_browser.setHtml(html_text)
            self._tabs.setCurrentIndex(1)
        else:
            self._html_browser.setPlainText("HTML 본문이 없습니다.")
            self._tabs.setCurrentIndex(0)
