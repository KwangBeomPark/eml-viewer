from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eml_viewer.models.email_data import ParsedEmail


@dataclass(frozen=True)
class RenamePlan:
    original_path: Path
    suggested_path: Path
    reason: str


class RenamePlanService:
    """향후 파일명 자동 생성과 변경 전 미리 보기 기능을 붙일 자리입니다."""

    def build_preview(self, email: ParsedEmail, target_folder: Path) -> RenamePlan:
        raise NotImplementedError("파일명 자동 변경 기능은 MVP 이후에 구현합니다.")
