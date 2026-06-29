from __future__ import annotations

import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from eml_viewer.gui.i18n import tr


@dataclass(frozen=True)
class FileOperationPreview:
    """실제 파일 작업 전에 사용자에게 보여줄 정보입니다."""

    action: str
    source_label: str
    destination: Path
    will_overwrite: bool

    @property
    def message(self) -> str:
        overwrite_text = tr("file_operation.overwrite") if self.will_overwrite else tr("file_operation.new_file")
        return f"{self.source_label}\n-> {self.destination}\n\n{overwrite_text}"


class FileOperationService:
    """파일 저장/이름 변경 같은 위험 작업의 공통 규칙을 담당합니다."""

    _invalid_filename_chars = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
    _reserved_windows_names = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }

    def build_write_preview(
        self,
        source_label: str,
        destination_path: str | Path,
        action: str = "save",
    ) -> FileOperationPreview:
        destination = Path(destination_path)
        return FileOperationPreview(
            action=action,
            source_label=source_label,
            destination=destination,
            will_overwrite=destination.exists(),
        )

    def write_bytes(self, destination_path: str | Path, data: bytes, overwrite: bool = False) -> Path:
        destination = Path(destination_path)
        if destination.exists() and destination.is_dir():
            raise IsADirectoryError(tr("file_operation.write_to_directory", destination=destination))
        if destination.exists() and not overwrite:
            raise FileExistsError(f"{tr('error.file_exists')}: {destination}")

        destination.parent.mkdir(parents=True, exist_ok=True)

        fd, temp_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent)
        temp_path = Path(temp_name)
        try:
            with os.fdopen(fd, "wb") as temp_file:
                temp_file.write(data)
            os.replace(temp_path, destination)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

        return destination

    def sanitize_filename(self, filename: str, fallback: str = "attachment") -> str:
        cleaned = self._invalid_filename_chars.sub("_", filename).strip(" .")
        if not cleaned:
            return fallback

        stem = Path(cleaned).stem.upper()
        if stem in self._reserved_windows_names:
            cleaned_path = Path(cleaned)
            cleaned = f"{cleaned_path.stem}_{cleaned_path.suffix}" if cleaned_path.suffix else f"{cleaned}_"

        return cleaned
