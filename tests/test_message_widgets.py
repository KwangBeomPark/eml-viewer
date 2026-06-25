from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication

from eml_viewer.gui.message_widgets import MessageBodyWidget
from eml_viewer.models.attachment_data import InlineResource
from eml_viewer.models.email_data import ParsedEmail


class MessageBodyWidgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_prepare_html_replaces_cid_image_reference(self) -> None:
        widget = MessageBodyWidget()
        email = ParsedEmail(
            subject="",
            sender="",
            recipients="",
            date="",
            plain_body="",
            html_body='<html><body><img src="cid:image001@example"></body></html>',
            inline_resources=[
                InlineResource(
                    content_id="image001@example",
                    filename="image001.png",
                    content_type="image/png",
                    payload=b"fake-png",
                )
            ],
        )

        prepared_html = widget._prepare_html(email)

        self.assertIn("file:///", prepared_html)
        self.assertNotIn("cid:image001@example", prepared_html)
        widget.clear()

    def test_prepare_html_keeps_duplicate_inline_filenames_distinct(self) -> None:
        widget = MessageBodyWidget()
        email = ParsedEmail(
            subject="",
            sender="",
            recipients="",
            date="",
            plain_body="",
            html_body=(
                '<html><body><img src="cid:first@example">'
                '<img src="cid:second@example"></body></html>'
            ),
            inline_resources=[
                InlineResource(
                    content_id="first@example",
                    filename="image.png",
                    content_type="image/png",
                    payload=b"first",
                ),
                InlineResource(
                    content_id="second@example",
                    filename="image.png",
                    content_type="image/png",
                    payload=b"second",
                ),
            ],
        )

        prepared_html = widget._prepare_html(email)

        self.assertIn("1-image.png", prepared_html)
        self.assertIn("2-image.png", prepared_html)
        self.assertNotIn("cid:first@example", prepared_html)
        self.assertNotIn("cid:second@example", prepared_html)
        widget.clear()


if __name__ == "__main__":
    unittest.main()
