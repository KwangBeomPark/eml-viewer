from __future__ import annotations

import sys
import tempfile
import unittest
from email.message import EmailMessage
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eml_viewer.services.eml_parser import EmlParser


class EmlParserTest(unittest.TestCase):
    def test_parse_plain_text_email(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "plain.eml"
            message = EmailMessage()
            message["Subject"] = "테스트 제목"
            message["From"] = "sender@example.com"
            message["To"] = "receiver@example.com"
            message["Date"] = "Sat, 06 Jun 2026 12:00:00 +0200"
            message.set_content("Plain 본문입니다.", charset="utf-8")
            path.write_bytes(message.as_bytes())

            parsed = EmlParser().parse_file(path)

            self.assertEqual(parsed.subject, "테스트 제목")
            self.assertEqual(parsed.sender, "sender@example.com")
            self.assertEqual(parsed.recipients, "receiver@example.com")
            self.assertIn("Plain 본문입니다.", parsed.plain_body)
            self.assertEqual(parsed.html_body, "")

    def test_parse_html_email(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "html.eml"
            message = EmailMessage()
            message["Subject"] = "HTML 메일"
            message["From"] = "sender@example.com"
            message["To"] = "receiver@example.com"
            message.set_content("대체 텍스트", charset="utf-8")
            message.add_alternative("<html><body><b>HTML 본문</b></body></html>", subtype="html")
            path.write_bytes(message.as_bytes())

            parsed = EmlParser().parse_file(path)

            self.assertIn("대체 텍스트", parsed.plain_body)
            self.assertIn("HTML 본문", parsed.html_body)

    def test_parse_attachment_info_and_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "attachment.eml"
            message = EmailMessage()
            message["Subject"] = "첨부 메일"
            message["From"] = "sender@example.com"
            message["To"] = "receiver@example.com"
            message.set_content("첨부가 있습니다.", charset="utf-8")
            message.add_attachment(b"hello", maintype="text", subtype="plain", filename="note.txt")
            path.write_bytes(message.as_bytes())

            parser = EmlParser()
            parsed = parser.parse_file(path)
            extracted = parser.extract_attachment(path, 0)

            self.assertEqual(len(parsed.attachments), 1)
            self.assertEqual(parsed.attachments[0].filename, "note.txt")
            self.assertEqual(parsed.attachments[0].content_type, "text/plain")
            self.assertEqual(parsed.attachments[0].size, 5)
            self.assertEqual(extracted.payload, b"hello")

    def test_missing_file_raises_file_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            EmlParser().parse_file("missing-file.eml")


if __name__ == "__main__":
    unittest.main()
