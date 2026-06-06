from __future__ import annotations

from pathlib import Path

from eml_viewer.models.attachment_data import AttachmentInfo
from eml_viewer.services.eml_parser import EmlParser
from eml_viewer.services.file_operation_service import FileOperationPreview, FileOperationService


class AttachmentService:
    """첨부파일 저장 기능을 담당합니다."""

    def __init__(
        self,
        parser: EmlParser | None = None,
        file_operation_service: FileOperationService | None = None,
    ) -> None:
        self._parser = parser or EmlParser()
        self._file_operation_service = file_operation_service or FileOperationService()

    def create_save_preview(
        self,
        attachment: AttachmentInfo,
        destination_path: str | Path,
    ) -> FileOperationPreview:
        return self._file_operation_service.build_write_preview(
            source_label=f"첨부파일: {attachment.filename}",
            destination_path=destination_path,
            action="save_attachment",
        )

    def save_attachment(
        self,
        email_path: str | Path,
        attachment_index: int,
        destination_path: str | Path,
        overwrite: bool = False,
    ) -> Path:
        extracted = self._parser.extract_attachment(email_path, attachment_index)
        return self._file_operation_service.write_bytes(
            destination_path=destination_path,
            data=extracted.payload,
            overwrite=overwrite,
        )
