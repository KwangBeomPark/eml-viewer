from __future__ import annotations

from PySide6.QtCore import Signal, QTimer
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QToolTip, QWidget


class CopyableLineEdit(QWidget):
    """Read-only line edit with a compact copy button."""

    copy_requested = Signal(str)

    def __init__(
        self,
        copy_tooltip: str,
        copied_tooltip: str = "Copied",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._copy_tooltip = copy_tooltip
        self._copied_tooltip = copied_tooltip
        self._line_edit = QLineEdit(self)
        self._line_edit.setReadOnly(True)

        self._copy_button = QPushButton(self)
        self._copy_button.setObjectName("copyButton")
        self._copy_button.setIcon(_copy_icon())
        self._copy_button.setFixedSize(30, 28)
        self._copy_button.setToolTip(self._copy_tooltip)
        self._copy_button.setEnabled(False)
        self._copy_button.clicked.connect(self._emit_copy_requested)

        self._copy_restore_timer = QTimer(self)
        self._copy_restore_timer.setSingleShot(True)
        self._copy_restore_timer.setInterval(3000)
        self._copy_restore_timer.timeout.connect(self._restore_copy_button)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._copy_button)
        layout.addWidget(self._line_edit, stretch=1)

    def setText(self, text: str) -> None:
        self._line_edit.setText(text)
        self._copy_button.setEnabled(bool(text.strip()))

    def set_copy_tooltip(self, tooltip: str) -> None:
        self._copy_tooltip = tooltip
        self._copy_button.setToolTip(tooltip)

    def set_copied_tooltip(self, tooltip: str) -> None:
        self._copied_tooltip = tooltip

    def text(self) -> str:
        return self._line_edit.text()

    def clear(self) -> None:
        self.setText("")

    def _emit_copy_requested(self) -> None:
        text = self.text()
        if text.strip():
            self.copy_requested.emit(text)
            self._show_copy_feedback()

    def _show_copy_feedback(self) -> None:
        self._copy_restore_timer.start()
        self._copy_button.setIcon(_copied_icon())
        self._copy_button.setToolTip(self._copied_tooltip)
        QToolTip.showText(
            self._copy_button.mapToGlobal(self._copy_button.rect().bottomLeft()),
            self._copied_tooltip,
            self._copy_button,
        )

    def _restore_copy_button(self) -> None:
        self._copy_button.setIcon(_copy_icon())
        self._copy_button.setToolTip(self._copy_tooltip)
        QToolTip.hideText()


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


def _copied_icon() -> QIcon:
    pixmap = QPixmap(18, 18)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("#2f9e44"))
    pen.setWidth(2)
    painter.setPen(pen)
    painter.drawLine(3, 9, 7, 13)
    painter.drawLine(7, 13, 15, 4)
    painter.end()
    return QIcon(pixmap)
