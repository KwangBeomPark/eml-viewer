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

    def test_zoom_controls_clamp_and_reset_percent(self) -> None:
        widget = MessageBodyWidget()

        widget.set_zoom_percent(25)
        self.assertEqual(widget.zoom_percent, 50)
        self.assertFalse(widget._zoom_out_button.isEnabled())

        widget.set_zoom_percent(250)
        self.assertEqual(widget.zoom_percent, 200)
        self.assertFalse(widget._zoom_in_button.isEnabled())

        widget.reset_zoom()
        self.assertEqual(widget.zoom_percent, 100)
        self.assertEqual(widget._zoom_label.text(), "100%")

    def test_html_body_gets_zoom_wrapper(self) -> None:
        widget = MessageBodyWidget()

        widget.set_zoom_percent(150)

        self.assertIn("font-size: 150%", widget._zoomed_html("<p>Hello</p>"))


if __name__ == "__main__":
    unittest.main()
