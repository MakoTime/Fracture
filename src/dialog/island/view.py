import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.components.scene import SceneViewer
from src.dialog.base.tab_editor import TabEditorView
from src.tools.widgets import NameField


class IslandView(TabEditorView):
    """Workspace for configuring an Island with a live scene preview."""

    def __init__(self, model, parent=None, on_apply=None, on_close=None, deduper=None):
        super().__init__(model, parent=parent, on_apply=on_apply, on_close=on_close)
        self.setWindowTitle("Configure Island")
        self.resize(980, 620)
        self._preview_ready = False
        self._preview_host = QWidget(self)
        self._preview_layout = QVBoxLayout(self._preview_host)
        self._preview_layout.setContentsMargins(0, 0, 0, 0)

        self.name = NameField(model.name, deduper)
        self.name.setAccessibleName("Island name")

        self.offset = QDoubleSpinBox()
        self.offset.setRange(0.0, 1_000_000.0)
        self.offset.setDecimals(4)
        self.offset.setSingleStep(0.1)
        self.offset.setFixedWidth(92)
        self.offset.setValue(model.core_offset)
        self.source_mesh = QComboBox()
        self.source_mesh.setMinimumWidth(180)
        for mesh in model.source_meshes:
            self.source_mesh.addItem(mesh.name, mesh)
        source_index = self.source_mesh.findData(model.source_mesh)
        self.source_mesh.setCurrentIndex(source_index)
        self.source_mesh.currentIndexChanged.connect(self._source_mesh_changed)
        self.orbit_speed = QDoubleSpinBox()
        self.orbit_speed.setRange(-360.0, 360.0)
        self.orbit_speed.setDecimals(3)
        self.orbit_speed.setSingleStep(0.1)
        self.orbit_speed.setFixedWidth(92)
        self.orbit_speed.setValue(model.orbit_speed)
        self.curve_mesh = QCheckBox("Curve mesh around core")
        self.curve_mesh.setChecked(model.curve_mesh)

        orbit_form = QFormLayout()
        self.orbit_normal = []
        for axis, value in zip("XYZ", model.orbit_normal):
            field = QDoubleSpinBox()
            field.setRange(-1.0, 1.0)
            field.setDecimals(4)
            field.setSingleStep(0.05)
            field.setFixedWidth(92)
            field.setValue(value)
            self.orbit_normal.append(field)
            orbit_form.addRow(f"Normal {axis}", field)
        self.orbit_angle = self._angle_field(model.orbit_angle)
        orbit_form.addRow("Angle (degrees)", self.orbit_angle)
        orbit_form.addRow("Speed (degrees/sec)", self.orbit_speed)
        orbit_group = QGroupBox("Island Orbit")
        orbit_group.setLayout(orbit_form)

        placement_form = QFormLayout()
        placement_form.addRow("Name", self.name)
        placement_form.addRow("Source mesh", self.source_mesh)
        placement_form.addRow("Core offset", self.offset)
        placement_form.addRow("Geometry", self.curve_mesh)
        placement_group = QGroupBox("Island placement")
        placement_group.setLayout(placement_form)

        self.show_in_place = QCheckBox("Show in place")
        self.show_in_place.setChecked(model.show_in_place)
        self.show_path = QCheckBox("Plot orbital path")
        self.show_path.setChecked(model.show_path)
        self.show_path.setEnabled(model.show_in_place)
        self.show_in_scene = QCheckBox("Show in scene")
        self.show_in_scene.setChecked(model.show_in_scene)
        self.show_in_place.toggled.connect(self._show_in_place_changed)
        self.show_path.toggled.connect(self._refresh_preview)

        view_form = QFormLayout()
        view_form.addRow("Preview", self.show_in_place)
        view_form.addRow("Path", self.show_path)
        view_form.addRow("Scene", self.show_in_scene)
        view_group = QGroupBox("View")
        view_group.setLayout(view_form)

        settings = QWidget()
        settings_layout = QVBoxLayout(settings)
        settings_layout.addWidget(placement_group)
        settings_layout.addWidget(orbit_group)
        settings_layout.addWidget(view_group)
        settings_layout.addStretch(1)

        self.create_button_box()
        left_panel = QWidget()
        left_panel.setMinimumWidth(260)
        left_panel.setMaximumWidth(500)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(settings)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self._preview_host)
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([300, 680])

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(splitter)
        layout.addWidget(self.button_box)
        self.setCentralWidget(content)

        self.offset.valueChanged.connect(self._refresh_preview)
        self.orbit_speed.valueChanged.connect(self._refresh_preview)
        self.orbit_angle.valueChanged.connect(self._refresh_preview)
        for field in self.orbit_normal:
            field.valueChanged.connect(self._refresh_preview)
        self.curve_mesh.toggled.connect(self._refresh_preview)
        QTimer.singleShot(0, self._initialize_preview)

    @staticmethod
    def _angle_field(value):
        field = QDoubleSpinBox()
        field.setFixedWidth(92)
        field.setRange(-360.0, 360.0)
        field.setDecimals(3)
        field.setValue(value)
        return field

    def update_model(self):
        self.model.name = self.name.text().strip() or "Island"
        self.model.core_offset = self.offset.value()
        self.model.source_mesh = self.source_mesh.currentData()
        self.model.orbit_speed = self.orbit_speed.value()
        self.model.orbit_normal = tuple(field.value() for field in self.orbit_normal)
        self.model.orbit_angle = self.orbit_angle.value()
        self.model.curve_mesh = self.curve_mesh.isChecked()
        self.model.show_in_place = self.show_in_place.isChecked()
        self.model.show_path = self.show_path.isChecked()
        self.model.show_in_scene = self.show_in_scene.isChecked()
        return self.model

    def _source_mesh_changed(self):
        self.model.source_mesh = self.source_mesh.currentData()
        self._refresh_preview()

    def _show_in_place_changed(self, enabled):
        self.model.show_in_place = bool(enabled)
        self.show_path.setEnabled(bool(enabled))
        if not enabled:
            self.show_path.setChecked(False)
        self._refresh_preview()

    def _initialize_preview(self):
        if self._preview_ready:
            return
        self.preview = SceneViewer(self, show_sky_dome=False)
        self._preview_layout.addWidget(self.preview)
        self._preview_ready = True
        self._refresh_preview()

    def _refresh_preview(self):
        if not self._preview_ready:
            return
        self.update_model()
        self.preview.clear_scene()
        try:
            mesh = self.model.preview_mesh()
        except ValueError:
            mesh = None
        if mesh is not None and not self.model.show_in_place:
            mesh = mesh.copy(deep=True)
            mesh.translate(-np.asarray(mesh.center), inplace=True)
        if mesh is not None:
            self.preview.plotter.add_mesh(mesh, color="#d6a85f", reset_camera=False)
        if self.model.show_in_place:
            self.preview.plotter.add_mesh(
                self.model.core_point(),
                color="#e85d5d",
                point_size=14,
                render_points_as_spheres=True,
                reset_camera=False,
            )
            if self.model.show_path and mesh is not None:
                path = self.model.path()
                if path.n_points:
                    self.preview.plotter.add_mesh(
                        path,
                        color="#8fd3c7",
                        line_width=2,
                        reset_camera=False,
                    )
        self.preview.reset_camera()
