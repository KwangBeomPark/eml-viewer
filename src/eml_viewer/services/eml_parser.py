from __future__ import annotations

from dataclasses import dataclass
from email import policy
from email.header import decode_header, make_header
from email.message import EmailMessage, Message
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from pathlib import Path

from eml_viewer.models.attachment_data import AttachmentInfo, InlineResource
from eml_viewer.models.email_data import ParsedEmail


class EmlParseError(Exception):
    """EML 파일을 읽거나 해석할 수 없을 때 사용하는 오류입니다."""


@dataclass(frozen=True)
class ExtractedAttachment:
    info: AttachmentInfo
    payload: bytes


class EmlParser:
    """EML 파일을 읽어서 화면과 저장 기능이 쓰기 쉬운 데이터로 바꿉니다."""

    def parse_file(self, path: str | Path) -> ParsedEmail:
        eml_path = Path(path)
        message = self._load_message(eml_path)

        plain_candidates: list[str] = []
        html_candidates: list[str] = []
        attachments: list[AttachmentInfo] = []
        inline_resources: list[InlineResource] = []

        for part in self._iter_leaf_parts(message):
            if self._is_inline_resource(part):
                inline_resources.append(self._inline_resource(part, len(inline_resources)))
                continue

            if self._is_attachment(part):
                attachments.append(self._attachment_info(part, len(attachments)))
                continue

            content_type = part.get_content_type().lower()
            if content_type == "text/plain":
                plain_candidates.append(self._safe_get_content(part))
            elif content_type == "text/html":
                html_candidates.append(self._safe_get_content(part))

        plain_body = self._choose_best_body(plain_candidates)
        html_body = self._choose_best_body(html_candidates)

        if not plain_body and not html_body and not message.is_multipart():
            content_type = message.get_content_type().lower()
            if content_type == "text/html":
                html_body = self._safe_get_content(message)
            else:
                plain_body = self._safe_get_content(message)

        return ParsedEmail(
            subject=self._decode_header_value(message.get("Subject", "")),
            sender=self._decode_header_value(message.get("From", "")),
            recipients=self._decode_header_value(message.get("To", "")),
            date=self._format_date(message.get("Date", "")),
            plain_body=plain_body,
            html_body=html_body,
            attachments=attachments,
            inline_resources=inline_resources,
            source_path=eml_path,
        )

    def extract_attachment(self, path: str | Path, attachment_index: int) -> ExtractedAttachment:
        eml_path = Path(path)
        message = self._load_message(eml_path)

        current_index = 0
        for part in self._iter_leaf_parts(message):
            if self._is_inline_resource(part) or not self._is_attachment(part):
                continue

            info = self._attachment_info(part, current_index)
            if current_index == attachment_index:
                payload = part.get_payload(decode=True) or b""
                return ExtractedAttachment(info=info, payload=payload)

            current_index += 1

        raise EmlParseError("선택한 첨부파일을 찾을 수 없습니다.")

    def _load_message(self, path: Path) -> EmailMessage | Message:
        if not path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")
        if not path.is_file():
            raise EmlParseError("선택한 경로가 파일이 아닙니다.")

        try:
            raw_bytes = path.read_bytes()
        except OSError as exc:
            raise EmlParseError(f"EML 파일을 읽을 수 없습니다: {path}") from exc

        try:
            return BytesParser(policy=policy.default).parsebytes(raw_bytes)
        except Exception as exc:
            raise EmlParseError("EML 파일 내용을 해석할 수 없습니다.") from exc

    def _iter_leaf_parts(self, message: EmailMessage | Message):
        if message.is_multipart():
            for part in message.walk():
                if part.is_multipart():
                    continue
                yield part
        else:
            yield message

    def _is_attachment(self, part: EmailMessage | Message) -> bool:
        disposition = (part.get_content_disposition() or "").lower()
        return disposition == "attachment" or bool(part.get_filename())

    def _is_inline_resource(self, part: EmailMessage | Message) -> bool:
        disposition = (part.get_content_disposition() or "").lower()
        content_id = self._content_id(part)
        return bool(content_id) and disposition != "attachment" and part.get_content_maintype().lower() == "image"

    def _attachment_info(self, part: EmailMessage | Message, index: int) -> AttachmentInfo:
        filename = part.get_filename() or f"attachment-{index + 1}"
        filename = self._decode_header_value(filename)
        payload = part.get_payload(decode=True) or b""
        return AttachmentInfo(
            index=index,
            filename=filename,
            content_type=part.get_content_type(),
            size=len(payload),
        )

    def _inline_resource(self, part: EmailMessage | Message, index: int) -> InlineResource:
        content_id = self._content_id(part) or f"inline-{index + 1}"
        filename = part.get_filename() or f"{content_id}"
        filename = self._decode_header_value(filename)
        return InlineResource(
            content_id=content_id,
            filename=filename,
            content_type=part.get_content_type(),
            payload=part.get_payload(decode=True) or b"",
        )

    def _safe_get_content(self, part: EmailMessage | Message) -> str:
        try:
            content = part.get_content()
        except Exception:
            payload = part.get_payload(decode=True) or b""
            charset = part.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")

        if isinstance(content, bytes):
            charset = part.get_content_charset() or "utf-8"
            return content.decode(charset, errors="replace")
        return str(content)

    def _decode_header_value(self, value: str) -> str:
        if not value:
            return ""
        try:
            return str(make_header(decode_header(value)))
        except Exception:
            return str(value)

    def _format_date(self, value: str) -> str:
        decoded = self._decode_header_value(value)
        if not decoded:
            return ""
        try:
            parsed = parsedate_to_datetime(decoded)
        except Exception:
            return decoded
        return parsed.strftime("%Y-%m-%d %H:%M:%S %z").strip()

    def _choose_best_body(self, candidates: list[str]) -> str:
        non_empty = [candidate for candidate in candidates if candidate and candidate.strip()]
        if not non_empty:
            return ""
        return max(non_empty, key=lambda candidate: len(candidate.strip()))

    def _content_id(self, part: EmailMessage | Message) -> str:
        raw_value = part.get("Content-ID", "")
        decoded = self._decode_header_value(raw_value)
        return decoded.strip().strip("<>").strip()
