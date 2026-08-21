import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class FrequencyAmplitudeGraph(QWidget):
    """Interactive frequency/amplitude editor for discrete bars or curves."""

    values_changed = Signal()
    mouse_position_changed = Signal(float, float)

    def __init__(self, frequencies=(), amplitudes=(), curve_points=(), curve_mode="discrete", parent=None, curve_handles=(), frequency_min=None, frequency_max=None, amplitude_max=1.0, sample_count=64):
        super().__init__(parent)
        self.setMinimumSize(360, 230)
        self.setMouseTracking(True)
        self.frequencies = tuple(frequencies)
        self.amplitudes = [float(value) for value in amplitudes]
        self.curve_points = [QPointF(float(x), float(y)) for x, y in curve_points]
        self.curve_handles = self._normalize_handles(curve_handles)
        self.curve_mode = curve_mode
        self.frequency_min = frequency_min if frequency_min is not None else (self.frequencies[0] if self.frequencies else 0)
        self.frequency_max = frequency_max if frequency_max is not None else (self.frequencies[-1] if self.frequencies else 1)
        self.amplitude_max = float(amplitude_max)
        self.sample_count = max(2, int(sample_count))
        self._drag_index = None
        self._handle_drag_index = None
        self._handle_drag_side = None
        self._handle_drag_origin_x = None

    def set_data(self, frequencies, amplitudes, curve_points=(), curve_mode="discrete", curve_handles=(), frequency_min=None, frequency_max=None, amplitude_max=None):
        self.frequencies = tuple(frequencies)
        self.amplitudes = [float(value) for value in amplitudes]
        self.curve_points = [QPointF(float(x), float(y)) for x, y in curve_points]
        self.curve_handles = self._normalize_handles(curve_handles)
        self.curve_mode = curve_mode
        if frequency_min is not None:
            self.frequency_min = frequency_min
        if frequency_max is not None:
            self.frequency_max = frequency_max
        if amplitude_max is not None:
            self.amplitude_max = float(amplitude_max)
        self.update()

    def set_axis_labels(self, frequency_min, frequency_max, amplitude_max):
        self.frequency_min = frequency_min
        self.frequency_max = frequency_max
        self.amplitude_max = float(amplitude_max)
        self.update()

    def set_sample_count(self, count):
        self.sample_count = max(2, int(count))
        self.update()

    def set_curve_mode(self, mode):
        self.curve_points = self._normalized_curve_points(self.curve_points)
        self.curve_mode = mode
        self.update()

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
            return [QPointF(0.0, point.y()), QPointF(1.0, point.y())]
        normalized[0] = QPointF(0.0, normalized[0].y())
        normalized[-1] = QPointF(1.0, normalized[-1].y())
        return normalized

    @staticmethod
    def _normalize_handles(handles):
        normalized = []
        for handle in handles:
            if handle is None:
                normalized.append(None)
                continue
            if len(handle) != 2:
                continue
            normalized.append(
                (
                    QPointF(float(handle[0][0]), float(handle[0][1])),
                    QPointF(float(handle[1][0]), float(handle[1][1])),
                )
            )
        return normalized

    def add_curve_point(self, point):
        """Insert a Bezier control point at a normalized graph position."""
        if self.curve_mode not in ("bezier", "line"):
            return False
        if hasattr(point, "position"):
            x, y = self._from_pixel(point.position())
        elif isinstance(point, QPointF):
            x, y = point.x(), point.y()
        else:
            x, y = float(point[0]), float(point[1])
        points = self._normalized_curve_points(self.curve_points)
        if x <= 0.0 or x >= 1.0:
            return False
        insertion_index = next(
            (index for index, current in enumerate(points) if x < current.x()),
            len(points),
        )
        points.insert(insertion_index, QPointF(x, y))
        self.curve_handles.insert(insertion_index, None)
        self.curve_points = points
        self.update()
        self.values_changed.emit()
        return True

    def remove_curve_point(self, point):
        """Remove an interior Bezier anchor at a pixel or normalized position."""
        if self.curve_mode != "bezier":
            return False
        if hasattr(point, "position"):
            position = point.position()
            index = self._nearest_anchor_index(position)
        elif isinstance(point, QPointF):
            points = self._normalized_curve_points(self.curve_points)
            index = min(
                range(len(points)),
                key=lambda candidate: abs(points[candidate].x() - point.x())
                + abs(points[candidate].y() - point.y()),
            ) if points else None
        else:
            position = QPointF(float(point[0]), float(point[1]))
            return self.remove_curve_point(position)
        if index is None or index in (0, len(self.curve_points) - 1):
            return False
        self.curve_points = self._normalized_curve_points(self.curve_points)
        self.curve_points.pop(index)
        if index < len(self.curve_handles):
            self.curve_handles.pop(index)
        self.update()
        self.values_changed.emit()
        return True

    def set_amplitudes(self, amplitudes):
        self.amplitudes = [max(0.0, min(1.0, float(value))) for value in amplitudes]
        self.update()
        self.values_changed.emit()

    def _plot_rect(self):
        return QRectF(38, 12, max(1, self.width() - 52), max(1, self.height() - 38))

    def _to_pixel(self, x, y):
        rect = self._plot_rect()
        return QPointF(rect.left() + x * rect.width(), rect.bottom() - y * rect.height())

    def _from_pixel(self, point):
        rect = self._plot_rect()
        x = (point.x() - rect.left()) / rect.width()
        y = (rect.bottom() - point.y()) / rect.height()
        return max(0.0, min(1.0, x)), max(0.0, min(1.0, y))

    def _bar_index(self, position):
        if not self.amplitudes:
            return None
        x, _ = self._from_pixel(position)
        return max(0, min(len(self.amplitudes) - 1, int(x * len(self.amplitudes))))

    @staticmethod
    def _axis_ticks(minimum, maximum, max_ticks=10):
        """Return at most max_ticks rounded ticks including both endpoints."""
        if maximum <= minimum:
            return (minimum,)
        span = maximum - minimum
        raw_step = span / max(1, max_ticks - 1)
        magnitude = 10 ** math.floor(math.log10(raw_step))
        normalized = raw_step / magnitude
        multiplier = 1 if normalized <= 1 else 2 if normalized <= 2 else 5 if normalized <= 5 else 10
        step = multiplier * magnitude
        ticks = [minimum]
        value = minimum + step
        while value < maximum and len(ticks) < max_ticks - 1:
            ticks.append(value)
            value += step
        ticks.append(maximum)
        midpoint = (minimum + maximum) / 2.0
        if abs(midpoint - round(midpoint)) < 1e-9 and not any(
            abs(tick - midpoint) < 1e-9 for tick in ticks
        ):
            ticks.append(midpoint)
            ticks.sort()
        while len(ticks) > max_ticks:
            removable = [
                index
                for index, tick in enumerate(ticks)
                if index not in (0, len(ticks) - 1)
                and abs(tick - midpoint) >= 1e-9
            ]
            if not removable:
                break
            ticks.pop(removable[-1])
        return tuple(ticks)

    @staticmethod
    def _format_tick(value):
        if abs(value - round(value)) < 1e-9:
            return str(int(round(value)))
        return f"{value:.3f}".rstrip("0").rstrip(".")

    def paintEvent(self, event):
        del event
        self.curve_points = self._normalized_curve_points(self.curve_points)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.palette().base())
        rect = self._plot_rect()
        painter.setPen(QPen(self.palette().mid(), 1))
        painter.drawRect(rect)
        painter.setPen(QPen(self.palette().mid(), 1))
        for value in self._axis_ticks(self.frequency_min, self.frequency_max):
            progress = (value - self.frequency_min) / max(0.0001, self.frequency_max - self.frequency_min)
            x = rect.left() + progress * rect.width()
            painter.drawLine(QPointF(x, rect.bottom()), QPointF(x, rect.bottom() + 4))
            painter.drawText(QRectF(x - 30, rect.bottom() + 5, 60, 18), Qt.AlignmentFlag.AlignHCenter, self._format_tick(value))
        for value in self._axis_ticks(0.0, self.amplitude_max):
            progress = value / max(0.0001, self.amplitude_max)
            y = rect.bottom() - progress * rect.height()
            painter.drawLine(QPointF(rect.left() - 4, y), QPointF(rect.left(), y))
            painter.drawText(QRectF(0, y - 9, rect.left() - 7, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._format_tick(value))

        if self.curve_mode == "bezier" and self.curve_points:
            path = QPainterPath(self._to_pixel(self.curve_points[0].x(), self.curve_points[0].y()))
            for index in range(1, self.sample_count):
                point = self._bezier_point(index / (self.sample_count - 1))
                path.lineTo(self._to_pixel(point.x(), point.y()))
            painter.setPen(QPen(self.palette().highlight(), 2))
            painter.drawPath(path)
            painter.setBrush(self.palette().highlight())
            for point in self.curve_points:
                painter.drawEllipse(self._to_pixel(point.x(), point.y()), 5, 5)
            painter.setPen(QPen(self.palette().mid(), 1))
            for index, handles in enumerate(self._effective_handles()):
                anchor = self.curve_points[index]
                painter.drawLine(self._to_pixel(anchor.x(), anchor.y()), self._to_pixel(handles[0].x(), handles[0].y()))
                painter.drawLine(self._to_pixel(anchor.x(), anchor.y()), self._to_pixel(handles[1].x(), handles[1].y()))
            painter.end()
            return

        if self.curve_mode == "line" and self.curve_points:
            path = QPainterPath(self._to_pixel(self.curve_points[0].x(), self.curve_points[0].y()))
            for point in self.curve_points[1:]:
                path.lineTo(self._to_pixel(point.x(), point.y()))
            painter.setPen(QPen(self.palette().highlight(), 2))
            painter.drawPath(path)
            painter.end()
            return

        if not self.amplitudes:
            painter.end()
            return
        bar_width = rect.width() / len(self.amplitudes)
        painter.setBrush(self.palette().highlight())
        painter.setPen(Qt.PenStyle.NoPen)
        for index, value in enumerate(self.amplitudes):
            height = value * rect.height()
            painter.drawRect(QRectF(rect.left() + index * bar_width + 1, rect.bottom() - height, max(1, bar_width - 2), height))
        painter.end()

    def mousePressEvent(self, event):
        self._emit_mouse_position(event.position())
        if event.button() == Qt.MouseButton.RightButton and self.curve_mode == "bezier":
            self._handle_drag_origin_x = self._from_pixel(event.position())[0]
            self._handle_drag_index = self._nearest_anchor_index(event.position())
            self._handle_drag_side = None
            if self._handle_drag_index is None:
                self._handle_drag_index, self._handle_drag_side = self._nearest_handle(event.position())
            if self._handle_drag_index is not None:
                if self._handle_drag_side is not None:
                    self._update_handle_drag(event.position())
                event.accept()
            else:
                self._handle_drag_index = None
                self._handle_drag_side = None
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self.curve_mode == "bezier" and self.curve_points:
            click_position = event.position()
            distances = [
                abs(self._to_pixel(point.x(), point.y()).x() - click_position.x())
                + abs(self._to_pixel(point.x(), point.y()).y() - click_position.y())
                for point in self._normalized_curve_points(self.curve_points)
            ]
            self.curve_points = self._normalized_curve_points(self.curve_points)
            nearest_index = min(range(len(distances)), key=distances.__getitem__)
            self._drag_index = nearest_index if distances[nearest_index] <= 14 else None
        else:
            self._drag_index = self._bar_index(event.position())
        self._update_drag(event.position())

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_index = None
            anchor_index = self._nearest_anchor_index(event.position())
            if anchor_index is not None:
                if anchor_index in (0, len(self.curve_points) - 1):
                    event.accept()
                    return
                self.remove_curve_point(event)
            else:
                self.add_curve_point(event)
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        self._emit_mouse_position(event.position())
        if self._handle_drag_index is not None:
            self._update_handle_drag(event.position())
        elif self._drag_index is not None:
            self._update_drag(event.position())

    def _emit_mouse_position(self, position):
        x, y = self._from_pixel(position)
        self.mouse_position_changed.emit(x, y)

    def mouseReleaseEvent(self, event):
        del event
        was_dragging = (
            self._drag_index is not None
            or self._handle_drag_index is not None
        )
        self._drag_index = None
        self._handle_drag_index = None
        self._handle_drag_side = None
        self._handle_drag_origin_x = None
        if was_dragging:
            self.values_changed.emit()

    def _nearest_anchor_index(self, position):
        points = self._normalized_curve_points(self.curve_points)
        if not points:
            return None
        distances = [
            abs(self._to_pixel(point.x(), point.y()).x() - position.x())
            + abs(self._to_pixel(point.x(), point.y()).y() - position.y())
            for point in points
        ]
        index = min(range(len(distances)), key=distances.__getitem__)
        return index if distances[index] <= 20 else None

    def _nearest_handle(self, position):
        handles = self._effective_handles()
        candidates = [
            (abs(self._to_pixel(handle.x(), handle.y()).x() - position.x())
             + abs(self._to_pixel(handle.x(), handle.y()).y() - position.y()), index, side)
            for index, pair in enumerate(handles)
            for side, handle in enumerate(pair)
        ]
        if not candidates:
            return None, None
        distance, index, side = min(candidates)
        return (index, side) if distance <= 18 else (None, None)

    def _effective_handles(self):
        points = self._normalized_curve_points(self.curve_points)
        handles = list(self.curve_handles)
        while len(handles) < len(points):
            handles.append(None)
        effective = []
        for index, point in enumerate(points):
            handle = handles[index]
            if handle is None:
                if index == 0:
                    right = points[1] if len(points) > 1 else point
                    vector = QPointF((right.x() - point.x()) / 3.0, (right.y() - point.y()) / 3.0)
                elif index == len(points) - 1:
                    left = points[index - 1]
                    vector = QPointF((point.x() - left.x()) / 3.0, (point.y() - left.y()) / 3.0)
                else:
                    left = points[index - 1]
                    right = points[index + 1]
                    delta_x = max(0.0001, right.x() - left.x())
                    slope = (right.y() - left.y()) / delta_x
                    vector = QPointF(
                        (point.x() - left.x()) / 3.0,
                        slope * (point.x() - left.x()) / 3.0,
                    )
                effective.append((
                    QPointF(point.x() - vector.x(), point.y() - vector.y()),
                    QPointF(point.x() + vector.x(), point.y() + vector.y()),
                ))
            else:
                effective.append(handle)
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
            horizontal_delta = x - origin_x
            if abs(horizontal_delta) <= 0.0001:
                return
            self._handle_drag_side = 1 if horizontal_delta > 0.0 else 0
        vector_x = max(-0.45, min(0.45, x - anchor.x()))
        vector_y = max(-0.45, min(0.45, y - anchor.y()))
        self.curve_handles = list(self._effective_handles())
        moved = QPointF(
            anchor.x() + vector_x,
            max(0.0, min(1.0, anchor.y() + vector_y)),
        )
        opposite = QPointF(
            anchor.x() - vector_x,
            max(0.0, min(1.0, anchor.y() - vector_y)),
        )
        self.curve_handles[index] = (
            (moved, opposite)
            if self._handle_drag_side == 0
            else (opposite, moved)
        )
        self.update()

    def _update_drag(self, position):
        if self._drag_index is None:
            return
        self.curve_points = self._normalized_curve_points(self.curve_points)
        x, y = self._from_pixel(position)
        if self.curve_mode == "bezier" and self.curve_points:
            old = self.curve_points[self._drag_index]
            is_endpoint = self._drag_index in (0, len(self.curve_points) - 1)
            previous_handles = self._effective_handles()
            if not is_endpoint:
                previous_point = self.curve_points[self._drag_index - 1]
                following_point = self.curve_points[self._drag_index + 1]
                x = max(previous_point.x() + 0.001, min(following_point.x() - 0.001, x))
            delta_x = (old.x() if is_endpoint else x) - old.x()
            delta_y = y - old.y()
            self.curve_points[self._drag_index] = QPointF(
                old.x() if is_endpoint else x,
                y,
            )
            self.curve_handles = [
                (
                    QPointF(handle.x() + delta_x, max(0.0, min(1.0, handle.y() + delta_y))),
                    QPointF(other.x() + delta_x, max(0.0, min(1.0, other.y() + delta_y))),
                )
                if index == self._drag_index
                else (handle, other)
                for index, (handle, other) in enumerate(previous_handles)
            ]
            self.curve_points = self._normalized_curve_points(self.curve_points)
            dragged_x = old.x() if is_endpoint else x
            self._drag_index = min(
                range(len(self.curve_points)),
                key=lambda index: abs(self.curve_points[index].x() - dragged_x)
                + abs(self.curve_points[index].y() - y),
            )
        else:
            self.amplitudes[self._drag_index] = y
        self.update()

    def sampled_values(self, count):
        if self.curve_mode == "line" and self.curve_points:
            points = self._normalized_curve_points(self.curve_points)
            return tuple(
                self._linear_point(points, index / max(1, count - 1)).y()
                for index in range(count)
            )
        if self.curve_mode != "bezier" or not self.curve_points:
            return tuple(self.amplitudes)
        return tuple(self._bezier_point(index / max(1, count - 1)).y() for index in range(count))

    @staticmethod
    def _linear_point(points, progress):
        if progress <= points[0].x():
            return points[0]
        if progress >= points[-1].x():
            return points[-1]
        for start, end in zip(points, points[1:]):
            if progress <= end.x():
                ratio = (progress - start.x()) / max(0.0001, end.x() - start.x())
                return QPointF(
                    progress,
                    start.y() + ratio * (end.y() - start.y()),
                )
        return points[-1]

    def _bezier_point(self, progress):
        """Evaluate a connected cubic segment through the anchor points."""
        points = self._normalized_curve_points(self.curve_points)
        if len(points) == 1:
            return points[0]
        if progress <= points[0].x():
            return points[0]
        if progress >= points[-1].x():
            return points[-1]

        segment_index = next(
            index
            for index, (start, end) in enumerate(zip(points, points[1:]))
            if progress <= end.x()
        )
        start = points[segment_index]
        end = points[segment_index + 1]
        delta_x = max(0.0001, end.x() - start.x())
        local = (progress - start.x()) / delta_x

        handles = self._effective_handles()
        raw_start = handles[segment_index][1]
        raw_end = handles[segment_index + 1][0]
        minimum_y = min(start.y(), end.y())
        maximum_y = max(start.y(), end.y())
        control_start = QPointF(
            max(start.x(), min(end.x(), raw_start.x())),
            max(minimum_y, min(maximum_y, raw_start.y())),
        )
        control_end = QPointF(
            max(start.x(), min(end.x(), raw_end.x())),
            max(minimum_y, min(maximum_y, raw_end.y())),
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

    @staticmethod
    def _monotonic_slope(previous, point, following):
        """Limit generated handles so a segment cannot overshoot its anchors."""
        left_delta_x = max(0.0001, point.x() - previous.x())
        right_delta_x = max(0.0001, following.x() - point.x())
        left_slope = (point.y() - previous.y()) / left_delta_x
        right_slope = (following.y() - point.y()) / right_delta_x
        if left_slope * right_slope <= 0.0:
            return 0.0
        magnitude = min(abs(left_slope), abs(right_slope))
        return (1.0 if left_slope > 0.0 else -1.0) * magnitude

    def serialized_curve_points(self):
        self.curve_points = self._normalized_curve_points(self.curve_points)
        return tuple((point.x(), point.y()) for point in self.curve_points)

    def serialized_curve_handles(self):
        return tuple(
            tuple((point.x(), point.y()) for point in handles)
            if handles is not None
            else None
            for handles in self.curve_handles
        )
