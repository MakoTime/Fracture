from PySide6.QtWidgets import QFormLayout, QVBoxLayout

from src.dialog.base.popup_editor import PopupEditorView
from src.tools.widgets import NameField
from src.tools.widgets.vector import Vector3Widget

from .model import WorldConfigModel


class WorldConfigView(PopupEditorView):
    """Popup editor for the singleton world configuration."""

    def __init__(self, model: WorldConfigModel, parent=None, deduper=None):
        super().__init__(model, parent=parent, deduper=deduper)
        self.setWindowTitle("Edit World Config")
        self.resize(340, 150)

        self.name_field = NameField(model.name, deduper)
        self.name_field.setAccessibleName("World configuration name")
        self.centre_field = Vector3Widget()
        self.centre_field.setAccessibleName("World centre")

        form = QFormLayout()
        form.addRow("Name", self.name_field)
        form.addRow("Centre", self.centre_field)

        self.create_button_box()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(8)
        layout.addLayout(form)
        layout.addWidget(self.button_box)
        self.set_model(model)

    def set_model(self, model):
        self.model = model
        self.name_field.setText(model.name)
        self.centre_field.set_value(model.centre)

    def update_model(self):
        self.model.name = self.name_field.text().strip()
        self.model.centre = self.centre_field.value()
        return self.model
