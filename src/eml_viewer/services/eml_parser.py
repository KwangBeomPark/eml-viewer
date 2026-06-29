from __future__ import annotations

import html
import re
from dataclasses import dataclass
from email import policy
from email.header import decode_header, make_header
from email.message import EmailMessage, Message
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

from eml_viewer.gui.i18n import tr
from eml_viewer.models.attachment_data import AttachmentInfo, InlineResource
from eml_viewer.models.email_data import ParsedEmail


class EmlParseError(Exception):
    """EML 파일을 읽거나 해석할 수 없을 때 사용하는 오류입니다."""


@dataclass(frozen=True)
class ExtractedAttachment:
    info: AttachmentInfo
    payload: bytes


class _HtmlPlainTextExtractor(HTMLParser):
    _block_tags = {"div", "p", "section", "article", "header", "footer", "table", "ul", "ol"}
    _row_tags = {"tr"}
    _cell_tags = {"td", "th"}
    _skip_tags = {"script", "style", "head", "title"}
    _void_tags = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if self._skip_stack:
            if tag not in self._void_tags:
                self._skip_stack.append(tag)
            return
        if tag in self._skip_tags:
            self._skip_stack.append(tag)
            return

        attr_map = {name.lower(): value or "" for name, value in attrs}
        if self._is_hidden(attr_map):
            if tag not in self._void_tags:
                self._skip_stack.append(tag)
            return

        if tag in self._block_tags or tag in self._row_tags:
            self._newline()
        elif tag in self._cell_tags:
            self._cell_break()
        elif tag == "br":
            self._newline()
        elif tag == "li":
            self._newline()
            self._append("- ")
        elif tag == "img":
            label = (attr_map.get("alt") or attr_map.get("title") or "").strip()
            self._append(f"[Image: {label}]" if label else "[Image]")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._skip_stack:
            self._skip_stack.pop()
            return
        if tag in self._block_tags or tag in self._row_tags:
            self._newline()

    def handle_data(self, data: str) -> None:
        if self._skip_stack:
            return
        text = " ".join(data.split())
        if text:
            self._append(text)

    def text(self) -> str:
        lines = []
        for line in "".join(self._chunks).splitlines():
            cleaned = re.sub(r"[ \t]+", " ", line).strip()
            if cleaned:
                lines.append(cleaned)
        return "\n".join(lines).strip()

    def _append(self, text: str) -> None:
        if self._chunks and self._chunks[-1] not in {"\n", "\t", " "}:
            self._chunks.append(" ")
        self._chunks.append(text)

    def _newline(self) -> None:
        if self._chunks and self._chunks[-1] != "\n":
            self._chunks.append("\n")

    def _cell_break(self) -> None:
        if self._chunks and self._chunks[-1] not in {"\n", "\t"}:
            self._chunks.append("\t")

    def _is_hidden(self, attrs: dict[str, str]) -> bool:
        hidden = attrs.get("hidden", "")
        style = attrs.get("style", "").replace(" ", "").lower()
        return hidden != "" or "display:none" in style or "visibility:hidden" in style


class _HtmlResourceReferenceExtractor(HTMLParser):
    _url_pattern = re.compile(r"url\((?P<quote>[\"']?)(?P<value>.*?)(?P=quote)\)", re.IGNORECASE)

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: set[str] = set()

    def handle_starttag(self, tag: str, attrs) -> None:
        for name, value in attrs:
            if not value:
                continue
            name = name.lower()
            if name in {"src", "background"}:
                self.references.update(_resource_keys(value))
            elif name == "srcset":
                for srcset_value in _srcset_values(value):
                    self.references.update(_resource_keys(srcset_value))
            elif name == "style":
                for match in self._url_pattern.finditer(value):
                    self.references.update(_resource_keys(match.group("value")))


