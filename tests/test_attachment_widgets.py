from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from eml_viewer.gui.attachment_widgets import AttachmentPanel
from eml_viewer.models.attachment_data import AttachmentInfo


class AttachmentPanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_panel_hides_when_no_attachments(self) -> None:
        panel = AttachmentPanel()

        panel.set_attachments([])

        self.assertTrue(panel.isHidden())
        self.assertTrue(panel._table.isHidden())

    def test_panel_defaults_to_collapsed_summary_when_attachments_exist(self) -> None:
        panel = AttachmentPanel()
        attachments = [
            AttachmentInfo(index=1, filename="a.txt", content_type="text/plain", size=1024),
            AttachmentInfo(index=2, filename="b.pdf", content_type="application/pdf", size=2048),
        ]

        panel.set_attachments(attachments)

        self.assertFalse(panel.isHidden())
        self.assertTrue(panel._table.isHidden())
        self.assertEqual(panel._toggle_button.text(), "Expand")
        self.assertEqual(panel._title_label.text(), "Attachments 2 · 3.0 KB · Selected 0")
        self.assertLessEqual(panel.maximumHeight(), 48)

    def test_toggle_expands_list_and_caps_height(self) -> None:
        panel = AttachmentPanel()
        attachments = [
            AttachmentInfo(index=index, filename=f"{index}.txt", content_type="text/plain", size=1)
            for index in range(1, 10)
        ]

        panel.set_attachments(attachments)
        collapsed_height = panel.maximumHeight()
        panel._toggle_button.click()

        self.assertFalse(panel._table.isHidden())
        self.assertEqual(panel._toggle_button.text(), "Collapse")
        self.assertGreater(panel.maximumHeight(), collapsed_height)
        self.assertLessEqual(panel.maximumHeight(), 42 + 34 + (6 * 30))

    def test_checked_rows_drive_selection_and_button_state(self) -> None:
        panel = AttachmentPanel()
        attachments = [
            AttachmentInfo(index=1, filename="a.txt", content_type="text/plain", size=1),
            AttachmentInfo(index=2, filename="b.txt", content_type="text/plain", size=1),
        ]

        panel.set_attachments(attachments)
        panel._toggle_button.click()
        self.assertFalse(panel._save_button.isEnabled())

        panel._table.item(0, 0).setCheckState(Qt.CheckState.Checked)

        self.assertEqual(panel.selected_attachments(), [attachments[0]])
        self.assertTrue(panel._save_button.isEnabled())
        self.assertEqual(panel._title_label.text(), "Attachments 2 · 2 B · Selected 1")


if __name__ == "__main__":
    unittest.main()
