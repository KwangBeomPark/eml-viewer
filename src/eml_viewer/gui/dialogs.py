from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget


def select_eml_file(parent: QWidget, start_dir: Path | None = None) -> Path | None:
    filename, _ = QFileDialog.getOpenFileName(
        parent,
        "EML 파일 열기",
        str(start_dir or Path.home()),
        "EML 파일 (*.eml);;모든 파일 (*.*)",
    )
    return Path(filename) if filename else None


def select_attachment_destination(parent: QWidget, default_filename: str) -> Path | None:
    filename, _ = QFileDialog.getSaveFileName(
        parent,
        "첨부파일 저장",
        str(Path.home() / default_filename),
        "모든 파일 (*.*)",
    )
    return Path(filename) if filename else None


def ask_overwrite(parent: QWidget, path: Path) -> bool:
    result = QMessageBox.question(
        parent,
        "파일 덮어쓰기 확인",
        f"이미 같은 이름의 파일이 있습니다.\n\n{path}\n\n덮어쓸까요?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return result == QMessageBox.StandardButton.Yes


def ask_execute_file_operation(parent: QWidget, title: str, preview_message: str) -> bool:
    result = QMessageBox.question(
        parent,
        title,
        f"아래 작업을 실행할까요?\n\n{preview_message}",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return result == QMessageBox.StandardButton.Yes


def show_error(parent: QWidget, title: str, message: str) -> None:
    QMessageBox.critical(parent, title, message)


def show_info(parent: QWidget, title: str, message: str) -> None:
    QMessageBox.information(parent, title, message)
