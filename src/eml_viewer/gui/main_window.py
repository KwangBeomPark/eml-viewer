from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QThread, Signal
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from eml_viewer.gui import dialogs
from eml_viewer.gui.attachment_widgets import AttachmentPanel
from eml_viewer.gui.message_widgets import MessageBodyWidget
from eml_viewer.models.attachment_data import AttachmentInfo
from eml_viewer.models.email_data import ParsedEmail
from eml_viewer.services.attachment_service import AttachmentService
from eml_viewer.services.eml_parser import EmlParser
from eml_viewer.services.error_service import ErrorService
from eml_viewer.services.file_operation_service import FileOperationService
from eml_viewer.services.settings_service import SettingsService
from eml_viewer.services.update_service import UpdateCheckError, UpdateService


class DownloadThread(QThread):
    progress = Signal(int, int)  # downloaded, total
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, service: UpdateService, url: str, dest_path: str) -> None:
        super().__init__()
        self._service = service
        self._url = url
        self._dest_path = dest_path
        import threading
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def run(self) -> None:
        try:
            self._service.download_installer(
                url=self._url,
                dest_path=self._dest_path,
                progress_callback=self._progress_callback,
                cancel_event=self._cancel_event,
            )
            if not self._cancel_event.is_set():
                self.finished.emit(self._dest_path)
        except Exception as exc:
            self.failed.emit(str(exc))

    def _progress_callback(self, downloaded: int, total: int) -> None:
        self.progress.emit(downloaded, total)


