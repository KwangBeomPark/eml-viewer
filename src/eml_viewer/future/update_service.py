from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpdateCheckResult:
    current_version: str
    latest_version: str
    download_url: str | None

    @property
    def update_available(self) -> bool:
        return self.latest_version != self.current_version


class UpdateService:
    """향후 설치 패키지와 업데이트 확인 기능을 붙일 자리입니다."""

    def check_for_updates(self) -> UpdateCheckResult:
        raise NotImplementedError("업데이트 확인 기능은 MVP 이후에 구현합니다.")
