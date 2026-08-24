from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QWidget

from .model import DropdownModel


class DropdownView(QComboBox):
    """Qt view for a DropdownModel."""

    value_changed = Signal(object)

    def __init__(self, model: DropdownModel, parent: QWidget | None = None):
        super().__init__(parent)
        self.dropdown_model = model
        self._populate()
        self.currentIndexChanged.connect(self._on_index_changed)

    def _populate(self):
        self.blockSignals(True)
        self.clear()
        for option in self.dropdown_model.options:
            self.addItem(option.label, option.value)
            index = self.count() - 1
            self.model().item(index).setEnabled(option.enabled)

        current_index = self.findData(self.dropdown_model.current_value)
        self.setCurrentIndex(max(current_index, 0))
        self.blockSignals(False)

    def _on_index_changed(self, index):
        if index < 0:
            return
        value = self.itemData(index)
        self.dropdown_model.current_value = value
        self.value_changed.emit(value)

    def set_model(self, model: DropdownModel):
        """Replace the data model and refresh the dropdown entries."""
        self.dropdown_model = model
        self._populate()

    def current_value(self):
        return self.currentData()
