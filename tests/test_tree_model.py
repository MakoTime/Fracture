from PySide6.QtCore import QModelIndex, Qt

from components.tree import TreeModel, TreeNode


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
