from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget


class CopyableLineEdit(QWidget):
    """Read-only line edit with a compact copy button."""

    copy_requested = Signal(str)

    def __init__(self, copy_tooltip: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._line_edit = QLineEdit(self)
        self._line_edit.setReadOnly(True)

        self._copy_button = QPushButton(self)
        self._copy_button.setObjectName("copyButton")
        self._copy_button.setIcon(_copy_icon())
        self._copy_button.setFixedSize(30, 28)
        self._copy_button.setToolTip(copy_tooltip)
        self._copy_button.setEnabled(False)
        self._copy_button.clicked.connect(self._emit_copy_requested)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._line_edit, stretch=1)
        layout.addWidget(self._copy_button)

    def setText(self, text: str) -> None:
        self._line_edit.setText(text)
        self._copy_button.setEnabled(bool(text.strip()))

    def set_copy_tooltip(self, tooltip: str) -> None:
        self._copy_button.setToolTip(tooltip)

    def text(self) -> str:
        return self._line_edit.text()

    def clear(self) -> None:
        self.setText("")

    def _emit_copy_requested(self) -> None:
        text = self.text()
        if text.strip():
            self.copy_requested.emit(text)


def _copy_icon() -> QIcon:
    pixmap = QPixmap(18, 18)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("#9aa0a6"))
    pen.setWidth(1)
    painter.setPen(pen)
    painter.drawRoundedRect(3, 6, 9, 9, 2, 2)
    painter.drawRoundedRect(6, 3, 9, 9, 2, 2)
    painter.end()
    return QIcon(pixmap)
