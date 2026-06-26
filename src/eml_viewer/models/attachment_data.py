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


@dataclass(frozen=True)
class InlineResource:
    """HTML 본문 안에서 cid: 형식으로 참조되는 이미지 같은 리소스입니다."""

    content_id: str
    filename: str
    content_type: str
    payload: bytes
    content_location: str = ""
