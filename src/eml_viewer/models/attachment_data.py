from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AttachmentInfo:
    """첨부파일 목록에 보여줄 최소 정보입니다."""

    index: int
    filename: str
    content_type: str
    size: int

    @property
    def display_size(self) -> str:
        if self.size < 1024:
            return f"{self.size} B"
        if self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        return f"{self.size / (1024 * 1024):.1f} MB"
