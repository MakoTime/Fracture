from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from tools.widgets.vector import Vector3Widget
from dialog.mesh_colourmap import MeshColourmapModel, create_mesh_colourmap_dialog

from .model import MeshEditModel


class MeshEditView(QDialog):
    """Dialog for editing metadata and transforms on an existing mesh."""

    def __init__(self, model: MeshEditModel, colourmaps=(), parent=None):
        super().__init__(parent)
        self.model = model
        self.setWindowTitle("Edit Mesh")
        self.resize(520, 420)
        self._build_ui()
        self._colourmaps = tuple(colourmaps)
        self.set_model(model)

    def _build_ui(self):
        self.name = QLineEdit()
        self.comments = QTextEdit()
        self.colourmap = QPushButton("Configure Colourmap...")
        self.colourmap.clicked.connect(self._configure_colourmap)
        self.comments.setPlaceholderText("Optional notes about this mesh")
        self.comments.setMinimumHeight(72)

        metadata = QFormLayout()
        metadata.addRow("Name", self.name)
        metadata.addRow("Comments", self.comments)
        metadata.addRow("Colourmap", self.colourmap)

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
        self._update_colourmap_label()
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

    def _configure_colourmap(self):
        field1, field2 = self.model.colourmap_field_sources
        invert1, invert2 = self.model.colourmap_field_inversions
        selected = next(
            (
                colourmap
                for colourmap in self._colourmaps
                if getattr(colourmap, "block_object", colourmap)
                is self.model.colourmap
            ),
            None,
        )
        def apply_colourmap(model):
            self.model.colourmap = model.colourmap
            self.model.colourmap_field_sources = (
                model.field1_source,
                model.field2_source,
            )
            self._update_colourmap_label()

        dialog = create_mesh_colourmap_dialog(
            MeshColourmapModel(
                mesh_object=self.model.mesh_object,
                colourmap=selected,
                field1_source=field1,
                field2_source=field2,
                invert_field1=invert1,
                invert_field2=invert2,
            ),
            colourmaps=self._colourmaps,
            parent=self,
            on_apply=apply_colourmap,
        )
        dialog.show()

    def _update_colourmap_label(self):
        name = getattr(self.model.colourmap, "name", "None")
        self.colourmap.setText(f"Colourmap: {name}")

    def _accept(self):
        self.update_model()
        self.accept()