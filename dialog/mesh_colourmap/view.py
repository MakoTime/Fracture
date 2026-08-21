from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QTimer

from components.scene import SceneViewer
from .model import MeshColourmapModel


class MeshColourmapView(QDialog):
    """Choose a mesh colourmap and map its two fields to mesh values."""

    def __init__(self, model, colourmaps=(), parent=None):
        super().__init__(parent)
        self.model = model
        self.setWindowTitle("Configure Mesh Colourmap")
        self.resize(760, 500)

        self.colourmap = QComboBox()
        self.colourmap.addItem("None", None)
        for colourmap in colourmaps:
            self.colourmap.addItem(colourmap.name, colourmap)

        self.field1 = QComboBox()
        self.field2 = QComboBox()
        for source_id, label in MeshColourmapModel.SOURCES:
            self.field1.addItem(label, source_id)
            self.field2.addItem(label, source_id)
        self.invert_field1 = QCheckBox("Invert Field 1")
        self.invert_field2 = QCheckBox("Invert Field 2")
        self.colourmap.currentIndexChanged.connect(self._refresh_preview)
        self.field1.currentIndexChanged.connect(self._refresh_preview)
        self.field2.currentIndexChanged.connect(self._refresh_preview)
        self.invert_field1.toggled.connect(self._refresh_preview)
        self.invert_field2.toggled.connect(self._refresh_preview)

        self._preview_host = QWidget(self)
        self._preview_host.setObjectName("meshColourmapPreviewHost")
        self._preview_layout = QVBoxLayout(self._preview_host)
        self._preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview = None
        self._preview_ready = False

        field1_row = self._field_row(self.field1, self.invert_field1)
        field2_row = self._field_row(self.field2, self.invert_field2)
        form = QFormLayout()
        form.addRow("Colourmap", self.colourmap)
        form.addRow("Field 1", field1_row)
        form.addRow("Field 2", field2_row)
        form.addRow(
            QLabel("Inputs are normalized before colourmap sampling."),
            QLabel(),
        )
        settings_group = QGroupBox("Colourmap settings")
        settings_group.setLayout(form)

        preview_group = QGroupBox("Mesh preview")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.addWidget(self._preview_host)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(8)
        content = QHBoxLayout()
        content.addWidget(settings_group, 0)
        content.addWidget(preview_group, 1)
        layout.addLayout(content, 1)
        layout.addWidget(buttons)
        self._set_model()
        QTimer.singleShot(0, self._initialize_preview)

    @staticmethod
    def _field_row(field_combo, invert_checkbox):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)
        row_layout.addWidget(field_combo, 1)
        row_layout.addWidget(invert_checkbox)
        return row

    def _initialize_preview(self):
        if self._preview_ready:
            return
        self.preview = SceneViewer(self)
        self._preview_layout.addWidget(self.preview)
        self._preview_ready = True
        self._refresh_preview()

    def _refresh_preview(self):
        if not self._preview_ready:
            return
        self.update_model()
        self.preview.clear_scene()
        preview_object = self.model.preview_object()
        if preview_object is not None:
            self.preview.add_object(preview_object)

    def _set_combo_data(self, combo, value):
        index = combo.findData(value)
        combo.setCurrentIndex(max(0, index))

    def _set_model(self):
        self._set_combo_data(self.colourmap, self.model.colourmap)
        self._set_combo_data(self.field1, self.model.field1_source)
        self._set_combo_data(self.field2, self.model.field2_source)
        self.invert_field1.setChecked(self.model.invert_field1)
        self.invert_field2.setChecked(self.model.invert_field2)

    def update_model(self):
        self.model.colourmap = self.colourmap.currentData()
        self.model.field1_source = self.field1.currentData()
        self.model.field2_source = self.field2.currentData()
        self.model.invert_field1 = self.invert_field1.isChecked()
        self.model.invert_field2 = self.invert_field2.isChecked()
        return self.model

    def _accept(self):
        self.update_model()
        self.accept()
