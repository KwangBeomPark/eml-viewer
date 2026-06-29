from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from eml_viewer.models.app_settings import AppSettings
from eml_viewer.models.email_data import ParsedEmail
from eml_viewer.services.forward_service import ForwardConfigError, ForwardService


class FakeSmtp:
    sent_messages: list[object] = []
    init_args: tuple[str, int, int] | None = None

    def __init__(self, host: str, port: int, timeout: int) -> None:
        type(self).init_args = (host, port, timeout)

    def __enter__(self) -> "FakeSmtp":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def send_message(self, message) -> None:
        type(self).sent_messages.append(message)


class ForwardServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        FakeSmtp.sent_messages = []
        FakeSmtp.init_args = None

    def test_forward_email_sends_original_eml_as_attachment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "original.eml"
            source_path.write_bytes(b"From: sender@example.com\n\nBody")
            email = ParsedEmail(
                subject="Hello",
                sender="sender@example.com",
                recipients="receiver@example.com",
                date="2026-06-27",
                plain_body="Body",
                html_body="",
                source_path=source_path,
            )
            settings = AppSettings(
                smtp_host="smtp.example.com",
                smtp_port=2525,
                smtp_sender="forwarder@example.com",
            )

            ForwardService(FakeSmtp).forward_email(email, settings, "target@example.com")

            self.assertEqual(FakeSmtp.init_args, ("smtp.example.com", 2525, 30))
            self.assertEqual(len(FakeSmtp.sent_messages), 1)
            message = FakeSmtp.sent_messages[0]
            self.assertEqual(message["From"], "forwarder@example.com")
            self.assertEqual(message["To"], "target@example.com")
            self.assertEqual(message["Subject"], "Fwd: Hello")
            self.assertTrue(message.is_multipart())

    def test_forward_email_requires_smtp_settings(self) -> None:
        email = ParsedEmail(
            subject="",
            sender="",
            recipients="",
            date="",
            plain_body="",
            html_body="",
        )

        with self.assertRaises(ForwardConfigError):
            ForwardService(FakeSmtp).forward_email(email, AppSettings(), "target@example.com")


if __name__ == "__main__":
    unittest.main()
