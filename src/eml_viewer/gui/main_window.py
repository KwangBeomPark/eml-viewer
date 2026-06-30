from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QThread, Signal
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QApplication,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from eml_viewer.gui import dialogs
from eml_viewer.gui.attachment_widgets import AttachmentPanel
from eml_viewer.gui.i18n import tr
from eml_viewer.gui.message_widgets import MessageBodyWidget
from eml_viewer.gui.metadata_widgets import CopyableLineEdit
from eml_viewer.gui.settings_dialog import SettingsDialog
from eml_viewer.gui.theme import apply_theme
from eml_viewer.models.attachment_data import AttachmentInfo
from eml_viewer.models.email_data import ParsedEmail
from eml_viewer.services.attachment_service import AttachmentService
from eml_viewer.services.eml_parser import EmlParser
from eml_viewer.services.error_service import ErrorService
from eml_viewer.services.file_operation_service import FileOperationService
from eml_viewer.services.forward_service import ForwardConfigError, ForwardService
from eml_viewer.services.settings_service import SettingsService
from eml_viewer.services.translation_service import TranslationCanceled, TranslationService
from eml_viewer.services.update_service import UpdateCheckError, UpdateCheckResult, UpdateService


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


class UpdateCheckThread(QThread):
    check_finished = Signal(object)
    failed = Signal(str)

    def __init__(self, service: UpdateService) -> None:
        super().__init__()
        self._service = service

    def run(self) -> None:
        try:
            self.check_finished.emit(self._service.check_for_updates())
        except Exception as exc:
            self.failed.emit(str(exc))


class TranslationThread(QThread):
    progress = Signal(int, int)
    finished = Signal(str, str)
    failed = Signal(str)
    canceled = Signal()

    def __init__(self, service: TranslationService, text: str, target_language: str, source_format: str) -> None:
        super().__init__()
        self._service = service
        self._text = text
        self._target_language = target_language
        self._source_format = source_format
        import threading
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()

    def run(self) -> None:
        try:
            if self._source_format == "html":
                translated = self._service.translate_html_text(
                    self._text,
                    self._target_language,
                    progress_callback=self._progress_callback,
                    cancel_event=self._cancel_event,
                )
            else:
                translated = self._service.translate_text(
                    self._text,
                    self._target_language,
                    progress_callback=self._progress_callback,
                    cancel_event=self._cancel_event,
                )
        except TranslationCanceled:
            self.canceled.emit()
            return
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(translated, self._source_format)

    def _progress_callback(self, done: int, total: int) -> None:
        self.progress.emit(done, total)


