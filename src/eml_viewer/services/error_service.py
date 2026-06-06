from __future__ import annotations

from eml_viewer.services.eml_parser import EmlParseError


class ErrorService:
    """기술적인 오류를 사용자가 이해하기 쉬운 문장으로 바꿉니다."""

    @staticmethod
    def to_user_message(error: Exception) -> str:
        if isinstance(error, FileNotFoundError):
            return "선택한 파일을 찾을 수 없습니다. 파일 위치를 다시 확인해 주세요."
        if isinstance(error, PermissionError):
            return "파일을 읽거나 저장할 권한이 없습니다. 다른 폴더를 선택해 주세요."
        if isinstance(error, FileExistsError):
            return "이미 같은 이름의 파일이 있습니다."
        if isinstance(error, IsADirectoryError):
            return "파일이 아니라 폴더가 선택되었습니다. 저장할 파일 이름을 선택해 주세요."
        if isinstance(error, EmlParseError):
            return str(error)
        return f"작업 중 오류가 발생했습니다.\n\n{error}"
