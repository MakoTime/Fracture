from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QMainWindow,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QTabWidget,
)
from PySide6.QtCore import QTimer, Qt

from components.scene import SceneViewer
from .model import MeshColourmapModel


class MeshColourmapView(QMainWindow):
    """Choose a mesh colourmap and map its two fields to mesh values."""

    def __init__(self, model, colourmaps=(), parent=None, on_apply=None):
        super().__init__(parent)
        self.model = model
        self._on_apply = on_apply
        self.setWindowTitle("Configure Mesh Colourmap")
        self.resize(900, 560)

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
        settings_group = QGroupBox("Colourmap")
        settings_group.setLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.rejected.connect(self._cancel)
        buttons.clicked.connect(self._button_clicked)

        left_panel = QWidget()
        left_panel.setMinimumWidth(220)
        left_panel.setMaximumWidth(500)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(settings_group)
        left_layout.addStretch(1)

        top = QSplitter(Qt.Orientation.Horizontal)
        top.addWidget(left_panel)
        top.addWidget(self._preview_host)
        top.setChildrenCollapsible(False)
        top.setStretchFactor(0, 0)
        top.setStretchFactor(1, 1)
        top.setSizes([260, 640])

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(top)
        layout.addWidget(buttons)
        self.setCentralWidget(content)
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
        preview_data = self.model.preview_data()
        if preview_data is None:
            return
        self.preview.plotter.add_mesh(
            preview_data,
            scalars=(
                "__colourmap_rgba"
                if "__colourmap_rgba" in preview_data.point_data
                else None
            ),
            rgb="__colourmap_rgba" in preview_data.point_data,
            reset_camera=True,
        )
        self.preview.plotter.render()

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

    def _button_clicked(self, button):
        role = self.sender().buttonRole(button)
        if role in (
            QDialogButtonBox.ButtonRole.ApplyRole,
            QDialogButtonBox.ButtonRole.AcceptRole,
        ):
            self._apply()
        if role == QDialogButtonBox.ButtonRole.AcceptRole:
            self.close()

    def _apply(self):
        self.update_model()
        if self._on_apply is not None:
            self._on_apply(self.model)
        return self.model

    def _cancel(self):
        self.close()

    def closeEvent(self, event):
        window = self.parentWidget()
        while window is not None and window.parentWidget() is not None:
            window = window.parentWidget()
        tabs = (
            window.findChild(QTabWidget, "workspaceTabs")
            if window is not None
            else None
        )
        if tabs is not None:
            index = tabs.indexOf(self)
            if index >= 0:
                tabs.removeTab(index)
        super().closeEvent(event)
