from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def apply_theme(app: QApplication | None, theme: str) -> None:
    if app is None:
        return

    if theme == "dark":
        app.setPalette(_dark_palette())
        app.setStyleSheet(_dark_style_sheet())
        return

    app.setPalette(app.style().standardPalette())
    app.setStyleSheet("")


def _dark_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(32, 34, 37))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(238, 238, 238))
    palette.setColor(QPalette.ColorRole.Base, QColor(24, 26, 29))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(38, 41, 45))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(238, 238, 238))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(24, 26, 29))
    palette.setColor(QPalette.ColorRole.Text, QColor(238, 238, 238))
    palette.setColor(QPalette.ColorRole.Button, QColor(43, 47, 52))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(238, 238, 238))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 98, 98))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    return palette


def _dark_style_sheet() -> str:
    return """
    QMenuBar, QMenu, QStatusBar, QToolBar {
        background: #202225;
        color: #eeeeee;
    }
    QGroupBox {
        border: 1px solid #4b4f58;
        margin-top: 10px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
    }
    QLineEdit, QTextBrowser, QWebEngineView, QTableWidget, QComboBox {
        background: #181a1d;
        color: #eeeeee;
        border: 1px solid #4b4f58;
        selection-background-color: #2a82da;
    }
    QPushButton {
        background: #2b2f34;
        color: #eeeeee;
        border: 1px solid #5a606a;
        padding: 5px 10px;
    }
    QPushButton:disabled {
        color: #858b94;
        border-color: #3d4148;
    }
    QLabel#plainNotice {
        color: #f0c36a;
    }
    QLabel#remoteNotice {
        color: #f0c36a;
    }
    """
