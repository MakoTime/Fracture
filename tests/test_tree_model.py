from PySide6.QtCore import QModelIndex, Qt

from components.tree import TreeModel, TreeNode, TreeSearch
from dialog.perlin_noise_transform import PerlinNoiseTransformModel


def test_tree_model_exposes_hierarchy_and_parent_indexes(qapp):
    root = TreeNode("Root")
    child = TreeNode("Child")
    root.add_child(child)
    model = TreeModel([root])

    root_index = model.index(0, 0)
    child_index = model.index(0, 0, root_index)

    assert model.rowCount(QModelIndex()) == 1
    assert model.data(root_index, Qt.DisplayRole) == "Root"
    assert model.data(child_index, Qt.DisplayRole) == "Child"
    assert model.parent(child_index) == root_index


def test_tree_model_tracks_expansion_state(qapp):
    node = TreeNode("Root")
    model = TreeModel([node])
    index = model.index(0, 0)

    assert model.is_expanded(index) is False
    model.set_expanded(index, True)
    assert model.is_expanded(index) is True


def test_tree_model_refreshes_after_children_change(qapp):
    root = TreeNode("Root")
    model = TreeModel([root])
    root_index = model.index(0, 0)

    root.add_child(TreeNode("New Child"))
    model.refresh()

    assert model.rowCount(root_index) == 1
    assert model.data(model.index(0, 0, root_index), Qt.DisplayRole) == "New Child"


def test_tree_node_shows_block_child_object_and_search_deduplicates_alias():
    transform = PerlinNoiseTransformModel(name="Shared").to_object()
    parent = TreeNode("Generated")
    transform_root = TreeNode("Transforms")
    transform_root.add_child(transform.node)
    parent.set_block_child_objects([transform])

    try:
        assert parent.children[0].node_object is transform
        assert parent.children[0].block_object is transform.block_object
        found = TreeSearch([parent, transform_root]).find()
        assert found == [transform]
    finally:
        transform.remove_from_tree()


def test_tree_object_removal_removes_child_aliases():
    transform = PerlinNoiseTransformModel(name="Shared").to_object()
    parent = TreeNode("Generated")
    transform_root = TreeNode("Transforms")
    transform_root.add_child(transform.node)
    parent.set_block_child_objects([transform])
    roots = [parent, transform_root]

    from components.tree.roots import root_objects

    root_objects.nodes.append(parent)
    root_objects.nodes.append(transform_root)
    try:
        transform.destroy()
        assert parent.children == []
        assert transform_root.children == []
    finally:
        if parent in root_objects.nodes:
            root_objects.nodes.remove(parent)
        if transform_root in root_objects.nodes:
            root_objects.nodes.remove(transform_root)


def test_destroying_parent_detaches_block_child_aliases():
    transform = PerlinNoiseTransformModel(name="Shared").to_object()
    parent_object = PerlinNoiseTransformModel(name="Parent").to_object()
    parent_object.node.set_block_child_objects([transform])
    stale_alias = parent_object.node.children[0]

    parent_object.destroy()

    assert stale_alias.parent is None
