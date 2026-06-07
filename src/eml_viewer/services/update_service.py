from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from eml_viewer import __version__


class UpdateCheckError(Exception):
    """업데이트 정보를 가져올 수 없을 때 사용하는 오류입니다."""


@dataclass(frozen=True)
class UpdateCheckResult:
    current_version: str
    latest_version: str
    release_url: str
    download_url: str | None

    @property
    def update_available(self) -> bool:
        return _version_tuple(self.latest_version) > _version_tuple(self.current_version)


class UpdateService:
    """GitHub Releases에서 최신 설치 파일 정보를 확인합니다."""

    def __init__(
        self,
        repository: str = "KwangBeomPark/eml-viewer",
        current_version: str = __version__,
        timeout_seconds: int = 10,
        opener=None,
    ) -> None:
        self._repository = repository
        self._current_version = current_version
        self._timeout_seconds = timeout_seconds
        self._opener = opener or urllib.request.urlopen

    def check_for_updates(self) -> UpdateCheckResult:
        url = f"https://api.github.com/repos/{self._repository}/releases/latest"
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "EML-Viewer-Update-Checker",
            },
        )

        try:
            with self._opener(request, timeout=self._timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise UpdateCheckError("아직 등록된 배포 버전이 없습니다.") from exc
            raise UpdateCheckError(f"업데이트 정보를 가져오지 못했습니다. HTTP {exc.code}") from exc
        except Exception as exc:
            raise UpdateCheckError("업데이트 정보를 가져오지 못했습니다. 인터넷 연결을 확인해 주세요.") from exc

        latest_version = _normalize_version(str(payload.get("tag_name", "")))
        if not latest_version:
            raise UpdateCheckError("최신 버전 정보를 읽을 수 없습니다.")

        release_url = str(payload.get("html_url", ""))
        download_url = self._installer_download_url(payload) or release_url or None

        return UpdateCheckResult(
            current_version=self._current_version,
            latest_version=latest_version,
            release_url=release_url,
            download_url=download_url,
        )

    def _installer_download_url(self, payload: dict) -> str | None:
        assets = payload.get("assets", [])
        if not isinstance(assets, list):
            return None

        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name", ""))
            if name.startswith("EmlViewerSetup-") and name.lower().endswith(".exe"):
                return str(asset.get("browser_download_url", "")) or None
        return None


def _normalize_version(version: str) -> str:
    return version.strip().lstrip("vV")


def _version_tuple(version: str) -> tuple[int, ...]:
    normalized = _normalize_version(version)
    parts: list[int] = []
    for part in normalized.split("."):
        digits = "".join(char for char in part if char.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts)
