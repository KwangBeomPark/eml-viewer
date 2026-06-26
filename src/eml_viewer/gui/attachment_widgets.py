from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from eml_viewer.models.attachment_data import AttachmentInfo


class AttachmentPanel(QWidget):
    """첨부파일 목록과 저장 버튼을 가진 화면입니다."""

    save_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._attachments: list[AttachmentInfo] = []
        self._expanded = False

        self._title_label = QLabel("첨부파일", self)
        self._toggle_button = QPushButton("Show", self)
        self._table = QTableWidget(0, 3, self)
        self._save_button = QPushButton("선택한 첨부 저장", self)

        self._table.setHorizontalHeaderLabels(["파일명", "종류", "크기"])
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().setVisible(False)

        self._toggle_button.clicked.connect(self._toggle_expanded)
        self._save_button.setEnabled(False)
        self._save_button.clicked.connect(self._emit_save_requested)
        self._table.itemSelectionChanged.connect(self._update_button_state)

        header_layout = QHBoxLayout()
        header_layout.addWidget(self._title_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self._toggle_button)
        header_layout.addWidget(self._save_button)

        layout = QVBoxLayout(self)
        layout.addLayout(header_layout)
        layout.addWidget(self._table)
        self.setVisible(False)

    def set_attachments(self, attachments: list[AttachmentInfo]) -> None:
        self._attachments = list(attachments)
        self._expanded = False
        self._table.setRowCount(len(self._attachments))

        for row, attachment in enumerate(self._attachments):
            filename_item = QTableWidgetItem(attachment.filename)
            filename_item.setData(Qt.ItemDataRole.UserRole, attachment.index)

            self._table.setItem(row, 0, filename_item)
            self._table.setItem(row, 1, QTableWidgetItem(attachment.content_type))
            self._table.setItem(row, 2, QTableWidgetItem(attachment.display_size))

        self._table.resizeColumnsToContents()
        self._update_summary()
        self._apply_expanded_state()
        self._update_button_state()

    def clear(self) -> None:
        self.set_attachments([])

    def current_attachment(self) -> AttachmentInfo | None:
        selected_rows = self._table.selectionModel().selectedRows()
        if not selected_rows:
            return None

        row = selected_rows[0].row()
        if row < 0 or row >= len(self._attachments):
            return None
        return self._attachments[row]

    def _update_button_state(self) -> None:
        self._save_button.setEnabled(self._expanded and self.current_attachment() is not None)

    def _emit_save_requested(self) -> None:
        attachment = self.current_attachment()
        if attachment is not None:
            self.save_requested.emit(attachment)

    def _toggle_expanded(self) -> None:
        self._expanded = not self._expanded
        self._apply_expanded_state()
        self._update_button_state()

    def _update_summary(self) -> None:
        count = len(self._attachments)
        total_size = sum(max(0, attachment.size) for attachment in self._attachments)
        self._title_label.setText(f"Attachments {count} · {self._display_size(total_size)}")

    def _apply_expanded_state(self) -> None:
        has_attachments = bool(self._attachments)
        self.setVisible(has_attachments)
        self._table.setVisible(has_attachments and self._expanded)
        self._save_button.setVisible(has_attachments and self._expanded)
        self._toggle_button.setVisible(has_attachments)
        self._toggle_button.setText("Hide" if self._expanded else "Show")

        if not has_attachments:
            self.setMaximumHeight(0)
            return

        if not self._expanded:
            self.setMaximumHeight(48)
            return

        row_height = 30
        table_header = 34
        panel_header = 42
        max_visible_rows = min(len(self._attachments), 6)
        self.setMaximumHeight(panel_header + table_header + (max_visible_rows * row_height))

    def _display_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.1f} MB"
