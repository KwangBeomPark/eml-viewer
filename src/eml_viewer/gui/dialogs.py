from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from eml_viewer.gui.i18n import tr


def select_eml_file(parent: QWidget, start_dir: Path | None = None) -> Path | None:
    filename, _ = QFileDialog.getOpenFileName(
        parent,
        tr("dialog.open_eml.title"),
        str(start_dir or Path.home()),
        tr("dialog.open_eml.filter"),
    )
    return Path(filename) if filename else None


def select_attachment_destination(parent: QWidget, default_filename: str) -> Path | None:
    filename, _ = QFileDialog.getSaveFileName(
        parent,
        tr("dialog.save_attachment.title"),
        str(Path.home() / default_filename),
        tr("dialog.save_attachment.filter"),
    )
    return Path(filename) if filename else None


def select_attachment_directory(parent: QWidget) -> Path | None:
    directory = QFileDialog.getExistingDirectory(
        parent,
        tr("dialog.save_attachment_dir.title"),
        str(Path.home()),
    )
    return Path(directory) if directory else None


def ask_overwrite(parent: QWidget, path: Path) -> bool:
    result = QMessageBox.question(
        parent,
        tr("dialog.overwrite.title"),
        tr("dialog.overwrite.body", path=path),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return result == QMessageBox.StandardButton.Yes


def ask_execute_file_operation(parent: QWidget, title: str, preview_message: str) -> bool:
    result = QMessageBox.question(
        parent,
        title,
        tr("dialog.execute.body", preview_message=preview_message),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return result == QMessageBox.StandardButton.Yes


def show_error(parent: QWidget, title: str, message: str) -> None:
    QMessageBox.critical(parent, title, message)


def show_info(parent: QWidget, title: str, message: str) -> None:
    QMessageBox.information(parent, title, message)
