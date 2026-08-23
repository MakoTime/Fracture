from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QTableWidget,
    QToolButton,
    QVBoxLayout,
)
from tools.widgets import NameField

from components.tree import TreeSearch
from engine.block_objects import PerlinNoiseTransformBlockObject
from objects.perlin_noise_transform import PerlinNoiseTransformObject

from .graph import ColourmapPreview
from .model import ColourmapModel
from tools.widgets import BezierCurveGraph
from common.icons import get_icon


class ColourmapView(QDialog):
    """Editor for colourmap stops and its optional noise transform."""

    def __init__(self, model=None, parent=None, tree_search=None, deduper=None):
        super().__init__(parent)
        self.model = model or ColourmapModel()
        self.tree_search = tree_search
        self.setWindowTitle("Colourmap")
        self.resize(1040, 620)

        self.name_field = NameField(self.model.name, deduper)
        self.field1_name_field = QLineEdit()
        self.field2_name_field = QLineEdit()
        self.comments_field = QLineEdit()
        self.noise_enabled_field = QCheckBox("Enable Perlin noise")
        self.transform_field = QComboBox()
        self.stops_table = QTableWidget(0, 2)
        self.stops_table.horizontalHeader().setVisible(False)
        self.stops_table.verticalHeader().setVisible(False)
        self.stops_table.horizontalHeader().setStretchLastSection(True)
        self.stops_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.stops_table.customContextMenuRequested.connect(self._show_grid_menu)
        self.stops_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.stops_table.setMinimumHeight(180)

        self.field_graph_selector = QComboBox()
        self.field_graph_selector.addItems((self.model.field1_name, self.model.field2_name))
        self.field_graph_selector.currentIndexChanged.connect(self._update_axis_graph)
        self.field1_name_field.textChanged.connect(self._update_field_labels)
        self.field2_name_field.textChanged.connect(self._update_field_labels)

        self._populate_transforms()
        self.set_model(self.model)

        preview_group = QGroupBox("Colourmap preview")
        preview_layout = QVBoxLayout(preview_group)
        self.colourmap_preview = ColourmapPreview(
            self.model.field1_positions,
            self.model.field2_positions,
            self.model.colour_grid,
            self.model.field1_curve_points,
            self.model.field1_curve_handles,
            self.model.field2_curve_points,
            self.model.field2_curve_handles,
        )
        self.colourmap_preview.set_field_names(
            self.model.field1_name,
            self.model.field2_name,
        )
        preview_layout.addWidget(self.colourmap_preview)

        axis_group = QGroupBox("Two-field colour space")
        axis_layout = QVBoxLayout(axis_group)
        self.axis_graph = BezierCurveGraph(
            curve_points=self.model.field1_curve_points,
            curve_mode="bezier",
            curve_handles=self.model.field1_curve_handles,
            frequency_min=0.0,
            frequency_max=1.0,
            amplitude_max=1.0,
        )
        self.axis_graph.values_changed.connect(self._transition_changed)
        axis_layout.addWidget(self.field_graph_selector)
        axis_layout.addWidget(self.axis_graph)

        visualisation = QVBoxLayout()
        visualisation.addWidget(preview_group)
        visualisation.addWidget(axis_group, 1)

        details = QFormLayout()
        details.addRow("Name", self.name_field)
        details.addRow("Field 1", self.field1_name_field)
        details.addRow("Field 2", self.field2_name_field)
        details.addRow("Comments", self.comments_field)
        details.addRow("Transform", self.transform_field)
        details.addRow("Noise", self.noise_enabled_field)
        details_group = QGroupBox("Colourmap settings")
        details_group.setLayout(details)

        stops_group = QGroupBox("Colour stops")
        stops_layout = QVBoxLayout(stops_group)
        self.x_field_label = QLabel()
        self.x_field_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.y_field_label = QLabel()
        self.y_field_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        table_row = QHBoxLayout()
        table_row.addWidget(self.y_field_label)
        table_row.addWidget(self.stops_table, 1)
        stops_layout.addWidget(self.x_field_label)
        stops_layout.addLayout(table_row, 1)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: palette(link);")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        self.button_box.accepted.connect(self._accept)
        self.button_box.rejected.connect(self.reject)

        left_panel = QVBoxLayout()
        left_panel.addWidget(details_group)
        left_panel.addWidget(stops_group, 1)
        left_panel.addWidget(self.error_label)

        editor = QHBoxLayout()
        editor.addLayout(left_panel, 1)
        editor.addLayout(visualisation, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(editor, 1)
        layout.addWidget(self.button_box)

    def _populate_transforms(self):
        self.transform_field.clear()
        self.transform_field.addItem("None", None)
        if self.tree_search is None:
            return
        transforms = self.tree_search.find(
            lambda node: isinstance(
                node.node_object,
                PerlinNoiseTransformObject,
            )
        )
        for transform in transforms:
            self.transform_field.addItem(transform.name, transform)

    def _update_field_labels(self):
        field1_name = self.field1_name_field.text().strip() or "Field 1"
        field2_name = self.field2_name_field.text().strip() or "Field 2"
        self.field_graph_selector.setItemText(0, field1_name)
        self.field_graph_selector.setItemText(1, field2_name)
        if not hasattr(self, "x_field_label"):
            return
        self.x_field_label.setText(field1_name)
        self.y_field_label.setText(field2_name)
        if hasattr(self, "colourmap_preview"):
            self.colourmap_preview.set_field_names(field1_name, field2_name)

    def _colour_button(self, colour):
        button = QToolButton()
        button.setFixedSize(54, 54)
        button.setIconSize(QSize(36, 36))
        button.setProperty("colour", tuple(colour))
        ColourmapView._set_colour_button_icon(button, colour)
        button.clicked.connect(lambda: self._choose_colour(button))
        return button

    @staticmethod
    def _set_colour_button_icon(button, colour):
        rgba = tuple(round(channel * 255) for channel in colour)
        pixmap = QPixmap(36, 36)
        pixmap.fill(QColor(*rgba))
        button.setIcon(QIcon(pixmap))
        button.setToolTip(
            "RGBA: " + ", ".join(f"{channel:.3f}" for channel in colour)
        )

    def _choose_colour(self, button):
        colour = QColorDialog.getColor(parent=button)
        if not colour.isValid():
            return
        rgba = (
            colour.redF(), colour.greenF(), colour.blueF(), colour.alphaF()
        )
        button.setProperty("colour", rgba)
        self._set_colour_button_icon(button, rgba)
        self._refresh_visuals()

    def _refresh_visuals(self):
        self._read_colour_grid()
        self.colourmap_preview.set_data(
            self.model.field1_positions,
            self.model.field2_positions,
            self.model.colour_grid,
        )
        self._update_axis_graph()
    def _populate_colour_grid(self):
        self.stops_table.setColumnCount(len(self.model.field1_positions))
        self.stops_table.setRowCount(0)
        for row in range(len(self.model.field2_positions)):
            self.stops_table.insertRow(row)
            self.stops_table.setRowHeight(row, 64)
            for column, colour in enumerate(self.model.colour_grid[row]):
                self.stops_table.setCellWidget(row, column, self._colour_button(colour))
        for column in range(self.stops_table.columnCount()):
            self.stops_table.setColumnWidth(column, 64)

    def _read_colour_grid(self):
        self.model.field1_positions = self._even_positions(self.stops_table.columnCount())
        self.model.field2_positions = self._even_positions(self.stops_table.rowCount())
        self.model.colour_grid = tuple(
            tuple(
                self.stops_table.cellWidget(row, column).property("colour")
                for column in range(self.stops_table.columnCount())
            )
            for row in range(self.stops_table.rowCount())
        )
        self.model.stops = tuple(
            (position, colour)
            for position, colour in zip(
                self.model.field1_positions,
                self.model.colour_grid[0],
            )
        )
        self.model.__post_init__()

    def _transition_changed(self):
        if self.field_graph_selector.currentIndex() == 0:
            self.model.field1_curve_points = self.axis_graph.serialized_curve_points()
            self.model.field1_curve_handles = self.axis_graph.serialized_curve_handles()
        else:
            self.model.field2_curve_points = self.axis_graph.serialized_curve_points()
            self.model.field2_curve_handles = self.axis_graph.serialized_curve_handles()
        self.model.__post_init__()
        self.colourmap_preview.set_data(
            self.model.field1_positions,
            self.model.field2_positions,
            self.model.colour_grid,
            self.model.field1_curve_points,
            self.model.field1_curve_handles,
            self.model.field2_curve_points,
            self.model.field2_curve_handles,
        )

    @staticmethod
    def _even_positions(count):
        if count < 2:
            raise ValueError("Colourmaps require at least two rows and columns")
        return tuple(index / (count - 1) for index in range(count))

    def _show_grid_menu(self, position):
        index = self.stops_table.indexAt(position)
        if not index.isValid():
            return
        row, column = index.row(), index.column()
        menu = QMenu(self.stops_table)
        actions = {
            menu.addAction("Insert row above"): lambda: self._insert_row(row),
            menu.addAction("Insert row below"): lambda: self._insert_row(row + 1),
            menu.addAction("Insert column left"): lambda: self._insert_column(column),
            menu.addAction("Insert column right"): lambda: self._insert_column(column + 1),
        }
        menu.addSeparator()
        remove_row = menu.addAction(get_icon("bin"), "Remove row")
        remove_column = menu.addAction(get_icon("bin"), "Remove column")
        remove_row.setEnabled(self.stops_table.rowCount() > 2)
        remove_column.setEnabled(self.stops_table.columnCount() > 2)
        actions[remove_row] = lambda: self._remove_row(row)
        actions[remove_column] = lambda: self._remove_column(column)
        selected = menu.exec(self.stops_table.viewport().mapToGlobal(position))
        if selected in actions:
            actions[selected]()

    def _insert_row(self, index):
        self._read_colour_grid()
        source = self.model.colour_grid[min(index, len(self.model.colour_grid) - 1)]
        self.model.colour_grid = tuple(
            (*self.model.colour_grid[:index], source, *self.model.colour_grid[index:])
        )
        self.model.field2_positions = self._even_positions(len(self.model.colour_grid))
        self._populate_colour_grid()
        self._refresh_visuals()

    def _remove_row(self, index):
        if len(self.model.field2_positions) <= 2:
            return
        self._read_colour_grid()
        self.model.colour_grid = tuple(row for row, value in enumerate(self.model.colour_grid) if row != index)
        self.model.field2_positions = self._even_positions(len(self.model.colour_grid))
        remove_index = max(0, index - 1)
        self._populate_colour_grid()
        self._refresh_visuals()

    def _insert_column(self, index):
        self._read_colour_grid()
        self.model.colour_grid = tuple(
            tuple((*row[:index], row[min(index, len(row) - 1)], *row[index:]))
            for row in self.model.colour_grid
        )
        self.model.field1_positions = self._even_positions(len(self.model.colour_grid[0]))
        self._populate_colour_grid()
        self._refresh_visuals()

    def _remove_column(self, index):
        if len(self.model.field1_positions) <= 2:
            return
        self._read_colour_grid()
        self.model.colour_grid = tuple(
            tuple(value for column, value in enumerate(row) if column != index)
            for row in self.model.colour_grid
        )
        self.model.field1_positions = self._even_positions(len(self.model.colour_grid[0]))
        remove_index = max(0, index - 1)
        self._populate_colour_grid()
        self._refresh_visuals()

    def _update_axis_graph(self):
        if not hasattr(self, "axis_graph"):
            return
        self._read_colour_grid()
        if self.field_graph_selector.currentIndex() == 0:
            positions = self.model.field1_positions
            points = self.model.field1_curve_points
            handles = self.model.field1_curve_handles
        else:
            positions = self.model.field2_positions
            points = self.model.field2_curve_points
            handles = self.model.field2_curve_handles
        self.axis_graph.set_data(
            positions,
            (),
            points,
            "bezier",
            handles,
            frequency_min=0.0,
            frequency_max=1.0,
            amplitude_max=1.0,
        )

    def _select_transform(self, transform):
        if transform is None:
            self.transform_field.setCurrentIndex(0)
            return
        guid = getattr(getattr(transform, "block_object", transform), "guid", None)
        for index in range(self.transform_field.count()):
            candidate = self.transform_field.itemData(index)
            candidate_guid = getattr(
                getattr(candidate, "block_object", candidate),
                "guid",
                None,
            )
            if candidate is transform or candidate_guid == guid:
                self.transform_field.setCurrentIndex(index)
                return
        self.transform_field.setCurrentIndex(0)

    def set_model(self, model):
        self.model = model
        self.name_field.setText(model.name)
        self.field1_name_field.setText(model.field1_name)
        self.field2_name_field.setText(model.field2_name)
        self._update_field_labels()
        self.comments_field.setText(model.comments)
        self.noise_enabled_field.setChecked(model.noise_enabled)
        while self.stops_table.rowCount():
            self.stops_table.removeRow(0)
        self._populate_colour_grid()
        self._select_transform(model.perlin_noise_transform)
        if hasattr(self, "colourmap_preview"):
            self.colourmap_preview.set_data(
                model.field1_positions,
                model.field2_positions,
                model.colour_grid,
                model.field1_curve_points,
                model.field1_curve_handles,
                model.field2_curve_points,
                model.field2_curve_handles,
            )
            self._update_axis_graph()

    def update_model(self):
        self.model.name = self.name_field.unique_name() or "Colourmap"
        self.model.field1_name = self.field1_name_field.text().strip() or "Field 1"
        self.model.field2_name = self.field2_name_field.text().strip() or "Field 2"
        self.model.comments = self.comments_field.text()
        self._read_colour_grid()
        self.model.noise_enabled = self.noise_enabled_field.isChecked()
        self.model.perlin_noise_transform = self.transform_field.currentData()
        self.model.__post_init__()
        self.colourmap_preview.set_data(
            self.model.field1_positions,
            self.model.field2_positions,
            self.model.colour_grid,
            self.model.field1_curve_points,
            self.model.field1_curve_handles,
            self.model.field2_curve_points,
            self.model.field2_curve_handles,
        )
        self._update_axis_graph()
        return self.model

    def _accept(self):
        try:
            self.update_model()
        except (TypeError, ValueError) as error:
            self.error_label.setText(str(error))
            self.error_label.setVisible(True)
            return
        self.accept()
