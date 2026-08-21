from PySide6.QtCore import QTimer, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QCheckBox,
    QComboBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSplitter,
    QSpinBox,
    QStyle,
    QSlider,
    QToolButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import numpy as np
import pyvista as pv

from components.scene import SceneViewer
from tools.widgets import VisibleWidget

from .model import MeshGenerateModel
from dialog.mesh_mask import create_surface_mask_dialog


from contextlib import contextmanager


class CompactSpinBox(QWidget):
    """Spinbox with large, tightly stacked increment and decrement buttons."""

    valueChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spinbox = QSpinBox()
        self.spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spinbox.setMinimumWidth(42)
        self.spinbox.valueChanged.connect(self.valueChanged)

        self.up_button = self._create_button(QStyle.StandardPixmap.SP_ArrowUp)
        self.down_button = self._create_button(QStyle.StandardPixmap.SP_ArrowDown)
        self.up_button.clicked.connect(self.spinbox.stepUp)
        self.down_button.clicked.connect(self.spinbox.stepDown)

        buttons = QVBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(0)
        buttons.addWidget(self.up_button)
        buttons.addWidget(self.down_button)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.addWidget(self.spinbox)
        layout.addLayout(buttons)

    @staticmethod
    def _create_button(pixmap):
        button = QToolButton()
        button.setIcon(button.style().standardIcon(pixmap))
        button.setIconSize(QSize(12, 12))
        button.setFixedSize(20, 13)
        button.setAutoRepeat(True)
        button.setAutoRepeatDelay(350)
        button.setAutoRepeatInterval(60)
        return button

    def setRange(self, minimum, maximum):
        self.spinbox.setRange(minimum, maximum)

    def setValue(self, value):
        self.spinbox.setValue(value)

    def value(self):
        return self.spinbox.value()


class NormalizedSpinBox(QDoubleSpinBox):
    """Editor for normalized values in the inclusive range from zero to one."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0.0, 1.0)
        self.setDecimals(3)
        self.setSingleStep(0.01)


class IntegerVector3Widget(QWidget):
    """Compact editor for three positive integer dimensions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._spins = []
        for axis in "XYZ":
            label = QLabel(axis)
            spin = CompactSpinBox()
            spin.setRange(1, 1_000)
            spin.setValue(10)
            spin.setToolTip(f"{axis} grid dimension")
            setattr(self, axis.lower(), spin)
            self._spins.append(spin)
            layout.addWidget(label)
            layout.addWidget(spin)

    def value(self):
        return tuple(spin.value() for spin in self._spins)

    def set_value(self, value):
        if len(value) != 3:
            raise ValueError("expected three grid dimensions")
        for spin, component in zip(self._spins, value):
            spin.setValue(int(component))


