from PySide6.QtWidgets import QWidget

from .model import ColourmapModel
from .view import ColourmapView


def create_colourmap_dialog(
    model: ColourmapModel | None = None,
    parent: QWidget | None = None,
    tree_search=None,
    deduper=None,
) -> ColourmapView:
    """Build the colourmap creation or editing dialog."""
    deduper = deduper or (lambda name: name)
    return ColourmapView(
        model=model or ColourmapModel(),
        parent=parent,
        tree_search=tree_search,
        deduper=deduper,
    )
