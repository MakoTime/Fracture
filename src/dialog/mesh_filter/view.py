from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.components.scene import SceneViewer
from src.dialog.base.tab_editor import TabEditorView
from src.tools.widgets import NameField, VisibleWidget

from .model import MeshFilterModel


class MeshFilterView(TabEditorView):
    def __init__(
        self,
        model: MeshFilterModel,
        transforms=(),
        parent=None,
        on_apply=None,
        on_close=None,
        deduper=None,
    ):
        TabEditorView.__init__(
            self,
            model,
            parent=parent,
            on_apply=on_apply,
            on_close=on_close,
        )
        self.transforms = tuple(transforms)
        self.setWindowTitle("Filter Generated Mesh")
        self.resize(900, 560)

        self.enabled = QCheckBox("Enable Perlin noise")
        self.transform_status = QLabel()
        self.minimum = QDoubleSpinBox()
        self.maximum = QDoubleSpinBox()
        for control in (self.minimum, self.maximum):
            control.setRange(0.0, 1.0)
            control.setDecimals(3)
            control.setSingleStep(0.01)
        self.name = NameField(model.name, deduper)
        self.name.setAccessibleName("New filtered mesh name")
        self.name.setText(model.name)
        self.show_original = VisibleWidget(True)
        self.show_original.setAccessibleName("Show original unfiltered mesh")
        self.show_original.toggled.connect(self._set_original_visibility)
        self.transform = QComboBox()
        self.transform.addItem("None", None)
        for transform in self.transforms:
            self.transform.addItem(transform.name, transform)
        self.transform.currentIndexChanged.connect(self._transform_changed)
        for control in (
            self.enabled,
            self.minimum,
            self.maximum,
        ):
            signal = getattr(control, "toggled", None) or control.valueChanged
            if control is self.enabled:
                signal.connect(self._filter_enabled_changed)
            else:
                signal.connect(self._schedule_preview_refresh)

        self._preview_refresh_timer = QTimer(self)
        self._preview_refresh_timer.setSingleShot(True)
        self._preview_refresh_timer.setInterval(80)
        self._preview_refresh_timer.timeout.connect(self._refresh_preview_now)

        self._preview_host = QWidget(self)
        self._preview_host.setObjectName("meshFilterPreviewHost")
        self._preview_layout = QVBoxLayout(self._preview_host)
        self._preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview = None
        self._preview_ready = False
        self._preview_camera_initialized = False
        self._original_actor = None

        form = QFormLayout()
        form.addRow("New mesh name", self.name)
        form.addRow("Original mesh", self.show_original)
        transform_row = QVBoxLayout()
        transform_row.addWidget(self.transform)
        transform_row.addWidget(self.transform_status)
        form.addRow("Transform", transform_row)
        form.addRow("Enabled", self.enabled)
        form.addRow("Minimum contour", self.minimum)
        form.addRow("Maximum contour", self.maximum)
        group = QGroupBox("Smoothing and Noise")
        group.setLayout(form)

        self.create_button_box()

        left_panel = QWidget()
        left_panel.setMinimumWidth(220)
        left_panel.setMaximumWidth(500)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(group)
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
        layout.addWidget(self.button_box)
        self.setCentralWidget(content)
        self._set_model()
        self._update_filter_state()
        QTimer.singleShot(0, self._initialize_preview)

    def _set_model(self):
        transform_index = self.transform.findData(self.model.perlin_noise_transform)
        self.transform.setCurrentIndex(max(0, transform_index))
        self.enabled.setChecked(self.model.noise_enabled)
        self.minimum.setValue(self.model.noise_minimum)
        self.maximum.setValue(self.model.noise_maximum)
        self.transform_status.setText(
            "No filter transform selected"
            if not self.model.has_transform
            else "Perlin noise transform selected"
        )

    def update_model(self):
        self.model.name = self.name.unique_name() or "Filtered Mesh"
        self.model.noise_enabled = self.enabled.isChecked()
        self.model.noise_minimum = self.minimum.value()
        self.model.noise_maximum = self.maximum.value()
        return self.model

    def _transform_changed(self):
        self.model.perlin_noise_transform = self.transform.currentData()
        if self.model.has_transform:
            self.model.noise_enabled = True
        self._set_model()
        self._update_filter_state()
        self._schedule_preview_refresh()

    def _filter_enabled_changed(self):
        self.update_model()
        self._update_filter_state()
        self._schedule_preview_refresh()

    def _update_filter_state(self):
        has_transform = self.model.has_transform
        self.enabled.setEnabled(has_transform)
        self.enabled.setChecked(bool(has_transform and self.model.noise_enabled))
        if self.button_box is not None:
            self.apply_button.setEnabled(self.model.filter_enabled)
            self.ok_button.setEnabled(self.model.filter_enabled)

    def _initialize_preview(self):
        if self._preview_ready:
            return
        self.preview = SceneViewer(self)
        self.preview.setObjectName("meshFilterPreview")
        self._preview_layout.addWidget(self.preview)
        self._preview_ready = True
        self._schedule_preview_refresh()

    def _set_original_visibility(self, visible):
        if self._original_actor is None:
            self._schedule_preview_refresh()
            return
        self._original_actor.SetVisibility(bool(visible))
        if self.preview is not None:
            self.preview.plotter.render()

    def _schedule_preview_refresh(self):
        if self._preview_ready:
            self._preview_refresh_timer.start()

    def _refresh_preview_now(self):
        if not self._preview_ready:
            return
        self.update_model()
        self.preview.clear_scene()
        self._original_actor = None
        reset_camera = not self._preview_camera_initialized
        source_data = self.model.source_mesh.mesh_data
        has_original = (
            self.show_original.is_visible()
            and source_data is not None
            and source_data.n_points
        )
        if has_original:
            self._original_actor = self.preview.plotter.add_mesh(
                source_data,
                color="#a8b0b8",
                opacity=0.35,
                reset_camera=reset_camera,
            )
            self._original_actor.SetVisibility(self.show_original.is_visible())
        if not self.model.filter_enabled:
            self.preview.plotter.render()
            return
        mesh_data = self.model.preview_mesh_data()
        if mesh_data is not None and mesh_data.n_points:
            self.preview.plotter.add_mesh(
                mesh_data,
                color="#8ecae6",
                opacity=0.85,
                reset_camera=reset_camera and not has_original,
            )
        if has_original or (mesh_data is not None and mesh_data.n_points):
            self._preview_camera_initialized = True
        self.preview.plotter.render()

    def apply_model(self):
        if not self.model.filter_enabled:
            return None
        return self.model
