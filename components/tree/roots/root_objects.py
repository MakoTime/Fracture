from ..model import TreeNode
from .colourmaps import colourmap_root
from .mesh import mesh_root
from .transforms import transform_root
from .islands import island_root


class RootObjects:
    """Singleton registry for nodes displayed at the tree root."""

    def __init__(self):
        self.nodes = [mesh_root, transform_root, colourmap_root, island_root]
        self._protected_nodes = set(self.nodes)

    def add(self, node: TreeNode):
        if node not in self.nodes:
            self.nodes.append(node)
        return node

    def protect(self, node: TreeNode):
        """Keep a persistent root node from being removed."""
        self._protected_nodes.add(node)
        return self.add(node)

    def remove(self, node: TreeNode):
        if node in self._protected_nodes:
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
        self._ensure_special_roots_last()
        return self.nodes

    def _ensure_special_roots_last(self):
        """Keep persistent category roots ordered before WorldConfig."""
        from .world_config_root import world_config

        for node in (island_root, world_config.node):
            if node in self.nodes:
                self.nodes.remove(node)
        self.nodes.extend((island_root, world_config.node))


root_objects = RootObjects()