class MainWindow(QMainWindow):
    """EML Viewer의 메인 화면입니다."""

    def __init__(
        self,
        parser: EmlParser,
        attachment_service: AttachmentService,
        settings_service: SettingsService,
        file_operation_service: FileOperationService,
        forward_service: ForwardService | None = None,
        update_service: UpdateService | None = None,
        translation_service: TranslationService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._parser = parser
        self._attachment_service = attachment_service
        self._settings_service = settings_service
        self._file_operation_service = file_operation_service
        self._forward_service = forward_service or ForwardService()
        self._update_service = update_service or UpdateService()
        self._translation_service = translation_service or TranslationService()
        self._current_email: ParsedEmail | None = None
        self._download_thread: DownloadThread | None = None
        self._update_check_thread: UpdateCheckThread | None = None
        self._translation_thread: TranslationThread | None = None
        self._translation_progress_dialog: QProgressDialog | None = None
        self._translation_privacy_confirmed = False
        self._available_update_result: UpdateCheckResult | None = None

        self._subject_edit = CopyableLineEdit(tr("copy.subject"), self)
        self._sender_edit = CopyableLineEdit(tr("copy.sender"), self)
        self._recipients_edit = CopyableLineEdit(tr("copy.recipients"), self)
        self._date_edit = CopyableLineEdit(tr("copy.date"), self)
        self._current_file_label = QLabel(self)
        self._forward_button = QPushButton(self)
        self._body_widget = MessageBodyWidget(self)
        self._attachment_panel = AttachmentPanel(self)

        self.setWindowTitle("EML Viewer")
        self._build_actions()
        self._build_ui()
        self._retranslate_ui()
        self._restore_window_geometry()

        self._attachment_panel.save_requested.connect(self._save_attachments)
        self._subject_edit.copy_requested.connect(self._copy_to_clipboard)
        self._sender_edit.copy_requested.connect(self._copy_to_clipboard)
        self._recipients_edit.copy_requested.connect(self._copy_to_clipboard)
        self._date_edit.copy_requested.connect(self._copy_to_clipboard)
        self._forward_button.clicked.connect(self._forward_current_email)
        self._body_widget.translate_requested.connect(self._translate_body)
        self._start_background_update_check()

    def _build_actions(self) -> None:
        self._open_action = QAction(self)
        self._open_action.setShortcut("Ctrl+O")
        self._open_action.triggered.connect(self._open_file)

        self._exit_action = QAction(self)
        self._exit_action.setShortcut("Alt+F4")
        self._exit_action.triggered.connect(self.close)

        self._settings_action = QAction(self)
        self._settings_action.triggered.connect(self._open_settings)

        self._file_menu = self.menuBar().addMenu("")
        self._file_menu.addAction(self._open_action)
        self._file_menu.addAction(self._settings_action)
        self._file_menu.addSeparator()
        self._file_menu.addAction(self._exit_action)

        self._update_action = QAction(self)
        self._update_action.triggered.connect(self._check_for_updates)

        self._help_menu = self.menuBar().addMenu("")
        self._help_menu.addAction(self._update_action)

        self._toolbar = self.addToolBar("")
        self._toolbar.setMovable(False)
        self._toolbar.addAction(self._open_action)

    def _build_ui(self) -> None:
        self._open_button = QPushButton(self)
        self._open_button.clicked.connect(self._open_file)
        self._forward_button.setEnabled(False)

        self._update_banner = QWidget(self)
        self._update_banner.setObjectName("updateBanner")
        self._update_banner_label = QLabel("", self)
        self._update_banner_download_button = QPushButton(self)
        self._update_banner_close_button = QPushButton(self)
        self._update_banner_download_button.clicked.connect(self._download_available_update)
        self._update_banner_close_button.clicked.connect(self._update_banner.hide)

        update_banner_layout = QHBoxLayout(self._update_banner)
        update_banner_layout.setContentsMargins(10, 6, 10, 6)
        update_banner_layout.addWidget(self._update_banner_label, stretch=1)
        update_banner_layout.addWidget(self._update_banner_download_button)
        update_banner_layout.addWidget(self._update_banner_close_button)
        self._update_banner.setVisible(False)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self._open_button)
        top_layout.addWidget(self._forward_button)
        top_layout.addWidget(self._current_file_label, stretch=1)

        self._metadata_group = QGroupBox(self)
        metadata_layout = QFormLayout(self._metadata_group)
        self._subject_label = QLabel(self)
        self._sender_label = QLabel(self)
        self._recipients_label = QLabel(self)
        self._date_label = QLabel(self)
        metadata_layout.addRow(self._subject_label, self._subject_edit)
        metadata_layout.addRow(self._sender_label, self._sender_edit)
        metadata_layout.addRow(self._recipients_label, self._recipients_edit)
        metadata_layout.addRow(self._date_label, self._date_edit)

        splitter = QSplitter(Qt.Orientation.Vertical, self)
        splitter.addWidget(self._body_widget)
        splitter.addWidget(self._attachment_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        content_layout = QVBoxLayout()
        content_layout.addWidget(self._update_banner)
        content_layout.addLayout(top_layout)
        content_layout.addWidget(self._metadata_group)
        content_layout.addWidget(splitter, stretch=1)

        central_widget = QWidget(self)
        central_widget.setLayout(content_layout)
        self.setCentralWidget(central_widget)

    def _retranslate_ui(self) -> None:
        self._open_action.setText(tr("menu.open_eml"))
        self._exit_action.setText(tr("menu.exit"))
        self._settings_action.setText(tr("menu.settings"))
        self._update_action.setText(tr("menu.update_check"))
        self._file_menu.setTitle(tr("menu.file"))
        self._help_menu.setTitle(tr("menu.help"))
        self._toolbar.setWindowTitle(tr("toolbar.main"))
        self._open_button.setText(tr("button.open_eml"))
        self._forward_button.setText(tr("forward.current"))
        self._update_banner_download_button.setText(tr("button.download"))
        self._update_banner_close_button.setText(tr("button.close"))
        self._metadata_group.setTitle(tr("label.metadata.group"))
        self._subject_label.setText(tr("label.metadata.subject"))
        self._sender_label.setText(tr("label.metadata.sender"))
        self._recipients_label.setText(tr("label.metadata.recipients"))
        self._date_label.setText(tr("label.metadata.date"))
        self._subject_edit.set_copy_tooltip(tr("copy.subject"))
        self._sender_edit.set_copy_tooltip(tr("copy.sender"))
        self._recipients_edit.set_copy_tooltip(tr("copy.recipients"))
        self._date_edit.set_copy_tooltip(tr("copy.date"))
        self._body_widget.retranslate_ui()
        self._attachment_panel.retranslate_ui()
        if self._current_email is None:
            self._current_file_label.setText(tr("label.current_file.none"))
            self.statusBar().showMessage(tr("status.select_eml"))
        if self._available_update_result is not None:
            self._set_update_banner_text(self._available_update_result)

    def _open_file(self) -> None:
        path = dialogs.select_eml_file(self)
        if path is None:
            return
        self.load_email(path)

    def load_email(self, path: str | Path) -> None:
        try:
            parsed_email = self._parser.parse_file(path)
        except Exception as exc:
            self._show_error(tr("error.open_eml.title"), exc)
            return

        self._current_email = parsed_email
        self._display_email(parsed_email)
        self.statusBar().showMessage(tr("status.file_opened", source_path=parsed_email.source_path))

    def _display_email(self, email: ParsedEmail) -> None:
        self._subject_edit.setText(email.subject)
        self._sender_edit.setText(email.sender)
        self._recipients_edit.setText(email.recipients)
        self._date_edit.setText(email.date)
        self._current_file_label.setText(str(email.source_path or ""))
        self._forward_button.setEnabled(email.source_path is not None)
        self._body_widget.set_email(email)
        self._attachment_panel.set_attachments(email.attachments)

    def _copy_to_clipboard(self, text: str) -> None:
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)
            self.statusBar().showMessage(tr("status.copied"))

    def _translate_body(self, text: str, target_language: str, source_format: str = "text") -> None:
        if self._translation_thread is not None and self._translation_thread.isRunning():
            return
        if not text.strip():
            return

        if not self._translation_privacy_confirmed:
            answer = QMessageBox.question(
                self,
                tr("translation.privacy.title"),
                tr("translation.privacy.body"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self._translation_privacy_confirmed = True

        self._body_widget.set_translation_enabled(False)
        self._translation_progress_dialog = QProgressDialog(
            tr("translation.progress.starting"),
            tr("settings.cancel"),
            0,
            0,
            self,
        )
        self._translation_progress_dialog.setWindowTitle(tr("translation.progress.title"))
        self._translation_progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._translation_progress_dialog.setAutoClose(False)
        self._translation_progress_dialog.setAutoReset(False)

        self._translation_thread = TranslationThread(self._translation_service, text, target_language, source_format)
        self._translation_thread.progress.connect(self._on_translation_progress)
        self._translation_thread.finished.connect(self._on_translation_finished)
        self._translation_thread.failed.connect(self._on_translation_failed)
        self._translation_thread.canceled.connect(self._on_translation_canceled)
        self._translation_progress_dialog.canceled.connect(self._translation_thread.cancel)

        self._translation_progress_dialog.show()
        self._translation_thread.start()
        self.statusBar().showMessage(tr("translation.status.running"))

    def _on_translation_progress(self, done: int, total: int) -> None:
        if self._translation_progress_dialog is None:
            return
        self._translation_progress_dialog.setRange(0, max(1, total))
        self._translation_progress_dialog.setValue(done)
        self._translation_progress_dialog.setLabelText(
            tr("translation.progress.label", done=done, total=total)
        )

    def _on_translation_finished(self, translated_text: str, source_format: str) -> None:
        if self._translation_progress_dialog is not None:
            self._translation_progress_dialog.close()
            self._translation_progress_dialog = None
        self._body_widget.set_translation_result(translated_text, source_format)
        self._body_widget.set_translation_enabled(True)
        self.statusBar().showMessage(tr("translation.status.done"))

    def _on_translation_failed(self, error_msg: str) -> None:
        if self._translation_progress_dialog is not None:
            self._translation_progress_dialog.close()
            self._translation_progress_dialog = None
        self._body_widget.set_translation_enabled(True)
        dialogs.show_error(
            self,
            tr("translation.error.title"),
            tr("translation.error.body", error=error_msg),
        )
        self.statusBar().showMessage(tr("translation.status.failed"))

    def _on_translation_canceled(self) -> None:
        if self._translation_progress_dialog is not None:
            self._translation_progress_dialog.close()
            self._translation_progress_dialog = None
        self._body_widget.set_translation_enabled(True)
        self.statusBar().showMessage(tr("translation.status.canceled"))

    def _open_settings(self) -> None:
        settings = self._settings_service.load_settings()
        dialog = SettingsDialog(settings, self)
        if dialog.exec() != SettingsDialog.DialogCode.Accepted:
            return

        new_settings = replace(
            settings,
            language=dialog.language,
            theme=dialog.theme,
            smtp_host=dialog.smtp_host,
            smtp_sender=dialog.smtp_sender,
            smtp_port=dialog.smtp_port,
        )
        language_changed = new_settings.language != settings.language
        self._settings_service.save_settings(new_settings)
        from eml_viewer.gui.i18n import set_language

        set_language(new_settings.language)
        apply_theme(QApplication.instance(), new_settings.theme)
        if language_changed:
            self._retranslate_ui()
            dialogs.show_info(self, tr("settings.title"), tr("settings.language_applied"))
        self.statusBar().showMessage(tr("settings.saved"))

    def _forward_current_email(self) -> None:
        if self._current_email is None:
            dialogs.show_error(self, tr("forward.error.title"), tr("forward.error.no_email"))
            return

        recipient, accepted = QInputDialog.getText(self, tr("forward.title"), tr("forward.recipient_prompt"))
        if not accepted:
            return

        settings = self._settings_service.load_settings()
        try:
            self._forward_service.forward_email(self._current_email, settings, recipient)
        except ForwardConfigError as exc:
            message_box = QMessageBox(self)
            message_box.setIcon(QMessageBox.Icon.Warning)
            message_box.setWindowTitle(tr("forward.config_required.title"))
            message_box.setText(tr("forward.config_required.body", error=exc))
            settings_button = message_box.addButton(tr("menu.settings"), QMessageBox.ButtonRole.AcceptRole)
            message_box.addButton(tr("settings.cancel"), QMessageBox.ButtonRole.RejectRole)
            message_box.exec()
            if message_box.clickedButton() == settings_button:
                self._open_settings()
            return
        except Exception as exc:
            self._show_error(tr("forward.error.title"), exc)
            return

        dialogs.show_info(
            self,
            tr("forward.success.title"),
            tr("forward.completed", recipient=recipient.strip()),
        )
        self.statusBar().showMessage(tr("forward.completed.status"))

    def _save_attachments(self, attachments: list[AttachmentInfo]) -> None:
        if self._current_email is None or self._current_email.source_path is None:
            dialogs.show_error(self, tr("error.attachment_save.title"), tr("forward.error.no_email"))
            return
        if not attachments:
            return

        if len(attachments) == 1:
            self._save_single_attachment(attachments[0])
            return

        destination_dir = dialogs.select_attachment_directory(self)
        if destination_dir is None:
            return

        previews = self._attachment_service.create_bulk_save_preview(attachments, destination_dir)
        overwrite_count = sum(1 for preview in previews if preview.will_overwrite)
        preview_lines = "\n".join(f"- {preview.source_label} -> {preview.destination.name}" for preview in previews)
        overwrite_text = (
            tr("attachment.bulk_overwrite", count=overwrite_count)
            if overwrite_count
            else tr("attachment.bulk_all_new")
        )
        if not dialogs.ask_execute_file_operation(
            self,
            tr("dialog.save_attachment.title"),
            tr(
                "attachment.bulk_preview",
                destination_dir=destination_dir,
                preview_lines=preview_lines,
                overwrite_text=overwrite_text,
            ),
        ):
            self.statusBar().showMessage(tr("status.attachment_save_canceled"))
            return

        try:
            results = self._attachment_service.save_attachments(
                email_path=self._current_email.source_path,
                attachments=attachments,
                destination_dir=destination_dir,
                overwrite=bool(overwrite_count),
            )
        except Exception as exc:
            self._show_error(tr("error.attachment_save.title"), exc)
            return

        dialogs.show_info(
            self,
            tr("dialog.save_attachment.title"),
            tr("attachment.saved_many", count=len(results), destination_dir=destination_dir),
        )
        self.statusBar().showMessage(
            tr("attachment.saved_many.status", count=len(results), destination_dir=destination_dir)
        )

    def _save_single_attachment(self, attachment: AttachmentInfo) -> None:
        if self._current_email is None or self._current_email.source_path is None:
            dialogs.show_error(self, tr("error.attachment_save.title"), tr("forward.error.no_email"))
            return

        safe_filename = self._file_operation_service.sanitize_filename(attachment.filename)
        destination = dialogs.select_attachment_destination(self, safe_filename)
        if destination is None:
            return

        preview = self._attachment_service.create_save_preview(attachment, destination)
        if not dialogs.ask_execute_file_operation(self, tr("dialog.save_attachment.title"), preview.message):
            self.statusBar().showMessage(tr("status.attachment_save_canceled"))
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
            self._show_error(tr("error.attachment_save.title"), exc)
            return

        dialogs.show_info(
            self,
            tr("dialog.save_attachment.title"),
            tr("attachment.saved_one", saved_path=saved_path),
        )
        self.statusBar().showMessage(tr("attachment.saved_one.status", saved_path=saved_path))

    def _restore_window_geometry(self) -> None:
        settings = self._settings_service.load_settings()
        self.setGeometry(
            settings.window_x,
            settings.window_y,
            settings.window_width,
            settings.window_height,
        )

    def closeEvent(self, event) -> None:
        if self._update_check_thread is not None and self._update_check_thread.isRunning():
            self._update_check_thread.wait(1000)
        if self._download_thread is not None and self._download_thread.isRunning():
            self._download_thread.cancel()
            self._download_thread.wait()
        if self._translation_thread is not None and self._translation_thread.isRunning():
            self._translation_thread.cancel()
            self._translation_thread.wait()
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
        self.statusBar().showMessage(tr("update.checking"))
        try:
            result = self._update_service.check_for_updates()
        except UpdateCheckError as exc:
            dialogs.show_error(self, tr("update.check.failed.title"), str(exc))
            self.statusBar().showMessage(tr("update.check.failed.status"))
            return

        if not result.update_available:
            dialogs.show_info(
                self,
                tr("update.current.title"),
                tr("update.current.body", current_version=result.current_version),
            )
            self.statusBar().showMessage(tr("update.current.status"))
            return

        self._show_update_banner(result)
        message = tr(
            "update.available.body",
            current_version=result.current_version,
            latest_version=result.latest_version,
        )
        answer = QMessageBox.question(
            self,
            tr("update.available.title"),
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if answer == QMessageBox.StandardButton.Yes and result.download_url:
            if result.download_url.lower().endswith(".exe"):
                self._start_update_download(result)
            else:
                QDesktopServices.openUrl(QUrl(result.download_url))
                self.statusBar().showMessage(tr("update.check.done"))
        else:
            self.statusBar().showMessage(tr("update.check.done"))

    def _start_background_update_check(self) -> None:
        if self._update_check_thread is not None and self._update_check_thread.isRunning():
            return
        self._update_check_thread = UpdateCheckThread(self._update_service)
        self._update_check_thread.check_finished.connect(self._on_background_update_check_finished)
        self._update_check_thread.failed.connect(lambda _message: None)
        self._update_check_thread.start()

    def _on_background_update_check_finished(self, result: UpdateCheckResult) -> None:
        if result.update_available:
            self._show_update_banner(result)

    def _show_update_banner(self, result: UpdateCheckResult) -> None:
        self._available_update_result = result
        self._set_update_banner_text(result)
        self._update_banner.setVisible(True)

    def _set_update_banner_text(self, result: UpdateCheckResult) -> None:
        self._update_banner_label.setText(
            tr(
                "update.banner",
                latest_version=result.latest_version,
                current_version=result.current_version,
            )
        )

    def _download_available_update(self) -> None:
        result = self._available_update_result
        if result is None:
            return
        if result.download_url and result.download_url.lower().endswith(".exe"):
            self._start_update_download(result)
            return
        if result.download_url:
            QDesktopServices.openUrl(QUrl(result.download_url))
        else:
            QDesktopServices.openUrl(QUrl(result.release_url))
        self.statusBar().showMessage(tr("update.opened_page"))

    def _start_update_download(self, result: UpdateCheckResult) -> None:
        if not result.download_url:
            return

        dest_path = str(self._update_service.installer_cache_path(result))
        if self._update_service.has_valid_cached_installer(result):
            self._on_download_finished(dest_path)
            return

        self._progress_dialog = QProgressDialog(
            tr("update.downloading_installer"),
            tr("settings.cancel"),
            0,
            100,
            self,
        )
        self._progress_dialog.setWindowTitle(tr("update.download.title"))
        self._progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress_dialog.setAutoClose(False)
        self._progress_dialog.setAutoReset(False)
        self._progress_dialog.setValue(0)

        self._download_thread = DownloadThread(self._update_service, result.download_url, dest_path)
        self._download_thread.progress.connect(self._on_download_progress)
        self._download_thread.finished.connect(self._on_download_finished)
        self._download_thread.failed.connect(self._on_download_failed)

        self._progress_dialog.canceled.connect(self._download_thread.cancel)
        self._progress_dialog.show()

        self._download_thread.start()
        self.statusBar().showMessage(tr("update.download.in_progress"))

    def _on_download_progress(self, downloaded: int, total: int) -> None:
        if total > 0:
            val = int(downloaded * 100 / total)
            self._progress_dialog.setValue(val)
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            self._progress_dialog.setLabelText(
                tr("update.download.label_total", downloaded_mb=downloaded_mb, total_mb=total_mb)
            )
        else:
            downloaded_mb = downloaded / (1024 * 1024)
            self._progress_dialog.setLabelText(
                tr("update.download.label", downloaded_mb=downloaded_mb)
            )

    def _on_download_finished(self, dest_path: str) -> None:
        self._progress_dialog.close()
        self.statusBar().showMessage(tr("update.download_complete"))

        # 방어적 코드: 다운로드된 파일 존재 여부 및 유효성(크기) 검증
        import os
        if not os.path.exists(dest_path) or os.path.getsize(dest_path) == 0:
            dialogs.show_error(
                self,
                tr("update.installer_validation_failed.title"),
                tr("update.installer_validation_failed.body")
            )
            return

        dialogs.show_info(
            self,
            tr("update.installer_ready.title"),
            tr("update.installer_ready.body")
        )

        from PySide6.QtWidgets import QApplication
        try:
            os.startfile(dest_path)
        except Exception as exc:
            dialogs.show_error(
                self,
                tr("update.installer_execute_failed.title"),
                tr("update.installer_execute_failed.body", error=exc)
            )
            return

        self.close()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _on_download_failed(self, error_msg: str) -> None:
        self._progress_dialog.close()
        if "다운로드가 취소되었습니다" in error_msg or "download canceled" in error_msg.lower():
            self.statusBar().showMessage(tr("update.download.canceled"))
            return

        dialogs.show_error(
            self,
            tr("update.download.failed.title"),
            tr("update.download.failed.body", error=error_msg)
        )
        self.statusBar().showMessage(tr("update.download.failed.status"))
