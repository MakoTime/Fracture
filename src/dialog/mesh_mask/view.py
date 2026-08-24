from collections import deque

import numpy as np
from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .model import SurfaceMaskModel


class MaskCanvas(QWidget):
    """Paintable 2D mask canvas with add, remove, and bucket-fill tools."""

    def __init__(self, model: SurfaceMaskModel, parent=None):
        super().__init__(parent)
        self.model = model
        self.values = model.view_values()
        self.tool = "add"
        self._painting = False
        self._last_cell = None
        self.setMinimumSize(320, 320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

    def set_model(self, model):
        self.model = model
        self.values = model.view_values()
        self.update()

    def set_tool(self, tool):
        self.tool = tool

    def commit(self):
        if np.all(self.values):
            self.model.mask = None
        else:
            self.model.set_view_values(self.values)

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#202938"))
        rows, columns = self.values.shape
        cell_size, left, top = self._grid_geometry()
        for row in range(rows):
            for column in range(columns):
                rect = self._cell_rect(row, column, cell_size, left, top)
                color = (
                    QColor("#8ecae6") if self.values[row, column] else QColor("#283548")
                )
                painter.fillRect(rect, color)
                painter.setPen(QPen(QColor("#536579"), 1))
                painter.drawRect(rect)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        cell = self._cell_at(event.position().toPoint())
        if cell is None:
            return
        if self.tool == "bucket":
            self._bucket_fill(*cell)
        else:
            self._paint_cell(*cell)
            self._painting = True
            self._last_cell = cell
        self.update()

    def mouseMoveEvent(self, event):
        if not self._painting or self.tool == "bucket":
            return
        cell = self._cell_at(event.position().toPoint())
        if cell is not None:
            start = self._last_cell or cell
            for row, column in self._line_cells(start, cell):
                self._paint_cell(row, column)
            self._last_cell = cell
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._painting = False
            self._last_cell = None

    def _paint_cell(self, row, column):
        self.values[row, column] = self.tool == "add"

    @staticmethod
    def _line_cells(start, end):
        start_row, start_column = start
        end_row, end_column = end
        steps = max(abs(end_row - start_row), abs(end_column - start_column))
        if steps == 0:
            return (start,)
        return tuple(
            (
                round(start_row + (end_row - start_row) * step / steps),
                round(start_column + (end_column - start_column) * step / steps),
            )
            for step in range(steps + 1)
        )

    def _bucket_fill(self, row, column):
        target = bool(self.values[row, column])
        replacement = not target
        if target == replacement:
            return
        rows, columns = self.values.shape
        pending = deque([(row, column)])
        visited = set()
        while pending:
            current_row, current_column = pending.popleft()
            if (current_row, current_column) in visited:
                continue
            if not (0 <= current_row < rows and 0 <= current_column < columns):
                continue
            if bool(self.values[current_row, current_column]) != target:
                continue
            visited.add((current_row, current_column))
            self.values[current_row, current_column] = replacement
            pending.extend(
                (
                    (current_row - 1, current_column),
                    (current_row + 1, current_column),
                    (current_row, current_column - 1),
                    (current_row, current_column + 1),
                )
            )

    def _cell_at(self, position: QPoint):
        rows, columns = self.values.shape
        cell_size, left, top = self._grid_geometry()
        column = int((position.x() - left) / cell_size)
        row = int((position.y() - top) / cell_size)
        if 0 <= row < rows and 0 <= column < columns:
            return row, column
        return None

    def _grid_geometry(self):
        rows, columns = self.values.shape
        cell_size = min(self.width() / columns, self.height() / rows)
        grid_width = cell_size * columns
        grid_height = cell_size * rows
        left = (self.width() - grid_width) / 2
        top = (self.height() - grid_height) / 2
        return cell_size, left, top

    @staticmethod
    def _cell_rect(row, column, cell_size, left, top):
        return QRectF(
            left + column * cell_size,
            top + row * cell_size,
            cell_size,
            cell_size,
        )


class SurfaceMaskView(QDialog):
    """Image-editor-style dialog for editing one generated mesh surface mask."""

    def __init__(self, model: SurfaceMaskModel, parent=None):
        super().__init__(parent)
        self.model = model
        self.setWindowTitle(f"Edit {model.axis} Surface Mask")
        self.resize(620, 620)
        self._build_ui()
        self.set_model(model)

    def _build_ui(self):
        self.canvas = MaskCanvas(self.model)

        tools = QHBoxLayout()
        self.tool_buttons = {}
        for name, label in (
            ("add", "Add"),
            ("remove", "Remove"),
            ("bucket", "Bucket Fill"),
        ):
            button = QToolButton()
            button.setText(label)
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked=False, name=name: self._select_tool(name)
            )
            self.tool_buttons[name] = button
            tools.addWidget(button)
        tools.addStretch(1)

        fill_button = QPushButton("Fill")
        clear_button = QPushButton("Clear")
        fill_button.clicked.connect(lambda: self._set_all(True))
        clear_button.clicked.connect(lambda: self._set_all(False))
        tools.addWidget(fill_button)
        tools.addWidget(clear_button)
        self._select_tool("add")

        horizontal_axis, vertical_axis = self.model.view_axes
        axis_labels = QHBoxLayout()
        axis_labels.addWidget(QLabel(f"{horizontal_axis} ->"))
        axis_labels.addStretch(1)
        axis_labels.addWidget(QLabel(f"^ {vertical_axis}"))

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        self.button_box.accepted.connect(self._accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(tools)
        layout.addLayout(axis_labels)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.button_box)

    def set_model(self, model: SurfaceMaskModel):
        self.model = model
        if hasattr(self, "canvas"):
            self.canvas.set_model(model)

    def update_model(self):
        self.canvas.commit()
        return self.model

    def _select_tool(self, tool):
        self.canvas.set_tool(tool)
        for name, button in self.tool_buttons.items():
            button.setChecked(name == tool)

    def _set_all(self, enabled):
        self.canvas.values.fill(enabled)
        self.canvas.update()

    def _accept(self):
        self.update_model()
        self.accept()
