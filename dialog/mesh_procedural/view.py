from contextlib import contextmanager

import numpy as np
import pyvista as pv
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from components.scene import SceneViewer
from dialog.base.tab_editor import TabEditorView
from tools.widgets import IntegerVector3Widget, NameField, VisibleWidget

from .model import MeshProceduralModel


class MeshProceduralView(TabEditorView):
    """Workspace for generating procedural meshes from a series of transforms."""

    GRID_POINT_SIZE_MIN = 2.0
    GRID_POINT_SIZE_MAX = 9.0
    GRID_POINT_SIZE_REFERENCE_COUNT = 1_000

    def __init__(
        self,
        parent=None,
        model=None,
        on_apply=None,
        on_close=None,
        tree_search=None,
        deduper=None,
        transforms=(),
    ):
        TabEditorView.__init__(
            self,
            model or MeshProceduralModel(),
            parent=parent,
            on_apply=on_apply,
            on_close=on_close,
        )
        self.setWindowTitle("Generate Procedural Mesh")
        self.resize(900, 560)
        self.tree_search = tree_search
        self.transforms = tuple(transforms)
        self._applied_mesh = None
        self._preview_host = QWidget(self)
        self._preview_host.setObjectName("meshPreviewHost")
        self.preview = None
        self._preview_ready = False
        self._preview_update_pending = False
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._render_preview)
        self._preview_block = None
        self._preview_layout = QVBoxLayout(self._preview_host)
        self._preview_layout.setContentsMargins(0, 0, 0, 0)
        deduper = deduper or (lambda name: name)
        self.name_field = NameField(self.model.name, deduper)
        self.name_field.setAccessibleName("Generated mesh name")
        self.grid_size = IntegerVector3Widget()
        self.grid_size.set_value(self.model.grid_size)
        self.grid_visibility = VisibleWidget(self.model.show_grid)
        self.grid_visibility.setAccessibleName("Show generated grid points")
        self.grid_visibility.toggled.connect(self._update_preview)
        for spin in self.grid_size._spins:
            spin.valueChanged.connect(self._grid_size_changed)

        generation_form = QFormLayout()
        generation_form.addRow("Name", self.name_field)
        generation_form.addRow("Grid size", self.grid_size)
        generation_group = QGroupBox("Generation")
        generation_group.setLayout(generation_form)

        self.grid_point_alpha = QSlider(Qt.Orientation.Horizontal)
        self.grid_point_alpha.setRange(0, 100)
        self.grid_point_alpha.setValue(100)
        self.grid_point_alpha.setToolTip("Grid point opacity")
        self.grid_point_alpha.valueChanged.connect(self._grid_point_alpha_changed)
        self.grid_point_alpha_value = QLabel()
        self._update_grid_point_alpha_label(100)

        visibility_row = QHBoxLayout()
        visibility_row.addWidget(self.grid_visibility)
        visibility_row.addStretch(1)

        point_form = QFormLayout()
        point_form.addRow("Visible", visibility_row)
        alpha_row = QHBoxLayout()
        alpha_row.addWidget(self.grid_point_alpha, 1)
        alpha_row.addWidget(self.grid_point_alpha_value)
        point_form.addRow("Opacity", alpha_row)
        point_group = QGroupBox("Grid points")
        point_group.setLayout(point_form)

        self.noise_object_combo = QComboBox()
        self.noise_object_combo.addItem("None", None)
        for transform in self.transforms:
            self.noise_object_combo.addItem(transform.name, transform)
        self.noise_object_combo.currentIndexChanged.connect(self._noise_object_changed)
        if self.noise_object_combo.count():
            self.model.perlin_noise_transform = self.noise_object_combo.currentData()
            self.seed_line_edit = QLineEdit(str(self.model.seed))
        else:
            self.seed_line_edit = QLineEdit(str(self.model.seed))
        self.seed_line_edit.textChanged.connect(self._seed_changed)

        self.upper_threshold = QSlider(Qt.Orientation.Horizontal)
        self.upper_threshold.setRange(0, 100)
        self.upper_threshold.setValue(round(self.model.upper_threshold * 100))
        self.upper_threshold.setToolTip("Upper threshold")
        self.upper_threshold.valueChanged.connect(self._upper_threshold_changed)
        self.upper_threshold_value = QLabel()
        self._update_upper_threshold_label(self.upper_threshold.value())

        self.lower_threshold = QSlider(Qt.Orientation.Horizontal)
        self.lower_threshold.setRange(0, 100)
        self.lower_threshold.setValue(round(self.model.lower_threshold * 100))
        self.lower_threshold.setToolTip("Lower threshold")
        self.lower_threshold.valueChanged.connect(self._lower_threshold_changed)
        self.lower_threshold_value = QLabel()
        self._update_lower_threshold_label(self.lower_threshold.value())

        overwrite_seed_button = QPushButton("Overwrite seed")
        overwrite_seed_button.setToolTip(
            "Overwrite the seed of the selected noise object"
        )
        overwrite_seed_button.clicked.connect(self._overwrite_noise_seed)
        seed_row = QHBoxLayout()
        seed_row.addWidget(self.seed_line_edit)
        seed_row.addWidget(overwrite_seed_button)

        lower_threshold_row = QHBoxLayout()
        lower_threshold_row.addWidget(self.lower_threshold, 1)
        lower_threshold_row.addWidget(self.lower_threshold_value)

        upper_threshold_row = QHBoxLayout()
        upper_threshold_row.addWidget(self.upper_threshold, 1)
        upper_threshold_row.addWidget(self.upper_threshold_value)

        procedural_form = QFormLayout()
        procedural_form.addRow("Noise object", self.noise_object_combo)
        procedural_form.addRow("Seed", seed_row)
        procedural_form.addRow("Lower threshold", lower_threshold_row)
        procedural_form.addRow("Upper threshold", upper_threshold_row)

        procedural_group = QGroupBox("Procedural generation")
        procedural_group.setLayout(procedural_form)

        left_panel = QWidget()
        left_panel.setMinimumWidth(220)
        left_panel.setMaximumWidth(500)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        left_layout.addWidget(generation_group)
        left_layout.addWidget(point_group)
        left_layout.addWidget(procedural_group)
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
        self.create_button_box()
        layout.addWidget(self.button_box)
        self.setCentralWidget(content)
        self._reset_camera = False
        QTimer.singleShot(0, self._initialize_preview)

    def _initialize_preview(self):
        """Construct the native VTK widget after the window enters the event loop."""
        if self._preview_ready or not self.isVisible():
            return
        self.preview = SceneViewer(self)
        self.preview.setObjectName("meshPreview")
        self._preview_layout.addWidget(self.preview)
        self._preview_ready = True
        with self.change_camera():
            self._update_preview()
        QTimer.singleShot(0, self._zoom_initial_preview)

    def _zoom_initial_preview(self):
        """Zoom after the initial generated grid has been fitted."""
        if self._preview_ready and self.isVisible():
            self.preview.zoom_camera(0.65)

    @contextmanager
    def change_camera(self):
        self._reset_camera = True
        try:
            yield
        finally:
            self._reset_camera = False

    def apply_model(self):
        self.model.name = self.name_field.unique_name() or "Procedural Mesh"
        self.model.grid_size = self.grid_size.value()
        self.model.show_grid = self.grid_visibility.is_visible()
        self.model.upper_threshold = self.upper_threshold.value() / 100.0
        self.model.lower_threshold = self.lower_threshold.value() / 100.0
        self._applied_mesh = self.model.generate()
        if self._on_apply is not None:
            self._on_apply(self._applied_mesh)
        return self._applied_mesh

    def _grid_size_changed(self):
        self.model.grid_size = self.grid_size.value()
        with self.change_camera():
            self._update_preview()

    def _grid_point_alpha_changed(self, value):
        self._update_grid_point_alpha_label(value)
        self._update_preview()

    def _update_upper_threshold_label(self, value):
        self.upper_threshold_value.setText(f"{value}%")

    def _update_lower_threshold_label(self, value):
        self.lower_threshold_value.setText(f"{value}%")

    def _upper_threshold_changed(self, value):
        self._update_upper_threshold_label(value)
        self.model.upper_threshold = value / 100.0
        self._update_preview()

    def _lower_threshold_changed(self, value):
        self._update_lower_threshold_label(value)
        self.model.lower_threshold = value / 100.0
        self._update_preview()

    def _noise_object_changed(self, index):
        self.model.perlin_noise_transform = self.noise_object_combo.currentData()
        self.seed_line_edit.setText(str(self.model.seed))
        self._update_preview()

    def _overwrite_noise_seed(self):
        self._seed_changed(self.seed_line_edit.text())

    def _seed_changed(self, value):
        try:
            self.model.seed = int(value)
        except (TypeError, ValueError):
            return
        self._update_preview()

    def _update_grid_point_alpha_label(self, value):
        self.grid_point_alpha_value.setText(f"{value}%")

    @staticmethod
    def _build_grid_point_cloud(points, grid_data):
        values = np.asarray(grid_data, dtype=float)
        if len(points) != values.size:
            raise ValueError("grid point count must match grid data size")
        point_cloud = pv.PolyData(np.asarray(points, dtype=np.float32))
        point_cloud.point_data["grid_value"] = values.ravel(order="C")
        return point_cloud

    @classmethod
    def _adaptive_grid_point_size(cls, point_count):
        if point_count < 1:
            return cls.GRID_POINT_SIZE_MAX
        size = 7.0 * (cls.GRID_POINT_SIZE_REFERENCE_COUNT / point_count) ** (1 / 3)
        return float(
            np.clip(
                size,
                cls.GRID_POINT_SIZE_MIN,
                cls.GRID_POINT_SIZE_MAX,
            )
        )

    def _update_preview(self):
        if not self._preview_ready:
            return
        self._preview_update_pending = True
        self._preview_timer.start(60)

    def _render_preview(self):
        self._preview_update_pending = False
        if not self._preview_ready:
            return
        self.model.grid_size = self.grid_size.value()
        self.model.show_grid = self.grid_visibility.is_visible()
        self.preview.clear_scene()
        self._dispose_preview_block()
        task = self.model.to_mesh_generate_task()
        block = task.execute(task.prepare())
        self._preview_block = block
        if block.mesh_data.n_points:
            self.preview.plotter.add_mesh(
                block.mesh_data,
                opacity=0.85,
                scalars="values",
                cmap="viridis",
                clim=(0.0, 1.0),
                show_scalar_bar=True,
                scalar_bar_args={"title": "Noise value"},
                reset_camera=self._reset_camera,
            )
        elif self.model.show_grid:
            points = self._build_grid_point_cloud(
                self.model.grid_points(),
                block.grid_data,
            )
            self.preview.plotter.add_mesh(
                points,
                style="points",
                point_size=self._adaptive_grid_point_size(len(points.points)),
                opacity=self.grid_point_alpha.value() / 100,
                scalars="grid_value",
                cmap="viridis",
                clim=(0.0, 1.0),
                show_scalar_bar=True,
                scalar_bar_args={"title": "Grid value"},
                reset_camera=self._reset_camera,
            )
        self.preview.plotter.render()

    def _dispose_preview_block(self):
        block = self._preview_block
        self._preview_block = None
        if block is None or block.is_destroyed():
            return
        block.set_perlin_noise_transform(None, notify=False)
        block.destroy()

    def closeEvent(self, event):
        self._preview_timer.stop()
        self._preview_update_pending = False
        self._dispose_preview_block()
        if self.preview is not None:
            self.preview.plotter.clear()
        self.model.perlin_noise_transform = None
        super().closeEvent(event)

    def ok_button(self):
        if self.model.perlin_noise_transform is None:
            self.cancel_button().click()
            return
        super().ok_button()
