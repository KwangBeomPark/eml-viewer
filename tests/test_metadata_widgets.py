from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication

from eml_viewer.gui.metadata_widgets import CopyableLineEdit


class CopyableLineEditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_copy_button_is_enabled_only_for_non_empty_text(self) -> None:
        widget = CopyableLineEdit("Copy field")

        widget.setText("")
        self.assertFalse(widget._copy_button.isEnabled())

        widget.setText("Subject")
        self.assertTrue(widget._copy_button.isEnabled())

    def test_copy_button_emits_current_text(self) -> None:
        widget = CopyableLineEdit("Copy field", "Copied")
        copied: list[str] = []
        widget.copy_requested.connect(copied.append)

        widget.setText("sender@example.com")
        widget._copy_button.click()

        self.assertEqual(copied, ["sender@example.com"])
        self.assertEqual(widget._copy_button.toolTip(), "Copied")
        self.assertTrue(widget._copy_restore_timer.isActive())

        widget._restore_copy_button()

        self.assertEqual(widget._copy_button.toolTip(), "Copy field")

    def test_copy_button_precedes_the_read_only_field(self) -> None:
        widget = CopyableLineEdit("Copy field")

        self.assertIs(widget.layout().itemAt(0).widget(), widget._copy_button)
        self.assertIs(widget.layout().itemAt(1).widget(), widget._line_edit)


if __name__ == "__main__":
    unittest.main()
