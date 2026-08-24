from common.icons import get_icon

from ..model import TreeNode


class TransformRoot(TreeNode):
    """Persistent root category for transform objects."""

    def __init__(self):
        super().__init__(
            name="Transforms",
            icon=get_icon("folder"),
            parent=None,
            node_object=None,
        )


transform_root = TransformRoot()
