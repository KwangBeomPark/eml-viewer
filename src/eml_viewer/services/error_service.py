from __future__ import annotations

from eml_viewer.gui.i18n import tr
from eml_viewer.services.eml_parser import EmlParseError


class ErrorService:
    """기술적인 오류를 사용자가 이해하기 쉬운 문장으로 바꿉니다."""

    @staticmethod
    def to_user_message(error: Exception) -> str:
        if isinstance(error, FileNotFoundError):
            return tr("error.file_not_found")
        if isinstance(error, PermissionError):
            return tr("error.permission")
        if isinstance(error, FileExistsError):
            return tr("error.file_exists")
        if isinstance(error, IsADirectoryError):
            return tr("error.directory_selected")
        if isinstance(error, EmlParseError):
            return str(error)
        return tr("error.generic", error=error)
