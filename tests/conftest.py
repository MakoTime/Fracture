import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from components.tree.roots import colourmap_root, mesh_root, root_objects, transform_root


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def clean_tree(qapp):
    root_objects.nodes[:] = [mesh_root, transform_root, colourmap_root]
    mesh_root.children.clear()
    transform_root.children.clear()
    yield
    root_objects.nodes[:] = [mesh_root, transform_root, colourmap_root]
    mesh_root.children.clear()
    transform_root.children.clear()
