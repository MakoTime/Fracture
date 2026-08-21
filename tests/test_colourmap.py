import numpy as np

from components.tree import TreeManager
from components.tree.roots import colourmap_root, root_objects
from engine.block_objects import ColourmapBlockObject
from objects.colourmap import ColourmapObject


def test_colourmap_block_interpolates_and_clamps_rgba_values():
    block = ColourmapBlockObject(
        stops=(
            (0.0, (0.0, 0.0, 1.0)),
            (1.0, (1.0, 0.0, 0.0, 0.5)),
        )
    )

    colours = block.apply(np.array([-1.0, 0.5, 2.0]))

    assert colours.shape == (3, 4)
    np.testing.assert_allclose(colours[0], (0.0, 0.0, 1.0, 1.0))
    np.testing.assert_allclose(colours[1], (0.5, 0.0, 0.5, 0.75))
    np.testing.assert_allclose(colours[2], (1.0, 0.0, 0.0, 0.5))


def test_colourmap_block_round_trips_json(tmp_path):
    block = ColourmapBlockObject(
        name="Terrain colours",
        guid="colourmap-guid",
        comments="elevation palette",
        stops=((0.0, (0.1, 0.2, 0.3, 1.0)), (1.0, (0.9, 0.8, 0.7, 1.0))),
    )

    restored = ColourmapBlockObject.load(block.serialise(tmp_path / "map.json"))

    assert restored.name == block.name
    assert restored.guid == block.guid
    assert restored.comments == block.comments
    assert restored.stops == block.stops


def test_colourmap_object_registers_under_colourmap_root():
    object_base = ColourmapObject(name="Terrain colours")
    manager = TreeManager()
    manager.root_nodes = root_objects.get_nodes()

    object_base.add_to_tree(manager)

    try:
        assert object_base.node.parent is colourmap_root
        assert object_base.node in colourmap_root.children
    finally:
        object_base.remove_from_tree()
