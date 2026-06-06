from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class HistoryEntry:
    action: str
    source_path: Path
    destination_path: Path
    created_at: datetime


class HistoryService:
    """향후 변경 이력 저장과 Undo 기능을 붙일 자리입니다."""

    def append(self, entry: HistoryEntry) -> None:
        raise NotImplementedError("변경 이력 저장 기능은 MVP 이후에 구현합니다.")

    def undo_last(self) -> None:
        raise NotImplementedError("Undo 기능은 MVP 이후에 구현합니다.")
