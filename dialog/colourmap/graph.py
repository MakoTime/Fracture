import math
from itertools import pairwise

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget

from tools.widgets.bezier_graph import (
    evaluate_prepared_bezier_array,
    prepare_bezier,
)


class ColourmapPreview(QWidget):
    """Paint the editable two-dimensional colour field."""

    def __init__(
        self,
        positions1=(),
        positions2=(),
        colour_grid=(),
        curve_points1=(),
        curve_handles1=(),
        curve_points2=(),
        curve_handles2=(),
        parent=None,
    ):
        super().__init__(parent)
        self._set_data(
            positions1,
            positions2,
            colour_grid,
            curve_points1,
            curve_handles1,
            curve_points2,
            curve_handles2,
        )
        self.setMinimumSize(280, 250)

    def set_data(
        self,
        positions1,
        positions2,
        colour_grid,
        curve_points1=(),
        curve_handles1=(),
        curve_points2=(),
        curve_handles2=(),
    ):
        self._set_data(
            positions1,
            positions2,
            colour_grid,
            curve_points1,
            curve_handles1,
            curve_points2,
            curve_handles2,
        )
        self.update()

    def _set_data(
        self,
        positions1,
        positions2,
        colour_grid,
        curve_points1,
        curve_handles1,
        curve_points2,
        curve_handles2,
    ):
        self.positions1 = tuple(positions1)
        self.positions2 = tuple(positions2)
        self.colour_grid = tuple(colour_grid)
        self.curve_points1 = tuple(curve_points1) or ((0.0, 0.0), (1.0, 1.0))
        self.curve_handles1 = tuple(curve_handles1) or (None, None)
        self.curve_points2 = tuple(curve_points2) or ((0.0, 0.0), (1.0, 1.0))
        self.curve_handles2 = tuple(curve_handles2) or (None, None)
        self.field1_name = "Field 1"
        self.field2_name = "Field 2"
        self.stops = (
            tuple(zip(self.positions1, self.colour_grid[0])) if self.colour_grid else ()
        )

    def set_field_names(self, field1_name, field2_name):
        self.field1_name = str(field1_name).strip() or "Field 1"
        self.field2_name = str(field2_name).strip() or "Field 2"
        self.update()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.palette().base())
        rect = QRectF(48, 16, max(1, self.width() - 68), max(1, self.height() - 58))
        painter.setPen(QPen(self.palette().mid(), 1))
        painter.drawRect(rect)

        if self.colour_grid:
            horizontal_curve = prepare_bezier(self.curve_points1, self.curve_handles1)
            vertical_curve = prepare_bezier(self.curve_points2, self.curve_handles2)
            columns = max(1, len(self.positions1) - 1)
            rows = max(1, len(self.positions2) - 1)
            image_width = max(1, round(rect.width()))
            image_height = max(1, round(rect.height()))
            image = np.empty((image_height, image_width, 4), dtype=np.uint8)
            for row in range(rows):
                for column in range(columns):
                    top_left = self.colour_grid[row][column]
                    top_right = self.colour_grid[row][column + 1]
                    bottom_left = self.colour_grid[row + 1][column]
                    bottom_right = self.colour_grid[row + 1][column + 1]
                    x_start = round(column * image_width / columns)
                    x_end = round((column + 1) * image_width / columns)
                    y_start = round(row * image_height / rows)
                    y_end = round((row + 1) * image_height / rows)
                    width = max(1, x_end - x_start)
                    height = max(1, y_end - y_start)
                    horizontal_grid, vertical_grid = np.meshgrid(
                        np.linspace(0.0, 1.0, width),
                        np.linspace(0.0, 1.0, height),
                    )
                    horizontal = evaluate_prepared_bezier_array(
                        horizontal_curve, horizontal_grid
                    )
                    vertical = evaluate_prepared_bezier_array(
                        vertical_curve, vertical_grid
                    )
                    cell_colours = np.empty((height, width, 4), dtype=float)
                    for channel in range(4):
                        top = (1 - horizontal) * top_left[
                            channel
                        ] + horizontal * top_right[channel]
                        bottom = (1 - horizontal) * bottom_left[
                            channel
                        ] + horizontal * bottom_right[channel]
                        cell_colours[:, :, channel] = (
                            1 - vertical
                        ) * top + vertical * bottom
                    image[y_start:y_end, x_start:x_end] = np.round(
                        np.clip(cell_colours, 0.0, 1.0) * 255
                    ).astype(np.uint8)
            rendered_image = QImage(
                image.data,
                image_width,
                image_height,
                image.strides[0],
                QImage.Format.Format_RGBA8888,
            ).copy()
            painter.drawImage(rect.topLeft(), rendered_image)
            painter.setPen(QPen(self.palette().mid(), 1))
            painter.drawRect(rect)
        painter.drawText(
            QRectF(rect.left() - 22, rect.bottom() + 7, 44, 18),
            Qt.AlignmentFlag.AlignHCenter,
            "0",
        )
        painter.drawText(
            QRectF(rect.right() - 22, rect.bottom() + 7, 44, 18),
            Qt.AlignmentFlag.AlignHCenter,
            "1",
        )
        painter.drawText(
            QRectF(rect.left(), rect.bottom() + 27, rect.width(), 18),
            Qt.AlignmentFlag.AlignHCenter,
            self.field1_name,
        )
        painter.save()
        painter.translate(15, rect.center().y())
        painter.rotate(-90)
        painter.drawText(
            QRectF(-rect.height() / 2, 0, rect.height(), 18),
            Qt.AlignmentFlag.AlignHCenter,
            self.field2_name,
        )
        painter.restore()
        painter.end()


