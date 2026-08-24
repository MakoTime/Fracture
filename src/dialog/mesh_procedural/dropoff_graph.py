from itertools import pairwise

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget


class DropoffGraph(QWidget):
    """Interactive editor for a normalized dropoff curve."""

    values_changed = Signal()
    mouse_position_changed = Signal(float, float)

    def __init__(
        self,
        curve_points=(),
        curve_handles=(),
        parent=None,
        sample_count=64,
    ):
        super().__init__(parent)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.setMouseTracking(True)

        self.curve_points = self._normalized_curve_points(curve_points)
        self.curve_handles = self._normalize_handles(curve_handles)
        self.sample_count = max(2, int(sample_count))

        self._drag_index = None
        self._handle_drag_index = None
        self._handle_drag_side = None
        self._handle_drag_origin_x = None

    def set_data(self, curve_points=(), curve_handles=()):
        self.curve_points = self._normalized_curve_points(curve_points)
        self.curve_handles = self._normalize_handles(curve_handles)
        self.update()

    def set_sample_count(self, count):
        self.sample_count = max(2, int(count))
        self.update()

    def sizeHint(self):
        return QSize(200, 150)

    @staticmethod
    def _normalized_curve_points(points):
        normalized = [
            point
            if isinstance(point, QPointF)
            else QPointF(float(point[0]), float(point[1]))
            for point in points
        ]

        normalized.sort(key=lambda point: point.x())

        if not normalized:
            return normalized

        if len(normalized) == 1:
            point = normalized[0]
            return [
                QPointF(0.0, point.y()),
                QPointF(1.0, point.y()),
            ]

        normalized[0] = QPointF(
            0.0,
            max(0.0, min(1.0, normalized[0].y())),
        )

        normalized[-1] = QPointF(
            1.0,
            max(0.0, min(1.0, normalized[-1].y())),
        )

        return [
            QPointF(
                max(0.0, min(1.0, point.x())),
                max(0.0, min(1.0, point.y())),
            )
            for point in normalized
        ]

    @staticmethod
    def _normalize_handles(handles):
        def normalize_point(point):
            if isinstance(point, QPointF):
                return QPointF(point)

            return QPointF(
                float(point[0]),
                float(point[1]),
            )

        normalized = []

        for handle in handles:
            if handle is None:
                normalized.append(None)
                continue

            if len(handle) != 2:
                continue

            normalized.append(
                (
                    normalize_point(handle[0]),
                    normalize_point(handle[1]),
                )
            )

        return normalized

    def _plot_rect(self):
        return QRectF(
            38,
            12,
            max(1, self.width() - 52),
            max(1, self.height() - 38),
        )

    def _to_pixel(self, x, y):
        rect = self._plot_rect()

        return QPointF(
            rect.left() + x * rect.width(),
            rect.bottom() - y * rect.height(),
        )

    def _from_pixel(self, point):
        rect = self._plot_rect()

        x = (point.x() - rect.left()) / rect.width()
        y = (rect.bottom() - point.y()) / rect.height()

        return (
            max(0.0, min(1.0, x)),
            max(0.0, min(1.0, y)),
        )

    def paintEvent(self, event):
        del event

        points = self._normalized_curve_points(self.curve_points)

        with QPainter(self) as painter:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            painter.fillRect(
                self.rect(),
                self.palette().base(),
            )

            rect = self._plot_rect()

            painter.setPen(QPen(self.palette().mid(), 1))
            painter.drawRect(rect)

            # Axes.
            painter.drawText(
                QRectF(
                    rect.left() - 30,
                    rect.bottom() - 8,
                    25,
                    18,
                ),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                "0",
            )

            painter.drawText(
                QRectF(
                    rect.left() - 30,
                    rect.top() - 8,
                    25,
                    18,
                ),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                "1",
            )

            painter.drawText(
                QRectF(
                    rect.left() - 5,
                    rect.bottom() + 5,
                    30,
                    18,
                ),
                Qt.AlignmentFlag.AlignLeft,
                "0",
            )

            painter.drawText(
                QRectF(
                    rect.right() - 25,
                    rect.bottom() + 5,
                    30,
                    18,
                ),
                Qt.AlignmentFlag.AlignRight,
                "1",
            )

            if not points:
                return

            # Curve.
            path = QPainterPath(
                self._to_pixel(
                    points[0].x(),
                    points[0].y(),
                )
            )

            for index in range(1, self.sample_count):
                point = self._bezier_point(index / (self.sample_count - 1))

                path.lineTo(
                    self._to_pixel(
                        point.x(),
                        point.y(),
                    )
                )

            painter.setPen(
                QPen(
                    self.palette().highlight(),
                    2,
                )
            )
            painter.drawPath(path)

            # Handles.
            painter.setPen(
                QPen(
                    self.palette().mid(),
                    1,
                )
            )

            handles = self._effective_handles()

            for index, (left, right) in enumerate(handles):
                anchor = points[index]

                painter.drawLine(
                    self._to_pixel(
                        anchor.x(),
                        anchor.y(),
                    ),
                    self._to_pixel(
                        left.x(),
                        left.y(),
                    ),
                )

                painter.drawLine(
                    self._to_pixel(
                        anchor.x(),
                        anchor.y(),
                    ),
                    self._to_pixel(
                        right.x(),
                        right.y(),
                    ),
                )

            # Handle points.
            painter.setBrush(self.palette().mid())

            for left, right in handles:
                painter.drawEllipse(
                    self._to_pixel(left.x(), left.y()),
                    3,
                    3,
                )
                painter.drawEllipse(
                    self._to_pixel(right.x(), right.y()),
                    3,
                    3,
                )

            # Anchors.
            painter.setBrush(self.palette().highlight())

            for point in points:
                painter.drawEllipse(
                    self._to_pixel(
                        point.x(),
                        point.y(),
                    ),
                    5,
                    5,
                )

    def mousePressEvent(self, event):
        self._emit_mouse_position(event.position())

        if event.button() == Qt.MouseButton.RightButton:
            self._handle_drag_origin_x = self._from_pixel(event.position())[0]

            self._handle_drag_index = self._nearest_anchor_index(event.position())

            self._handle_drag_side = None

            if self._handle_drag_index is None:
                (
                    self._handle_drag_index,
                    self._handle_drag_side,
                ) = self._nearest_handle(event.position())

            if self._handle_drag_index is not None:
                if self._handle_drag_side is not None:
                    self._update_handle_drag(event.position())

                event.accept()

            return

        if event.button() != Qt.MouseButton.LeftButton:
            return

        if not self.curve_points:
            return

        index = self._nearest_anchor_index(event.position())

        if index is not None:
            self._drag_index = index
            self._update_drag(event.position())

    def mouseDoubleClickEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseDoubleClickEvent(event)
            return

        self._drag_index = None

        anchor_index = self._nearest_anchor_index(event.position())

        if anchor_index is not None:
            if anchor_index in (
                0,
                len(self.curve_points) - 1,
            ):
                event.accept()
                return

            self.remove_curve_point(event)

        else:
            self.add_curve_point(event)

        event.accept()

    def mouseMoveEvent(self, event):
        self._emit_mouse_position(event.position())

        if self._handle_drag_index is not None:
            self._update_handle_drag(event.position())

        elif self._drag_index is not None:
            self._update_drag(event.position())

    def mouseReleaseEvent(self, event):
        del event

        was_dragging = (
            self._drag_index is not None or self._handle_drag_index is not None
        )

        self._drag_index = None
        self._handle_drag_index = None
        self._handle_drag_side = None
        self._handle_drag_origin_x = None

        if was_dragging:
            self.values_changed.emit()

    def add_curve_point(self, point):
        """Insert a Bezier anchor at a normalized position."""

        if hasattr(point, "position"):
            x, y = self._from_pixel(point.position())

        elif isinstance(point, QPointF):
            x, y = point.x(), point.y()

        else:
            x, y = (
                float(point[0]),
                float(point[1]),
            )

        points = self._normalized_curve_points(self.curve_points)

        if x <= 0.0 or x >= 1.0:
            return False

        insertion_index = next(
            (index for index, current in enumerate(points) if x < current.x()),
            len(points),
        )

        points.insert(
            insertion_index,
            QPointF(x, y),
        )

        handles = list(self._normalize_handles(self.curve_handles))

        while len(handles) < len(points) - 1:
            handles.append(None)

        handles.insert(
            insertion_index,
            None,
        )

        self.curve_points = points
        self.curve_handles = handles

        self.update()
        self.values_changed.emit()

        return True

    def remove_curve_point(self, point):
        """Remove an interior Bezier anchor."""

        if hasattr(point, "position"):
            index = self._nearest_anchor_index(point.position())

        elif isinstance(point, QPointF):
            points = self._normalized_curve_points(self.curve_points)

            index = (
                min(
                    range(len(points)),
                    key=lambda candidate: (
                        abs(points[candidate].x() - point.x())
                        + abs(points[candidate].y() - point.y())
                    ),
                )
                if points
                else None
            )

        else:
            return self.remove_curve_point(
                QPointF(
                    float(point[0]),
                    float(point[1]),
                )
            )

        if index is None:
            return False

        if index in (
            0,
            len(self.curve_points) - 1,
        ):
            return False

        self.curve_points = self._normalized_curve_points(self.curve_points)

        self.curve_points.pop(index)

        if index < len(self.curve_handles):
            self.curve_handles.pop(index)

        self.update()
        self.values_changed.emit()

        return True

    def _nearest_anchor_index(self, position):
        points = self._normalized_curve_points(self.curve_points)
        if not points:
            return None
        distances = [
            abs(
                self._to_pixel(
                    point.x(),
                    point.y(),
                ).x()
                - position.x()
            )
            + abs(
                self._to_pixel(
                    point.x(),
                    point.y(),
                ).y()
                - position.y()
            )
            for point in points
        ]

        index = min(
            range(len(distances)),
            key=distances.__getitem__,
        )

        return index if distances[index] <= 20 else None

    def _nearest_handle(self, position):
        candidates = [
            (
                abs(
                    self._to_pixel(
                        handle.x(),
                        handle.y(),
                    ).x()
                    - position.x()
                )
                + abs(
                    self._to_pixel(
                        handle.x(),
                        handle.y(),
                    ).y()
                    - position.y()
                ),
                index,
                side,
            )
            for index, pair in enumerate(self._effective_handles())
            for side, handle in enumerate(pair)
        ]

        if not candidates:
            return None, None

        distance, index, side = min(candidates)

        if distance > 18:
            return None, None

        return index, side

    def _effective_handles(self):
        points = self._normalized_curve_points(self.curve_points)

        handles = self._normalize_handles(self.curve_handles)

        while len(handles) < len(points):
            handles.append(None)

        effective = []

        for index, point in enumerate(points):
            handle = handles[index]

            if handle is not None:
                effective.append(handle)
                continue

            if index == 0:
                right = points[1] if len(points) > 1 else point

                vector = QPointF(
                    (right.x() - point.x()) / 3.0,
                    (right.y() - point.y()) / 3.0,
                )

            elif index == len(points) - 1:
                left = points[index - 1]

                vector = QPointF(
                    (point.x() - left.x()) / 3.0,
                    (point.y() - left.y()) / 3.0,
                )

            else:
                left = points[index - 1]
                right = points[index + 1]

                delta_x = max(
                    0.0001,
                    right.x() - left.x(),
                )

                slope = (right.y() - left.y()) / delta_x

                vector = QPointF(
                    (point.x() - left.x()) / 3.0,
                    slope * (point.x() - left.x()) / 3.0,
                )

            effective.append(
                (
                    QPointF(
                        point.x() - vector.x(),
                        point.y() - vector.y(),
                    ),
                    QPointF(
                        point.x() + vector.x(),
                        point.y() + vector.y(),
                    ),
                )
            )

        return effective

    def _update_handle_drag(self, position):
        if self._handle_drag_index is None:
            return

        points = self._normalized_curve_points(self.curve_points)

        index = self._handle_drag_index
        anchor = points[index]

        x, y = self._from_pixel(position)

        if self._handle_drag_side is None:
            origin_x = (
                anchor.x()
                if self._handle_drag_origin_x is None
                else self._handle_drag_origin_x
            )

            delta = x - origin_x

            if abs(delta) <= 0.0001:
                return

            self._handle_drag_side = 1 if delta > 0.0 else 0

        vector_x = max(
            -0.45,
            min(0.45, x - anchor.x()),
        )

        vector_y = max(
            -0.45,
            min(0.45, y - anchor.y()),
        )

        self.curve_handles = list(self._effective_handles())

        moved = QPointF(
            anchor.x() + vector_x,
            max(
                0.0,
                min(
                    1.0,
                    anchor.y() + vector_y,
                ),
            ),
        )

        opposite = QPointF(
            anchor.x() - vector_x,
            max(
                0.0,
                min(
                    1.0,
                    anchor.y() - vector_y,
                ),
            ),
        )

        self.curve_handles[index] = (
            (moved, opposite) if self._handle_drag_side == 0 else (opposite, moved)
        )

        self.update()

    def _update_drag(self, position):
        if self._drag_index is None:
            return

        points = self._normalized_curve_points(self.curve_points)

        x, y = self._from_pixel(position)

        index = self._drag_index
        old = points[index]

        is_endpoint = index in (
            0,
            len(points) - 1,
        )

        previous_handles = self._effective_handles()

        if not is_endpoint:
            previous = points[index - 1]
            following = points[index + 1]

            x = max(
                previous.x() + 0.001,
                min(
                    following.x() - 0.001,
                    x,
                ),
            )

        delta_x = (old.x() if is_endpoint else x) - old.x()

        delta_y = y - old.y()

        points[index] = QPointF(
            old.x() if is_endpoint else x,
            y,
        )

        self.curve_points = points

        self.curve_handles = [
            (
                (
                    QPointF(
                        handle.x() + delta_x,
                        max(
                            0.0,
                            min(
                                1.0,
                                handle.y() + delta_y,
                            ),
                        ),
                    ),
                    QPointF(
                        other.x() + delta_x,
                        max(
                            0.0,
                            min(
                                1.0,
                                other.y() + delta_y,
                            ),
                        ),
                    ),
                )
                if handle_index == index
                else (handle, other)
            )
            for handle_index, (handle, other) in enumerate(previous_handles)
        ]

        self._drag_index = min(
            range(len(points)),
            key=lambda candidate: (
                abs(points[candidate].x() - (old.x() if is_endpoint else x))
                + abs(points[candidate].y() - y)
            ),
        )

        self.update()

    def _bezier_point(self, progress):
        """Evaluate the connected cubic Bezier curve."""

        points = self._normalized_curve_points(self.curve_points)

        if not points:
            return QPointF()

        if len(points) == 1:
            return points[0]

        if progress <= points[0].x():
            return points[0]

        if progress >= points[-1].x():
            return points[-1]

        segment_index = next(
            index
            for index, (start, end) in enumerate(pairwise(points))
            if progress <= end.x()
        )

        start = points[segment_index]
        end = points[segment_index + 1]

        delta_x = max(
            0.0001,
            end.x() - start.x(),
        )

        local = (progress - start.x()) / delta_x

        handles = self._effective_handles()

        control_start = handles[segment_index][1]

        control_end = handles[segment_index + 1][0]

        # Keep the controls within their segment.
        control_start = QPointF(
            max(
                start.x(),
                min(
                    end.x(),
                    control_start.x(),
                ),
            ),
            max(
                min(start.y(), end.y()),
                min(
                    max(start.y(), end.y()),
                    control_start.y(),
                ),
            ),
        )

        control_end = QPointF(
            max(
                start.x(),
                min(
                    end.x(),
                    control_end.x(),
                ),
            ),
            max(
                min(start.y(), end.y()),
                min(
                    max(start.y(), end.y()),
                    control_end.y(),
                ),
            ),
        )

        inverse = 1.0 - local

        return QPointF(
            inverse**3 * start.x()
            + 3 * inverse**2 * local * control_start.x()
            + 3 * inverse * local**2 * control_end.x()
            + local**3 * end.x(),
            inverse**3 * start.y()
            + 3 * inverse**2 * local * control_start.y()
            + 3 * inverse * local**2 * control_end.y()
            + local**3 * end.y(),
        )

    def sampled_values(self, count):
        """Return Y values sampled uniformly across the curve."""

        return tuple(
            self._bezier_point(index / max(1, count - 1)).y() for index in range(count)
        )

    def _emit_mouse_position(self, position):
        x, y = self._from_pixel(position)
        self.mouse_position_changed.emit(x, y)

    def serialized_curve_points(self):
        return tuple(
            (point.x(), point.y())
            for point in self._normalized_curve_points(self.curve_points)
        )

    def serialized_curve_handles(self):
        return tuple(
            tuple((point.x(), point.y()) for point in handles)
            if handles is not None
            else None
            for handles in self.curve_handles
        )
