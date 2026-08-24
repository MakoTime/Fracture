from src.common.icons import get_icon

from ..model import TreeNode


class MeshRoot(TreeNode):
    """Persistent root category for mesh objects."""

    def __init__(self):
        super().__init__(
            name="Meshes", icon=get_icon("folder"), parent=None, node_object=None
        )


mesh_root = MeshRoot()
