from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QVBoxLayout, QWidget

from eml_viewer.gui.i18n import tr
from eml_viewer.models.app_settings import AppSettings


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("settings.title"))

        self._language_combo = QComboBox(self)
        self._language_combo.addItem(tr("language.ko"), "ko")
        self._language_combo.addItem(tr("language.en"), "en")
        self._set_combo_value(self._language_combo, settings.language)

        self._theme_combo = QComboBox(self)
        self._theme_combo.addItem(tr("theme.system"), "system")
        self._theme_combo.addItem(tr("theme.light"), "light")
        self._theme_combo.addItem(tr("theme.dark"), "dark")
        self._set_combo_value(self._theme_combo, settings.theme)

        form_layout = QFormLayout()
        form_layout.addRow(tr("settings.language"), self._language_combo)
        form_layout.addRow(tr("settings.theme"), self._theme_combo)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText(tr("settings.ok"))
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("settings.cancel"))
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addWidget(button_box)

    @property
    def language(self) -> str:
        return str(self._language_combo.currentData())

    @property
    def theme(self) -> str:
        return str(self._theme_combo.currentData())

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)
