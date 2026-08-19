from ..model import TreeNode
from .mesh import mesh_root


class RootObjects:
    """Singleton registry for nodes displayed at the tree root."""

    def __init__(self):
        self.nodes = [mesh_root]

    def add(self, node: TreeNode):
        if node not in self.nodes:
            self.nodes.append(node)
        return node

    def remove(self, node: TreeNode):
        if node is mesh_root:
            return False
        if node not in self.nodes:
            return False
        self.nodes.remove(node)
        return True

    def get_nodes(self):
        return self.nodes


root_objects = RootObjects()