class EmlParser:
    """EML 파일을 읽어서 화면과 저장 기능이 쓰기 쉬운 데이터로 바꿉니다."""

    def parse_file(self, path: str | Path) -> ParsedEmail:
        eml_path = Path(path)
        message = self._load_message(eml_path)
        parts = list(self._iter_leaf_parts(message))

        plain_candidates: list[str] = []
        html_candidates: list[str] = []

        for part in parts:
            content_type = part.get_content_type().lower()
            if self._is_attachment(part):
                continue
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

        plain_body_generated = False
        if not plain_body and html_body:
            plain_body = self._html_to_plain_text(html_body)
            plain_body_generated = bool(plain_body)

        html_references = self._html_resource_references(html_body)
        attachments: list[AttachmentInfo] = []
        inline_resources: list[InlineResource] = []
        attachment_index = 0
        for part in parts:
            if self._is_body_text_part(part):
                continue

            if self._is_inline_resource(part, html_references):
                inline_resources.append(self._inline_resource(part, len(inline_resources)))
                continue

            if self._is_attachment(part):
                attachments.append(self._attachment_info(part, attachment_index))
                attachment_index += 1

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
            plain_body_generated=plain_body_generated,
        )

    def extract_attachment(self, path: str | Path, attachment_index: int) -> ExtractedAttachment:
        eml_path = Path(path)
        message = self._load_message(eml_path)
        parts = list(self._iter_leaf_parts(message))
        html_body = self._choose_best_body(
            [
                self._safe_get_content(part)
                for part in parts
                if part.get_content_type().lower() == "text/html" and not self._is_attachment(part)
            ]
        )
        html_references = self._html_resource_references(html_body)

        current_index = 0
        for part in parts:
            if self._is_inline_resource(part, html_references) or not self._is_attachment(part):
                continue

            info = self._attachment_info(part, current_index)
            if current_index == attachment_index:
                payload = part.get_payload(decode=True) or b""
                return ExtractedAttachment(info=info, payload=payload)

            current_index += 1

        raise EmlParseError(tr("parse.attachment_not_found"))

    def _load_message(self, path: Path) -> EmailMessage | Message:
        if not path.exists():
            raise FileNotFoundError(tr("parse.file_not_found", path=path))
        if not path.is_file():
            raise EmlParseError(tr("parse.not_file"))

        try:
            raw_bytes = path.read_bytes()
        except OSError as exc:
            raise EmlParseError(tr("parse.cannot_read", path=path)) from exc

        try:
            return BytesParser(policy=policy.default).parsebytes(raw_bytes)
        except Exception as exc:
            raise EmlParseError(tr("parse.cannot_parse")) from exc

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

    def _is_body_text_part(self, part: EmailMessage | Message) -> bool:
        disposition = (part.get_content_disposition() or "").lower()
        return part.get_content_type().lower() in {"text/plain", "text/html"} and disposition != "attachment"

    def _is_inline_resource(self, part: EmailMessage | Message, html_references: set[str]) -> bool:
        if part.get_content_maintype().lower() != "image":
            return False

        disposition = (part.get_content_disposition() or "").lower()
        content_id = self._content_id(part)
        content_location = self._content_location(part)
        keys = self._part_resource_keys(part)
        if keys.intersection(html_references):
            return True
        if disposition == "inline" and (content_id or content_location or part.get_filename()):
            return True
        return bool(content_id) and disposition != "attachment"

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
        content_location = self._content_location(part)
        filename = part.get_filename() or f"{content_id}"
        filename = self._decode_header_value(filename)
        return InlineResource(
            content_id=content_id,
            filename=filename,
            content_type=part.get_content_type(),
            payload=part.get_payload(decode=True) or b"",
            content_location=content_location,
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

    def _html_to_plain_text(self, html_body: str) -> str:
        parser = _HtmlPlainTextExtractor()
        try:
            parser.feed(html_body)
            parser.close()
        except Exception:
            return ""
        return parser.text()

    def _html_resource_references(self, html_body: str) -> set[str]:
        if not html_body:
            return set()

        parser = _HtmlResourceReferenceExtractor()
        try:
            parser.feed(html_body)
            parser.close()
        except Exception:
            return set()
        return parser.references

    def _content_id(self, part: EmailMessage | Message) -> str:
        raw_value = part.get("Content-ID", "")
        decoded = self._decode_header_value(raw_value)
        return decoded.strip().strip("<>").strip()

    def _content_location(self, part: EmailMessage | Message) -> str:
        raw_value = part.get("Content-Location", "")
        decoded = self._decode_header_value(raw_value)
        return decoded.strip().strip("<>").strip()

    def _part_resource_keys(self, part: EmailMessage | Message) -> set[str]:
        keys: set[str] = set()
        keys.update(_resource_keys(self._content_id(part)))
        keys.update(_resource_keys(self._content_location(part)))
        filename = part.get_filename()
        if filename:
            keys.update(_resource_keys(self._decode_header_value(filename)))
        return keys


def _resource_keys(value: str) -> set[str]:
    if not value:
        return set()

    cleaned = html.unescape(unquote(str(value))).strip().strip("\"'<>")
    if not cleaned:
        return set()

    lowered = cleaned.lower()
    if lowered.startswith(("http://", "https://", "data:", "mailto:", "#")):
        return set()
    if lowered.startswith("cid:"):
        cleaned = cleaned[4:]
        lowered = cleaned.lower()

    parsed_path = urlparse(cleaned).path or cleaned
    candidates = {
        cleaned,
        lowered,
        cleaned.lstrip("./\\"),
        parsed_path,
        parsed_path.lstrip("./\\"),
        Path(parsed_path.replace("\\", "/")).name,
    }
    return {candidate.strip().strip("<>").lower() for candidate in candidates if candidate.strip()}


def _srcset_values(value: str) -> list[str]:
    values: list[str] = []
    for candidate in str(value).split(","):
        candidate = candidate.strip()
        if not candidate:
            continue
        values.append(candidate.split()[0])
    return values