class ColourmapAxisGraph(QWidget):
    """Edit the transition rate for one colourmap field at a time."""

    transitions_changed = Signal()

    def __init__(self, positions=(), exponents=(), axis_name="Field 1", parent=None):
        super().__init__(parent)
        self.positions = tuple(positions)
        self.exponents = list(exponents)
        self.axis_name = axis_name
        self._drag_index = None
        self.setMinimumSize(280, 250)

    def set_data(self, positions, exponents, axis_name):
        self.positions = tuple(positions)
        self.exponents = list(exponents)
        self.axis_name = axis_name
        self.update()

    def _plot_rect(self):
        return QRectF(48, 16, max(1, self.width() - 68), max(1, self.height() - 58))

    def _to_pixel(self, x, y):
        rect = self._plot_rect()
        return QPointF(
            rect.left() + x * rect.width(), rect.bottom() - y * rect.height()
        )

    def _segment_value(self, index, progress):
        exponent = self.exponents[index]
        return progress**exponent

    def _handle_position(self, index):
        start = self.positions[index]
        end = self.positions[index + 1]
        return self._to_pixel(
            (start + end) / 2,
            self._segment_value(index, 0.5),
        )

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.palette().base())
        rect = self._plot_rect()

        painter.setPen(QPen(self.palette().mid(), 1))
        painter.drawRect(rect)
        for index in range(1, 5):
            x = rect.left() + rect.width() * index / 5
            y = rect.top() + rect.height() * index / 5
            painter.setPen(QPen(self.palette().mid(), 1, Qt.PenStyle.DotLine))
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

        painter.setPen(QPen(self.palette().text(), 1))
        painter.drawText(
            QRectF(rect.left() - 25, rect.bottom() + 8, 50, 18),
            Qt.AlignmentFlag.AlignHCenter,
            "0",
        )
        painter.drawText(
            QRectF(rect.right() - 25, rect.bottom() + 8, 50, 18),
            Qt.AlignmentFlag.AlignHCenter,
            "1",
        )
        painter.drawText(
            QRectF(8, rect.bottom() - 9, 32, 18),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            "0",
        )
        painter.drawText(
            QRectF(8, rect.top() - 9, 32, 18),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            "1",
        )
        painter.drawText(
            QRectF(rect.left(), rect.bottom() + 27, rect.width(), 20),
            Qt.AlignmentFlag.AlignHCenter,
            self.axis_name,
        )
        painter.save()
        painter.translate(15, rect.center().y())
        painter.rotate(-90)
        painter.drawText(
            QRectF(-rect.height() / 2, 0, rect.height(), 20),
            Qt.AlignmentFlag.AlignHCenter,
            self.axis_name,
        )
        painter.restore()
        if len(self.positions) > 1 and len(self.exponents) == len(self.positions) - 1:
            painter.setPen(QPen(self.palette().highlight(), 2))
            for index in range(len(self.positions) - 1):
                points = []
                for sample in range(25):
                    progress = sample / 24
                    x = self.positions[index] + progress * (
                        self.positions[index + 1] - self.positions[index]
                    )
                    points.append(
                        self._to_pixel(x, self._segment_value(index, progress))
                    )
                for start, end in pairwise(points, points[1:]):
                    painter.drawLine(start, end)
                painter.setBrush(self.palette().highlight())
                handle = self._handle_position(index)
                painter.drawEllipse(handle, 5, 5)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        handles = [self._handle_position(index) for index in range(len(self.exponents))]
        distances = [
            abs(handle.x() - event.position().x())
            + abs(handle.y() - event.position().y())
            for handle in handles
        ]
        if distances and min(distances) <= 18:
            self._drag_index = distances.index(min(distances))
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_index is None:
            return
        rect = self._plot_rect()
        value = max(
            0.02, min(0.98, (rect.bottom() - event.position().y()) / rect.height())
        )
        self.exponents[self._drag_index] = max(
            0.1,
            min(8.0, math.log(value) / math.log(0.5)),
        )
        self.update()
        self.transitions_changed.emit()
        event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_index = None
        super().mouseReleaseEvent(event)
