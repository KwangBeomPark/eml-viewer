from __future__ import annotations

import sys
import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eml_viewer.services.attachment_service import AttachmentService


class AttachmentServiceTest(unittest.TestCase):
    def test_save_attachment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            eml_path = self._create_email_with_attachment(temp_path)
            destination = temp_path / "saved.txt"

            saved_path = AttachmentService().save_attachment(eml_path, 0, destination)

            self.assertEqual(saved_path, destination)
            self.assertEqual(destination.read_bytes(), b"hello")

    def test_existing_file_requires_overwrite_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            eml_path = self._create_email_with_attachment(temp_path)
            destination = temp_path / "saved.txt"
            destination.write_text("old", encoding="utf-8")

            service = AttachmentService()
            with self.assertRaises(FileExistsError):
                service.save_attachment(eml_path, 0, destination)

            service.save_attachment(eml_path, 0, destination, overwrite=True)
            self.assertEqual(destination.read_bytes(), b"hello")

    def _create_email_with_attachment(self, folder: Path) -> Path:
        path = folder / "attachment.eml"
        message = EmailMessage()
        message["Subject"] = "첨부 메일"
        message["From"] = "sender@example.com"
        message["To"] = "receiver@example.com"
        message.set_content("첨부가 있습니다.", charset="utf-8")
        message.add_attachment(b"hello", maintype="text", subtype="plain", filename="note.txt")
        path.write_bytes(message.as_bytes())
        return path


if __name__ == "__main__":
    unittest.main()
