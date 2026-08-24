from src.common.icons import get_icon
from src.components.tree.model import TreeNode


class ColourmapRoot(TreeNode):
    """Persistent root category for colourmap objects."""

    def __init__(self):
        super().__init__(
            name="Colourmaps",
            icon=get_icon("folder"),
            parent=None,
            node_object=None,
        )


colourmap_root = ColourmapRoot()
