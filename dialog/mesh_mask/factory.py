from typing import Optional

from PySide6.QtWidgets import QWidget

from .model import SurfaceMaskModel
from .view import SurfaceMaskView


def create_surface_mask_dialog(
    axis: str,
    shape: tuple[int, int],
    mask=None,
    parent: Optional[QWidget] = None,
) -> SurfaceMaskView:
    """Build a surface-mask editor for one generated-mesh plane."""
    model = SurfaceMaskModel(axis=axis, shape=shape, mask=mask)
    return SurfaceMaskView(model, parent=parent)
