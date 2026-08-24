from PySide6.QtWidgets import QWidget

from .model import PerlinNoiseTransformModel
from .view import PerlinNoiseTransformView


def create_perlin_noise_transform_dialog(
    model: PerlinNoiseTransformModel | None = None,
    parent: QWidget | None = None,
    deduper=None,
) -> PerlinNoiseTransformView:
    """Build the Perlin transform creation/import editor."""
    deduper = deduper or (lambda name: name)
    return PerlinNoiseTransformView(
        model=model or PerlinNoiseTransformModel(),
        parent=parent,
        deduper=deduper,
    )
