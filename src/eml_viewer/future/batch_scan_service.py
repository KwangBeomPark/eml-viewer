from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from eml_viewer.models.email_data import ParsedEmail
from eml_viewer.services.eml_parser import EmlParser


@dataclass(frozen=True)
class FolderScanResult:
    folder: Path
    eml_files: list[Path]


class FolderScanService:
    """향후 폴더 단위 EML 스캔 기능을 붙일 자리입니다."""

    def scan(self, folder: Path, recursive: bool = False) -> FolderScanResult:
        pattern = "**/*.eml" if recursive else "*.eml"
        eml_files = sorted(path for path in folder.glob(pattern) if path.is_file())
        return FolderScanResult(folder=folder, eml_files=eml_files)


class BatchAnalysisService:
    """향후 여러 EML 파일 일괄 분석 기능을 붙일 자리입니다."""

    def __init__(self, parser: EmlParser | None = None) -> None:
        self._parser = parser or EmlParser()

    def parse_many(self, paths: list[Path]) -> list[ParsedEmail]:
        return [self._parser.parse_file(path) for path in paths]
