from common.icons import get_icon

from ..model import TreeNode


class IslandRoot(TreeNode):
    """Persistent root category for island scene objects."""

    def __init__(self):
        super().__init__(name="Islands", icon=get_icon("folder"))


island_root = IslandRoot()
