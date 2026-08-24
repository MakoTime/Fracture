from collections.abc import Callable, Iterable

from .model import TreeNode


class TreeSearch:
    """Search project objects below a collection of tree roots."""

    def __init__(self, roots: Iterable[TreeNode]):
        self.roots = roots

    def find(self, filter: Callable[[TreeNode], bool] | None = None):
        """Return node objects matching ``filter`` in tree order."""
        matches = []
        seen = set()
        for root in self.roots:
            self._collect(root, filter, matches, seen)
        return matches


    def _collect(self, node, filter, matches, seen):
        if node.node_object is not None and (filter is None or filter(node)):
            identity = getattr(node.node_object, "guid", id(node.node_object))
            if identity not in seen:
                matches.append(node.node_object)
                seen.add(identity)
        for child in node.children:
            self._collect(child, filter, matches, seen)
