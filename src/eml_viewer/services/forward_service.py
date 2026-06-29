from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path

from eml_viewer.gui.i18n import tr
from eml_viewer.models.app_settings import AppSettings
from eml_viewer.models.email_data import ParsedEmail


class ForwardConfigError(Exception):
    """Raised when SMTP forwarding settings are incomplete."""


class ForwardSendError(Exception):
    """Raised when the current email cannot be forwarded."""


class ForwardService:
    """Sends the currently opened EML as an attached original message."""

    def __init__(self, smtp_factory=smtplib.SMTP) -> None:
        self._smtp_factory = smtp_factory

    def forward_email(self, email: ParsedEmail, settings: AppSettings, recipient: str) -> None:
        recipient = recipient.strip()
        self._validate_settings(settings, recipient)

        if email.source_path is None:
            raise ForwardSendError(tr("forward.error.no_email"))

        source_path = Path(email.source_path)
        try:
            original_bytes = source_path.read_bytes()
        except OSError as exc:
            raise ForwardSendError(tr("forward.error.read_original", source_path=source_path)) from exc

        message = EmailMessage()
        message["From"] = settings.smtp_sender
        message["To"] = recipient
        message["Subject"] = self._forward_subject(email.subject)
        message.set_content(self._plain_forward_body(email))
        message.add_attachment(
            original_bytes,
            maintype="message",
            subtype="rfc822",
            filename=source_path.name,
        )

        try:
            with self._smtp_factory(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
                smtp.send_message(message)
        except Exception as exc:
            raise ForwardSendError(tr("forward.error.send", error=exc)) from exc

    def _validate_settings(self, settings: AppSettings, recipient: str) -> None:
        missing: list[str] = []
        if not settings.smtp_host.strip():
            missing.append(tr("settings.smtp_host"))
        if not settings.smtp_sender.strip():
            missing.append(tr("settings.smtp_sender"))
        if not recipient:
            missing.append(tr("forward.recipient_prompt").rstrip(":"))
        if missing:
            raise ForwardConfigError(tr("forward.missing_prefix", fields=", ".join(missing)))

    def _forward_subject(self, subject: str) -> str:
        subject = subject.strip()
        if not subject:
            return "Fwd: forwarded EML"
        if subject.lower().startswith(("fw:", "fwd:")):
            return subject
        return f"Fwd: {subject}"

    def _plain_forward_body(self, email: ParsedEmail) -> str:
        body = email.plain_body.strip() or "(Plain text body is not available.)"
        return (
            "Forwarded from EML Viewer.\n\n"
            "----- Original message -----\n"
            f"Subject: {email.subject}\n"
            f"From: {email.sender}\n"
            f"To: {email.recipients}\n"
            f"Date: {email.date}\n\n"
            f"{body}\n"
        )
