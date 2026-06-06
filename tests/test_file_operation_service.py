from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eml_viewer.services.file_operation_service import FileOperationService


class FileOperationServiceTest(unittest.TestCase):
    def test_build_write_preview_marks_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "existing.txt"
            destination.write_text("old", encoding="utf-8")

            preview = FileOperationService().build_write_preview("첨부파일: existing.txt", destination)

            self.assertTrue(preview.will_overwrite)
            self.assertIn("기존 파일을 덮어씁니다.", preview.message)

    def test_write_bytes_requires_overwrite_for_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "existing.txt"
            destination.write_text("old", encoding="utf-8")
            service = FileOperationService()

            with self.assertRaises(FileExistsError):
                service.write_bytes(destination, b"new")

            service.write_bytes(destination, b"new", overwrite=True)
            self.assertEqual(destination.read_bytes(), b"new")

    def test_sanitize_filename_replaces_windows_invalid_chars(self) -> None:
        filename = FileOperationService().sanitize_filename('bad:name*?.txt')

        self.assertEqual(filename, "bad_name__.txt")


if __name__ == "__main__":
    unittest.main()
