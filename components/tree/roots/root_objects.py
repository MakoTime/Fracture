from ..model import TreeNode
from .colourmaps import colourmap_root
from .mesh import mesh_root
from .transforms import transform_root


class RootObjects:
    """Singleton registry for nodes displayed at the tree root."""

    def __init__(self):
        self.nodes = [mesh_root, transform_root, colourmap_root]

    def add(self, node: TreeNode):
        if node not in self.nodes:
            self.nodes.append(node)
        return node

    def remove(self, node: TreeNode):
        if node in (mesh_root, transform_root, colourmap_root):
            return False
        if node not in self.nodes:
            return False
        self.nodes.remove(node)
        return True

    def remove_object(self, node_object):
        """Remove all tree nodes representing a project object."""
        removed = False
        for root in tuple(self.nodes):
            if root.node_object is node_object:
                removed = self.remove(root) or removed
                continue
            removed = root.remove_object_nodes(node_object) or removed
        return removed

    def get_nodes(self):
        return self.nodes


root_objects = RootObjects()