class MainWindow(QMainWindow):
    """EML Viewer의 메인 화면입니다."""

    def __init__(
        self,
        parser: EmlParser,
        attachment_service: AttachmentService,
        settings_service: SettingsService,
        file_operation_service: FileOperationService,
        update_service: UpdateService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._parser = parser
        self._attachment_service = attachment_service
        self._settings_service = settings_service
        self._file_operation_service = file_operation_service
        self._update_service = update_service or UpdateService()
        self._current_email: ParsedEmail | None = None
        self._download_thread: DownloadThread | None = None

        self._subject_edit = self._readonly_line_edit()
        self._sender_edit = self._readonly_line_edit()
        self._recipients_edit = self._readonly_line_edit()
        self._date_edit = self._readonly_line_edit()
        self._current_file_label = QLabel("열린 파일 없음", self)
        self._body_widget = MessageBodyWidget(self)
        self._attachment_panel = AttachmentPanel(self)

        self.setWindowTitle("EML Viewer")
        self._build_actions()
        self._build_ui()
        self._restore_window_geometry()

        self._attachment_panel.save_requested.connect(self._save_attachment)

    def _build_actions(self) -> None:
        open_action = QAction("EML 열기", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file)

        exit_action = QAction("종료", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)

        file_menu = self.menuBar().addMenu("파일")
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        update_action = QAction("업데이트 확인", self)
        update_action.triggered.connect(self._check_for_updates)

        help_menu = self.menuBar().addMenu("도움말")
        help_menu.addAction(update_action)

        toolbar = self.addToolBar("기본")
        toolbar.setMovable(False)
        toolbar.addAction(open_action)

    def _build_ui(self) -> None:
        open_button = QPushButton("EML 파일 열기", self)
        open_button.clicked.connect(self._open_file)

        top_layout = QHBoxLayout()
        top_layout.addWidget(open_button)
        top_layout.addWidget(self._current_file_label, stretch=1)

        metadata_group = QGroupBox("이메일 정보", self)
        metadata_layout = QFormLayout(metadata_group)
        metadata_layout.addRow("제목", self._subject_edit)
        metadata_layout.addRow("보낸 사람", self._sender_edit)
        metadata_layout.addRow("받는 사람", self._recipients_edit)
        metadata_layout.addRow("날짜", self._date_edit)

        splitter = QSplitter(Qt.Orientation.Vertical, self)
        splitter.addWidget(self._body_widget)
        splitter.addWidget(self._attachment_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        content_layout = QVBoxLayout()
        content_layout.addLayout(top_layout)
        content_layout.addWidget(metadata_group)
        content_layout.addWidget(splitter, stretch=1)

        central_widget = QWidget(self)
        central_widget.setLayout(content_layout)
        self.setCentralWidget(central_widget)
        self.statusBar().showMessage("EML 파일을 선택해 주세요.")

    def _readonly_line_edit(self) -> QLineEdit:
        line_edit = QLineEdit(self)
        line_edit.setReadOnly(True)
        return line_edit

    def _open_file(self) -> None:
        path = dialogs.select_eml_file(self)
        if path is None:
            return
        self.load_email(path)

    def load_email(self, path: str | Path) -> None:
        try:
            parsed_email = self._parser.parse_file(path)
        except Exception as exc:
            self._show_error("EML 파일 열기 실패", exc)
            return

        self._current_email = parsed_email
        self._display_email(parsed_email)
        self.statusBar().showMessage(f"파일을 열었습니다: {parsed_email.source_path}")

    def _display_email(self, email: ParsedEmail) -> None:
        self._subject_edit.setText(email.subject)
        self._sender_edit.setText(email.sender)
        self._recipients_edit.setText(email.recipients)
        self._date_edit.setText(email.date)
        self._current_file_label.setText(str(email.source_path or ""))
        self._body_widget.set_email(email)
        self._attachment_panel.set_attachments(email.attachments)

    def _save_attachment(self, attachment: AttachmentInfo) -> None:
        if self._current_email is None or self._current_email.source_path is None:
            dialogs.show_error(self, "첨부파일 저장 실패", "먼저 EML 파일을 열어 주세요.")
            return

        safe_filename = self._file_operation_service.sanitize_filename(attachment.filename)
        destination = dialogs.select_attachment_destination(self, safe_filename)
        if destination is None:
            return

        preview = self._attachment_service.create_save_preview(attachment, destination)
        if not dialogs.ask_execute_file_operation(self, "첨부파일 저장 확인", preview.message):
            self.statusBar().showMessage("첨부파일 저장을 취소했습니다.")
            return
        overwrite = preview.will_overwrite

        try:
            saved_path = self._attachment_service.save_attachment(
                email_path=self._current_email.source_path,
                attachment_index=attachment.index,
                destination_path=preview.destination,
                overwrite=overwrite,
            )
        except Exception as exc:
            self._show_error("첨부파일 저장 실패", exc)
            return

        dialogs.show_info(self, "첨부파일 저장 완료", f"첨부파일을 저장했습니다.\n\n{saved_path}")
        self.statusBar().showMessage(f"첨부파일을 저장했습니다: {saved_path}")

    def _restore_window_geometry(self) -> None:
        settings = self._settings_service.load_settings()
        self.setGeometry(
            settings.window_x,
            settings.window_y,
            settings.window_width,
            settings.window_height,
        )

    def closeEvent(self, event) -> None:
        if self._download_thread is not None and self._download_thread.isRunning():
            self._download_thread.cancel()
            self._download_thread.wait()
        try:
            geometry = self.geometry()
            self._settings_service.save_window_geometry(
                x=geometry.x(),
                y=geometry.y(),
                width=geometry.width(),
                height=geometry.height(),
            )
        except Exception:
            pass
        super().closeEvent(event)

    def _show_error(self, title: str, error: Exception) -> None:
        dialogs.show_error(self, title, ErrorService.to_user_message(error))

    def _check_for_updates(self) -> None:
        self.statusBar().showMessage("업데이트를 확인하는 중입니다.")
        try:
            result = self._update_service.check_for_updates()
        except UpdateCheckError as exc:
            dialogs.show_error(self, "업데이트 확인 실패", str(exc))
            self.statusBar().showMessage("업데이트 확인에 실패했습니다.")
            return

        if not result.update_available:
            dialogs.show_info(
                self,
                "업데이트 확인",
                f"현재 최신 버전을 사용 중입니다.\n\n현재 버전: {result.current_version}",
            )
            self.statusBar().showMessage("현재 최신 버전입니다.")
            return

        message = (
            "새 버전이 있습니다.\n\n"
            f"현재 버전: {result.current_version}\n"
            f"최신 버전: {result.latest_version}\n\n"
            "업데이트를 다운로드하고 설치하시겠습니까?"
        )
        answer = QMessageBox.question(
            self,
            "업데이트 가능",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer == QMessageBox.StandardButton.Yes and result.download_url:
            if result.download_url.lower().endswith(".exe"):
                self._start_update_download(result.download_url)
            else:
                QDesktopServices.openUrl(QUrl(result.download_url))
                self.statusBar().showMessage("업데이트 확인을 완료했습니다.")
        else:
            self.statusBar().showMessage("업데이트 확인을 완료했습니다.")

    def _start_update_download(self, url: str) -> None:
        import os
        import tempfile

        dest_dir = tempfile.gettempdir()
        filename = url.split("/")[-1]
        if not filename.endswith(".exe"):
            filename = "EmlViewerSetup.exe"
        dest_path = os.path.join(dest_dir, filename)

        self._progress_dialog = QProgressDialog(
            "업데이트 설치 파일을 다운로드하는 중입니다...",
            "취소",
            0,
            100,
            self,
        )
        self._progress_dialog.setWindowTitle("업데이트 다운로드")
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.setAutoClose(False)
        self._progress_dialog.setAutoReset(False)
        self._progress_dialog.setValue(0)

        self._download_thread = DownloadThread(self._update_service, url, dest_path)
        self._download_thread.progress.connect(self._on_download_progress)
        self._download_thread.finished.connect(self._on_download_finished)
        self._download_thread.failed.connect(self._on_download_failed)

        self._progress_dialog.canceled.connect(self._download_thread.cancel)
        self._progress_dialog.show()

        self._download_thread.start()
        self.statusBar().showMessage("업데이트 다운로드 중...")

    def _on_download_progress(self, downloaded: int, total: int) -> None:
        if total > 0:
            val = int(downloaded * 100 / total)
            self._progress_dialog.setValue(val)
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            self._progress_dialog.setLabelText(
                f"다운로드 중... ({downloaded_mb:.2f} MB / {total_mb:.2f} MB)"
            )
        else:
            downloaded_mb = downloaded / (1024 * 1024)
            self._progress_dialog.setLabelText(
                f"다운로드 중... ({downloaded_mb:.2f} MB)"
            )

    def _on_download_finished(self, dest_path: str) -> None:
        self._progress_dialog.close()
        self.statusBar().showMessage("다운로드 완료.")

        dialogs.show_info(
            self,
            "업데이트 준비 완료",
            "설치 프로그램 다운로드가 완료되었습니다.\n"
            "확인을 누르면 프로그램을 종료하고 설치를 시작합니다."
        )

        import os
        import sys
        try:
            os.startfile(dest_path)
        except Exception as exc:
            dialogs.show_error(
                self,
                "설치 프로그램 실행 실패",
                f"설치 프로그램을 실행하지 못했습니다:\n{exc}"
            )
            return

        sys.exit(0)

    def _on_download_failed(self, error_msg: str) -> None:
        self._progress_dialog.close()
        if "다운로드가 취소되었습니다" in error_msg:
            self.statusBar().showMessage("업데이트 다운로드가 취소되었습니다.")
            return

        dialogs.show_error(
            self,
            "업데이트 다운로드 실패",
            f"업데이트 파일을 다운로드하는 중에 오류가 발생했습니다:\n{error_msg}"
        )
        self.statusBar().showMessage("업데이트 다운로드 실패.")
