from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QDoubleSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from tools.widgets.vector import Vector3Widget

from .model import MeshImportModel


class MeshImportView(QDialog):
    """Dialog for reviewing mesh metadata and transform values."""

    MESH_FILTER = (
        "Mesh files (*.obj *.stl *.ply *.vtk *.vtp *.vtu *.glb *.gltf);;"
        "All files (*)"
    )

    def __init__(self, model: MeshImportModel, parent=None):
        super().__init__(parent)
        self.model = model
        self.setWindowTitle("Import Mesh")
        self.resize(520, 520)
        self._build_ui()
        self.set_model(model)

    def _build_ui(self):
        self.source_path = QLineEdit()
        self.source_path.setPlaceholderText("Select a mesh file")
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._browse)
        source_layout = QHBoxLayout()
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.addWidget(self.source_path, 1)
        source_layout.addWidget(self.browse_button)

        self.name = QLineEdit()
        self.comments = QTextEdit()
        self.comments.setPlaceholderText("Optional notes about this mesh")
        self.comments.setMinimumHeight(72)
        self.add_to_scene = QCheckBox("Add to scene/table")

        metadata = QFormLayout()
        metadata.addRow("Mesh file", source_layout)
        metadata.addRow("Name", self.name)
        metadata.addRow("Comments", self.comments)
        metadata.addRow("Load", self.add_to_scene)

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

    def set_model(self, model: MeshImportModel):
        """Populate the dialog from a mesh import model."""
        self.model = model
        self.source_path.setText(model.source_path)
        self.name.setText(model.name)
        self.comments.setPlainText(model.comments)
        self.add_to_scene.setChecked(model.add_to_scene)
        self.scale.set_value(model.scale)
        self.rotation.set_value(model.rotation)
        self.offset.set_value(model.offset)

    def update_model(self) -> MeshImportModel:
        """Copy the current widget values into and return the model."""
        self.model.source_path = self.source_path.text().strip()
        self.model.name = self.name.text().strip() or "Imported Mesh"
        self.model.comments = self.comments.toPlainText()
        self.model.add_to_scene = self.add_to_scene.isChecked()
        self.model.scale = self.scale.value()
        self.model.rotation = self.rotation.value()
        self.model.offset = self.offset.value()
        return self.model

    def _accept(self):
        self.update_model()
        self.accept()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Mesh",
            str(Path.home()),
            self.MESH_FILTER,
        )
        if path:
            self.source_path.setText(path)
            if self.name.text().strip() in ("", "Imported Mesh"):
                self.name.setText(Path(path).stem)


class ElevationImportView(MeshImportView):
    """Dialog for importing a grayscale image as elevation data."""

    MESH_FILTER = "Elevation images (*.bmp *.jpg *.jpeg *.png *.tif *.tiff);;All files (*)"

    def __init__(self, model: MeshImportModel, parent=None):
        super().__init__(model, parent)
        self.setWindowTitle("Import Mesh from Elevation Data")
        self._build_elevation_controls()
        self.set_model(model)

    def _build_elevation_controls(self):
        self.low_threshold = QDoubleSpinBox()
        self.low_threshold.setRange(0.0, 255.0)
        self.low_threshold.setDecimals(2)
        self.high_threshold = QDoubleSpinBox()
        self.high_threshold.setRange(0.0, 255.0)
        self.high_threshold.setDecimals(2)
        self.vertical_scale = QDoubleSpinBox()
        self.vertical_scale.setRange(0.0, 10000.0)
        self.vertical_scale.setDecimals(3)
        self.vertical_scale.setSingleStep(0.1)
        self.low_threshold.valueChanged.connect(
            self.high_threshold.setMinimum
        )
        self.high_threshold.valueChanged.connect(
            self.low_threshold.setMaximum
        )

        controls = QFormLayout()
        controls.addRow("Low threshold", self.low_threshold)
        controls.addRow("High threshold", self.high_threshold)
        controls.addRow("Vertical scale", self.vertical_scale)
        group = QGroupBox("Elevation mapping")
        group.setLayout(controls)
        self.layout().insertWidget(self.layout().count() - 1, group)

    def set_model(self, model: MeshImportModel):
        super().set_model(model)
        if hasattr(self, "low_threshold"):
            self.low_threshold.setValue(model.low_threshold)
            self.high_threshold.setValue(model.high_threshold)
            self.vertical_scale.setValue(model.vertical_scale)

    def update_model(self) -> MeshImportModel:
        super().update_model()
        self.model.low_threshold = self.low_threshold.value()
        self.model.high_threshold = self.high_threshold.value()
        self.model.vertical_scale = self.vertical_scale.value()
        return self.model
