from typing import Optional

from PySide6.QtWidgets import QWidget

from .model import PerlinNoiseTransformModel
from .view import PerlinNoiseTransformView


def create_perlin_noise_transform_dialog(
    model: Optional[PerlinNoiseTransformModel] = None,
    parent: Optional[QWidget] = None,
) -> PerlinNoiseTransformView:
    """Build the Perlin transform creation/import editor."""
    return PerlinNoiseTransformView(
        model=model or PerlinNoiseTransformModel(),
        parent=parent,
    )