class GenerateMeshWindow(QMainWindow):
    """Workspace for configuring and applying a basic generated mesh."""

    GRID_POINT_SIZE_MIN = 2.0
    GRID_POINT_SIZE_MAX = 9.0
    GRID_POINT_SIZE_REFERENCE_COUNT = 1_000

    def __init__(self, parent=None, model=None, on_apply=None, tree_search=None):
        super().__init__(parent)
        self.setWindowTitle("Generate Mesh")
        self.resize(900, 560)
        self.model = model or MeshGenerateModel()
        self.model.noise_enabled = False
        self.model.perlin_noise_transform = None
        self._on_apply = on_apply
        self.tree_search = tree_search
        self._applied_mesh = None
        self._preview_host = QWidget(self)
        self._preview_host.setObjectName("meshPreviewHost")
        self.preview = None
        self._preview_ready = False
        self._preview_layout = QVBoxLayout(self._preview_host)
        self._preview_layout.setContentsMargins(0, 0, 0, 0)
        self.name_field = QLineEdit()
        self.name_field.setPlaceholderText("Generated Mesh")
        self.name_field.setText(self.model.name)
        self.name_field.setAccessibleName("Generated mesh name")
        self.grid_size = IntegerVector3Widget()
        self.grid_size.set_value(self.model.grid_size)
        self.grid_visibility = VisibleWidget(self.model.show_grid)
        self.grid_visibility.setAccessibleName("Show generated grid points")
        self.grid_visibility.toggled.connect(self._update_preview)
        self.flexible_grid = QCheckBox("Flexible")
        self.flexible_grid.setChecked(self.model.flexible_grid)
        self.flexible_grid.setAccessibleName("Allow flexible grid size")
        self.flexible_grid.toggled.connect(self._set_grid_flexible)
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
        visibility_row.addWidget(self.flexible_grid)
        visibility_row.addStretch(1)

        point_form = QFormLayout()
        point_form.addRow("Visible", visibility_row)
        alpha_row = QHBoxLayout()
        alpha_row.addWidget(self.grid_point_alpha, 1)
        alpha_row.addWidget(self.grid_point_alpha_value)
        point_form.addRow("Opacity", alpha_row)
        point_group = QGroupBox("Grid points")
        point_group.setLayout(point_form)

        mask_form = QFormLayout()
        self.mask_buttons = {}
        for axis in "XYZ":
            button = QPushButton(f"Configure {axis} mask")
            button.clicked.connect(lambda checked=False, axis=axis: self._edit_mask(axis))
            self.mask_buttons[axis] = button
            mask_form.addRow(f"{axis} surface", button)
        self.show_mask_surface = VisibleWidget(self.model.show_mask_surface)
        self.show_mask_surface.setAccessibleName("Show surface mask preview")
        self.show_mask_surface.toggled.connect(self._update_preview)
        self.flexible_masks = QCheckBox("Flexible")
        self.flexible_masks.setChecked(self.model.flexible_masks)
        self.flexible_masks.setAccessibleName("Allow surface masks to resize with the grid")
        self.flexible_masks.toggled.connect(self._set_masks_flexible)
        mask_visibility_row = QHBoxLayout()
        mask_visibility_row.addWidget(self.show_mask_surface)
        mask_visibility_row.addWidget(self.flexible_masks)
        mask_visibility_row.addStretch(1)
        mask_form.addRow("Visible", mask_visibility_row)
        mask_group = QGroupBox("Surface masks")
        mask_group.setLayout(mask_form)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Ok
        )
        self.button_box.rejected.connect(self._cancel)
        self.button_box.clicked.connect(self._button_clicked)

        left_panel = QWidget()
        left_panel.setMinimumWidth(220)
        left_panel.setMaximumWidth(500)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        left_layout.addWidget(generation_group)
        left_layout.addWidget(point_group)
        left_layout.addWidget(mask_group)
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
        self._reset_camera = False
        QTimer.singleShot(0, self._initialize_preview)

    def _initialize_preview(self):
        """Construct the native VTK widget after the window enters the event loop."""
        if self._preview_ready:
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
        self.preview.zoom_camera(0.65)
        
    @contextmanager
    def change_camera(self):
        self._reset_camera = True
        try:
            yield
        finally:
            self._reset_camera = False

    def _button_clicked(self, button):
        role = self.button_box.buttonRole(button)
        if role in (
            QDialogButtonBox.ButtonRole.ApplyRole,
            QDialogButtonBox.ButtonRole.AcceptRole,
        ):
            self._apply()
        if role == QDialogButtonBox.ButtonRole.AcceptRole:
            self.close()

    def _cancel(self):
        self.close()

    def _apply(self):
        self.model.name = self.name_field.text().strip() or "Generated Mesh"
        self.model.grid_size = self.grid_size.value()
        self.model.show_grid = self.grid_visibility.is_visible()
        self.model.show_mask_surface = self.show_mask_surface.is_visible()
        self.model.flexible_masks = self.flexible_masks.isChecked()
        self.model.flexible_grid = self.flexible_grid.isChecked()
        self._applied_mesh = self.model.generate()
        if self._on_apply is not None:
            self._on_apply(self._applied_mesh)
        return self._applied_mesh

    def _grid_size_changed(self):
        if not self.flexible_grid.isChecked():
            return
        for axis in "xyz":
            mask = self.model.get_mask(axis)
            if mask is not None and mask.shape != self.model.mask_shape(axis):
                if self.flexible_masks.isChecked():
                    setattr(
                        self.model,
                        f"{axis}_mask",
                        self._resize_mask(mask, self.model.mask_shape(axis)),
                    )
                else:
                    setattr(self.model, f"{axis}_mask", None)
        with self.change_camera():
            self._update_preview()

    def _set_grid_flexible(self, flexible):
        self.model.flexible_grid = bool(flexible)
        self.grid_size.setEnabled(bool(flexible))

    def _set_masks_flexible(self, flexible):
        self.model.flexible_masks = bool(flexible)

    def _grid_point_alpha_changed(self, value):
        self._update_grid_point_alpha_label(value)
        self._update_preview()

    def _update_grid_point_alpha_label(self, value):
        self.grid_point_alpha_value.setText(f"{value}%")

    def _edit_mask(self, axis):
        editor = create_surface_mask_dialog(
            axis=axis,
            shape=self.model.mask_shape(axis),
            mask=self.model.get_mask(axis),
            parent=self,
        )
        if editor.exec() == QDialog.DialogCode.Accepted:
            self.model.set_mask(axis, editor.model.mask)
            with self.change_camera():
                self._update_preview()

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
        size = 7.0 * (
            cls.GRID_POINT_SIZE_REFERENCE_COUNT / point_count
        ) ** (1 / 3)
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
        self.model.noise_enabled = False
        self.model.perlin_noise_transform = None
        self.model.grid_size = self.grid_size.value()
        self.model.show_grid = self.grid_visibility.is_visible()
        self.model.show_mask_surface = self.show_mask_surface.is_visible()
        self.preview.clear_scene()
        task = self.model.to_mesh_generate_task()
        block = task.execute(task.prepare())
        if self.model.show_mask_surface and block.mask_mesh_data is not None:
            if block.mask_mesh_data.n_points:
                self.preview.plotter.add_mesh(
                    block.mask_mesh_data,
                    color="#f2a65a",
                    opacity=0.45,
                    reset_camera=self._reset_camera,
                )
        if block.mesh_data.n_points:
            self.preview.plotter.add_mesh(
                block.mesh_data,
                color="#8ecae6",
                opacity=0.85,
                reset_camera=self._reset_camera,
            )
        if not self.model.show_grid:
            self.preview.plotter.render()
            return
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

    @staticmethod
    def _resize_mask(mask, shape):
        values = np.asarray(mask, dtype=bool)
        rows = np.linspace(0, values.shape[0] - 1, shape[0]).round().astype(int)
        columns = np.linspace(0, values.shape[1] - 1, shape[1]).round().astype(int)
        return values[np.ix_(rows, columns)]

    def closeEvent(self, event):
        """Remove this editor from the host tabs when it is closed."""
        parent = self.parentWidget()
        while parent is not None and not isinstance(parent, QTabWidget):
            parent = parent.parentWidget()
        if parent is not None:
            tab_index = parent.indexOf(self)
            if tab_index >= 0:
                parent.removeTab(tab_index)
        super().closeEvent(event)
