from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from tools.widgets.vector import Vector3Widget

from .model import MeshEditModel


class MeshEditView(QDialog):
    """Dialog for editing metadata and transforms on an existing mesh."""

    def __init__(self, model: MeshEditModel, parent=None):
        super().__init__(parent)
        self.model = model
        self.setWindowTitle("Edit Mesh")
        self.resize(520, 420)
        self._build_ui()
        self.set_model(model)

    def _build_ui(self):
        self.name = QLineEdit()
        self.comments = QTextEdit()
        self.comments.setPlaceholderText("Optional notes about this mesh")
        self.comments.setMinimumHeight(72)

        metadata = QFormLayout()
        metadata.addRow("Name", self.name)
        metadata.addRow("Comments", self.comments)

        self.scale = Vector3Widget()
        self.rotation = Vector3Widget()
        self.offset = Vector3Widget()
        self.rotation.setToolTip("Rotation in degrees around X, Y, and Z")
        transforms = QFormLayout()
        transforms.addRow("Scale", self.scale)
        transforms.addRow("Rotation (degrees)", self.rotation)
        transforms.addRow("Offset", self.offset)

        metadata_group = QGroupBox("Mesh information")
        metadata_group.setLayout(metadata)
        transform_group = QGroupBox("Transform")
        transform_group.setLayout(transforms)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self._accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)
        layout.addWidget(metadata_group)
        layout.addWidget(transform_group)
        layout.addWidget(self.button_box)

    def set_model(self, model: MeshEditModel):
        self.model = model
        self.name.setText(model.name)
        self.comments.setPlainText(model.comments)
        self.scale.set_value(model.scale)
        self.rotation.set_value(model.rotation)
        self.offset.set_value(model.offset)

    def update_model(self) -> MeshEditModel:
        self.model.name = self.name.text().strip()
        self.model.comments = self.comments.toPlainText()
        self.model.scale = self.scale.value()
        self.model.rotation = self.rotation.value()
        self.model.offset = self.offset.value()
        return self.model

    def _accept(self):
        self.update_model()
        self.accept()