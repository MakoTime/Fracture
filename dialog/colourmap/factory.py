from typing import Optional

from PySide6.QtWidgets import QWidget

from .model import ColourmapModel
from .view import ColourmapView


def create_colourmap_dialog(
    model: Optional[ColourmapModel] = None,
    parent: Optional[QWidget] = None,
    tree_search=None,
) -> ColourmapView:
    """Build the colourmap creation or editing dialog."""
    return ColourmapView(
        model=model or ColourmapModel(),
        parent=parent,
        tree_search=tree_search,
    )
