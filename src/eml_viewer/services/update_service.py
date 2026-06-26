from __future__ import annotations

import json
import os
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from eml_viewer import __version__


class UpdateCheckError(Exception):
    """업데이트 정보를 가져올 수 없을 때 사용하는 오류입니다."""


class UpdateDownloadError(Exception):
    """업데이트 설치 파일을 다운로드할 수 없을 때 사용하는 오류입니다."""


class OperationCanceled(Exception):
    """사용자가 작업을 취소했을 때 발생하는 예외입니다."""


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
        download_timeout_seconds: int = 300,
        opener=None,
    ) -> None:
        self._repository = repository
        self._current_version = current_version
        self._timeout_seconds = timeout_seconds
        self._download_timeout_seconds = download_timeout_seconds
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
                raise UpdateCheckError(
                    "업데이트 배포 정보를 찾을 수 없습니다. GitHub Releases 공개 여부와 저장소 접근 권한을 확인해 주세요."
                ) from exc
            raise UpdateCheckError(f"업데이트 정보를 가져오지 못했습니다. HTTP {exc.code}") from exc
        except Exception as exc:
            raise UpdateCheckError("업데이트 정보를 가져오지 못했습니다. 인터넷 연결을 확인해 주세요.") from exc

        if not isinstance(payload, dict):
            raise UpdateCheckError("최신 버전 정보를 읽을 수 없습니다.")

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

    def download_installer(
        self,
        url: str,
        dest_path: str,
        progress_callback=None,
        cancel_event=None,
    ) -> None:
        """설치 프로그램을 다운로드합니다."""
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "EML-Viewer-Updater",
            },
        )
        destination = Path(dest_path)
        temp_path: Path | None = None

        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with self._opener(request, timeout=self._download_timeout_seconds) as response:
                total_size = int(response.headers.get("content-length", 0))
                block_size = 8192
                downloaded = 0

                fd, temp_name = tempfile.mkstemp(
                    prefix=f".{destination.name}.",
                    suffix=".tmp",
                    dir=destination.parent,
                )
                temp_path = Path(temp_name)
                with os.fdopen(fd, "wb") as f:
                    while True:
                        if cancel_event is not None and cancel_event.is_set():
                            raise OperationCanceled("다운로드가 취소되었습니다.")

                        buffer = response.read(block_size)
                        if not buffer:
                            break

                        f.write(buffer)
                        downloaded += len(buffer)

                        if progress_callback is not None:
                            progress_callback(downloaded, total_size)

                if downloaded == 0:
                    raise UpdateDownloadError("다운로드된 설치 파일이 비어 있습니다.")

                os.replace(temp_path, destination)
                temp_path = None
        except Exception as exc:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            if isinstance(exc, OperationCanceled):
                raise
            if isinstance(exc, UpdateDownloadError):
                raise
            raise UpdateDownloadError(f"다운로드 중 오류가 발생했습니다: {exc}") from exc


def _normalize_version(version: str) -> str:
    return version.strip().lstrip("vV")


def _version_tuple(version: str) -> tuple[int, ...]:
    normalized = _normalize_version(version)
    parts: list[int] = []
    for part in normalized.split("."):
        digits = "".join(char for char in part if char.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts)
