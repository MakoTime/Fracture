from PySide6.QtCore import QPointF
import numpy as np

def _implementation():
    from dialog.perlin_noise_transform.graph import FrequencyAmplitudeGraph

    return FrequencyAmplitudeGraph


class BezierCurveGraph:
    """Shared lazy entry point for the application's Bezier curve editor."""

    def __new__(cls, *args, **kwargs):
        return _implementation()(*args, **kwargs)

    @staticmethod
    def _normalized_curve_points(points):
        return _implementation()._normalized_curve_points(points)


def evaluate_bezier(points, handles, progress):
    """Evaluate a normalized connected cubic Bezier curve without creating a widget."""
    return evaluate_prepared_bezier(prepare_bezier(points, handles), progress)


def prepare_bezier(points, handles):
    normalized = normalize_curve_points(points)
    return normalized, _effective_handles(normalized, handles)


def evaluate_prepared_bezier(prepared, progress):
    normalized, effective = prepared
    if len(normalized) < 2:
        return normalized[0][1] if normalized else 0.0
    progress = max(0.0, min(1.0, float(progress)))
    index = next(
        (index for index, (_, end) in enumerate(zip(normalized, normalized[1:])) if progress <= end[0]),
        len(normalized) - 2,
    )
    start, end = normalized[index], normalized[index + 1]
    local = (progress - start[0]) / max(0.0001, end[0] - start[0])
    control_start = effective[index][1]
    control_end = effective[index + 1][0]
    minimum = min(start[1], end[1])
    maximum = max(start[1], end[1])
    control_start = (max(start[0], min(end[0], control_start[0])), max(minimum, min(maximum, control_start[1])))
    control_end = (max(start[0], min(end[0], control_end[0])), max(minimum, min(maximum, control_end[1])))
    inverse = 1.0 - local
    return (
        inverse**3 * start[1]
        + 3 * inverse**2 * local * control_start[1]
        + 3 * inverse * local**2 * control_end[1]
        + local**3 * end[1]
    )


def evaluate_prepared_bezier_array(prepared, progress):
    normalized, effective = prepared
    values = np.asarray(progress, dtype=float)
    if len(normalized) < 2:
        return np.full_like(values, normalized[0][1] if normalized else 0.0)
    clipped = np.clip(values, 0.0, 1.0)
    positions = np.asarray([point[0] for point in normalized])
    segment = np.searchsorted(positions, clipped, side="left") - 1
    segment = np.clip(segment, 0, len(normalized) - 2)
    start_x = positions[segment]
    end_x = positions[segment + 1]
    local = (clipped - start_x) / np.maximum(0.0001, end_x - start_x)
    start_y = np.asarray([point[1] for point in normalized])[segment]
    end_y = np.asarray([point[1] for point in normalized])[segment + 1]
    control_start = np.asarray([pair[1][1] for pair in effective])[segment]
    control_end = np.asarray([pair[0][1] for pair in effective])[segment + 1]
    minimum = np.minimum(start_y, end_y)
    maximum = np.maximum(start_y, end_y)
    control_start = np.clip(control_start, minimum, maximum)
    control_end = np.clip(control_end, minimum, maximum)
    inverse = 1.0 - local
    return (
        inverse**3 * start_y
        + 3 * inverse**2 * local * control_start
        + 3 * inverse * local**2 * control_end
        + local**3 * end_y
    )


def _effective_handles(points, handles):
    normalized_handles = list(handles)
    while len(normalized_handles) < len(points):
        normalized_handles.append(None)
    result = []
    for index, point in enumerate(points):
        handle = normalized_handles[index]
        if handle is not None:
            result.append(handle)
            continue
        if index == 0:
            right = points[1]
            vector = ((right[0] - point[0]) / 3, (right[1] - point[1]) / 3)
        elif index == len(points) - 1:
            left = points[index - 1]
            vector = ((point[0] - left[0]) / 3, (point[1] - left[1]) / 3)
        else:
            left = points[index - 1]
            right = points[index + 1]
            delta = max(0.0001, right[0] - left[0])
            slope = (right[1] - left[1]) / delta
            vector = ((point[0] - left[0]) / 3, slope * (point[0] - left[0]) / 3)
        result.append(
            (
                (point[0] - vector[0], point[1] - vector[1]),
                (point[0] + vector[0], point[1] + vector[1]),
            )
        )
    return result


def normalize_curve_points(points):
    return tuple(
        (point.x(), point.y())
        if isinstance(point, QPointF)
        else (float(point[0]), float(point[1]))
        for point in BezierCurveGraph._normalized_curve_points(points)
    )


def normalize_curve_handles(handles):
    normalized = []
    for handle in handles:
        if handle is None:
            normalized.append(None)
        else:
            normalized.append(
                tuple(
                    (point.x(), point.y())
                    if isinstance(point, QPointF)
                    else (float(point[0]), float(point[1]))
                    for point in handle
                )
            )
    return tuple(normalized)
