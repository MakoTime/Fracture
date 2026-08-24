from types import SimpleNamespace

import numpy as np
import pytest
import pyvista as pv

from src.components.tree.roots import root_objects
from src.components.tree import TreeManager, TreeSearch
from src.components.tree.roots import colourmap_root, transform_root
from src.dialog.colourmap import ColourmapModel, create_colourmap_dialog
from src.dialog.colourmap.graph import ColourmapPreview
from src.dialog.mesh_colourmap import MeshColourmapModel
from src.engine.block_objects import (
    ColourmapBlockObject,
    MeshBlockObject,
    PerlinNoiseTransformBlockObject,
)
from src.objects.colourmap import ColourmapObject


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


def test_colourmap_process_runs_value_calculation():
    block = ColourmapBlockObject()
    _prepared = block.prepare()

    processed = block.calculate_values(np.array([0.25, 0.75]))

    np.testing.assert_allclose(processed, block.apply(np.array([0.25, 0.75])))
    assert block.is_valid()


def test_colourmap_process_runs_field_calculation():
    block = ColourmapBlockObject(
        field1_positions=(0.0, 1.0),
        field2_positions=(0.0, 1.0),
        colour_grid=(
            ((0.0, 0.0, 0.0, 1.0), (1.0, 0.0, 0.0, 1.0)),
            ((0.0, 1.0, 0.0, 1.0), (1.0, 1.0, 0.0, 1.0)),
        ),
    )

    processed = block.calculate_fields((np.array([0.25]), np.array([0.75])))

    np.testing.assert_allclose(
        processed,
        block.apply_fields(np.array([0.25]), np.array([0.75])),
    )


def test_colourmap_block_samples_elevation_and_normal_fields():
    block = ColourmapBlockObject(
        field1_positions=(0.0, 1.0),
        field2_positions=(0.0, 1.0),
        colour_grid=(
            ((0.0, 0.0, 0.0, 1.0), (1.0, 0.0, 0.0, 1.0)),
            ((0.0, 1.0, 0.0, 1.0), (1.0, 1.0, 0.0, 1.0)),
        ),
    )

    colours = block.apply_fields(np.array([0.25, 0.75]), np.array([0.0, 1.0]))

    np.testing.assert_allclose(colours[0], (0.25, 0.0, 0.0, 1.0))
    np.testing.assert_allclose(colours[1], (0.75, 1.0, 0.0, 1.0))


def test_colourmap_block_applies_saved_bezier_curves_to_fields():
    block = ColourmapBlockObject(
        field1_curve_points=((0.0, 0.0), (0.5, 0.1), (1.0, 1.0)),
        field2_curve_points=((0.0, 0.0), (1.0, 1.0)),
        colour_grid=(
            ((0.0, 0.0, 0.0, 1.0), (1.0, 1.0, 1.0, 1.0)),
            ((0.0, 0.0, 0.0, 1.0), (1.0, 1.0, 1.0, 1.0)),
        ),
    )

    colours = block.apply_fields(np.array([0.5]), np.array([0.0]))

    assert colours[0, 0] < 0.5


def test_mesh_block_can_attach_a_colourmap():
    colourmap = ColourmapBlockObject()
    mesh = MeshBlockObject()

    mesh.set_colourmap(colourmap)

    assert mesh.colourmap is colourmap
    assert colourmap not in mesh.child_block_objects


def test_destroying_mesh_colourmap_detaches_and_invalidates_parent_mesh():
    colourmap = ColourmapBlockObject()
    mesh = MeshBlockObject(colourmap=colourmap)

    colourmap.destroy()

    assert not mesh.is_destroyed()
    assert mesh.colourmap is None
    assert not mesh.is_valid()


def test_changing_child_colourmap_invalidates_parent_mesh():
    colourmap = ColourmapBlockObject()
    mesh = MeshBlockObject(colourmap=colourmap)
    mesh.validate()
    colourmap.validate()

    colourmap.mark_changed()

    assert not colourmap.is_valid()
    assert not mesh.is_valid()


def test_destroying_colourmap_noise_invalidates_mesh_even_if_already_invalid():
    noise = PerlinNoiseTransformBlockObject()
    colourmap = ColourmapBlockObject(perlin_noise_transform=noise)
    mesh = MeshBlockObject(colourmap=colourmap)
    mesh.validate()
    colourmap.validate()
    noise.validate()

    colourmap.mark_changed()
    noise.destroy()

    assert colourmap.perlin_noise_transform is None
    assert not colourmap.noise_enabled
    assert not colourmap.is_valid()
    assert not mesh.is_valid()


def test_mesh_colourmap_model_applies_field_sources():
    mesh = MeshBlockObject()
    colourmap = ColourmapBlockObject()
    model = MeshColourmapModel(
        colourmap=colourmap,
        field1_source="normal_z",
        field2_source="elevation",
        invert_field1=True,
        invert_field2=False,
    )

    model.apply(mesh)

    assert mesh.colourmap is colourmap
    assert mesh.colourmap_field_sources == ("normal_z", "elevation")
    assert mesh.colourmap_field_inversions == (True, False)


def test_mesh_colourmap_model_applies_global_scope():
    mesh = MeshBlockObject()
    model = MeshColourmapModel(scope="global")

    model.apply(mesh)

    assert mesh.colourmap_scope == "global"


def test_mesh_colourmap_preview_data_is_decoupled_from_mesh():
    mesh_data = pv.Plane(i_resolution=2, j_resolution=2)
    colourmap = ColourmapBlockObject(name="Preview colours")
    model = MeshColourmapModel(
        mesh_object=SimpleNamespace(mesh_data=mesh_data),
        colourmap=colourmap,
    )

    preview = model.preview_data()

    assert preview is not mesh_data
    assert "__colourmap_rgba" in preview.point_data


def test_colourmap_block_round_trips_json(tmp_path):
    block = ColourmapBlockObject(
        name="Terrain colours",
        guid="colourmap-guid",
        comments="elevation palette",
        field1_name="Elevation",
        field2_name="Temperature",
        stops=((0.0, (0.1, 0.2, 0.3, 1.0)), (1.0, (0.9, 0.8, 0.7, 1.0))),
    )

    restored = ColourmapBlockObject.load(block.serialise(tmp_path / "map.json"))

    assert restored.name == block.name
    assert restored.guid == block.guid
    assert restored.comments == block.comments
    assert restored.field1_name == block.field1_name
    assert restored.field2_name == block.field2_name
    assert restored.stops == block.stops


def test_colourmap_block_serialises_to_directory(tmp_path):
    block = ColourmapBlockObject(guid="colourmap-guid")

    output = block.serialise_to_directory(tmp_path)

    assert output == tmp_path / "colourmap-guid.colourmap.json"
    assert output.exists()


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


def test_colourmap_can_apply_noise_from_a_perlin_child():
    transform = PerlinNoiseTransformBlockObject(
        frequencies=(2,),
        amplitudes=(0.2,),
        seed=42,
    )
    colourmap = ColourmapBlockObject(
        perlin_noise_transform=transform,
        noise_enabled=True,
    )
    values = np.full((2, 2, 2), 0.5)

    noisy = colourmap.apply(values)
    plain = colourmap.apply(values, skip_noise=True)

    assert noisy.shape == (2, 2, 2, 4)
    assert not np.allclose(noisy, plain)
    assert transform not in colourmap.child_block_objects


def test_colourmap_noise_transform_can_be_removed():
    transform = PerlinNoiseTransformBlockObject()
    colourmap = ColourmapBlockObject(perlin_noise_transform=transform)

    colourmap.set_perlin_noise_transform(None)

    assert colourmap.perlin_noise_transform is None
    assert colourmap.noise_enabled is True
    assert colourmap.child_block_objects == ()


def test_colourmap_noise_is_disabled_when_transform_is_destroyed():
    transform = PerlinNoiseTransformBlockObject()
    colourmap = ColourmapBlockObject(perlin_noise_transform=transform)

    transform.destroy()

    assert colourmap.perlin_noise_transform is None
    assert colourmap.noise_enabled is False
    assert not colourmap.is_valid()
    assert not colourmap.is_destroyed()


def test_colourmap_rejects_invalid_noise_transform():
    with pytest.raises(TypeError):
        ColourmapBlockObject(perlin_noise_transform="not a transform")


def test_colourmap_dialog_factory_uses_model(qapp):
    model = ColourmapModel(
        name="Terrain palette",
        stops=((0.0, (0.1, 0.2, 0.3, 1.0)), (1.0, (0.9, 0.8, 0.7, 1.0))),
        noise_enabled=True,
    )
    dialog = create_colourmap_dialog(model)

    assert dialog.model is model
    assert dialog.name_field.text() == "Terrain palette"
    assert dialog.field1_name_field.text() == "Field 1"
    assert dialog.field2_name_field.text() == "Field 2"
    assert dialog.stops_table.rowCount() == 2
    assert dialog.noise_enabled_field.isChecked()
    assert dialog.colourmap_preview.stops == model.stops
    assert dialog.axis_graph.minimumSize().width() == 360
    assert dialog.stops_table.rowHeight(0) == dialog.stops_table.columnWidth(0)
    dialog.close()


def test_colourmap_dialog_updates_field_names(qapp):
    dialog = create_colourmap_dialog()

    dialog.field1_name_field.setText("Elevation")
    dialog.field2_name_field.setText("Temperature")
    dialog.update_model()

    assert dialog.model.field1_name == "Elevation"
    assert dialog.model.field2_name == "Temperature"
    assert dialog.field_graph_selector.itemText(0) == "Elevation"
    assert dialog.field_graph_selector.itemText(1) == "Temperature"
    assert dialog.x_field_label.text() == "Elevation"
    assert dialog.y_field_label.text() == "Temperature"
    dialog.close()


def test_colourmap_object_exposes_field_names():
    colourmap = ColourmapObject(
        block_object=ColourmapBlockObject(
            field1_name="Elevation",
            field2_name="Temperature",
        )
    )

    assert colourmap.field1_name == "Elevation"
    assert colourmap.field2_name == "Temperature"
    colourmap.destroy()


def test_colourmap_dialog_updates_stops_and_optional_transform(qapp):
    from src.dialog.perlin_noise_transform import PerlinNoiseTransformModel

    noise = PerlinNoiseTransformModel(name="Noise").to_object()
    transform_root.add_child(noise.node)
    try:
        model = ColourmapModel()
        dialog = create_colourmap_dialog(
            model,
            tree_search=TreeSearch(root_objects.get_nodes()),
        )
        dialog.stops_table.cellWidget(0, 0).setProperty(
            "colour", (0.25, 0.5, 0.75, 1.0)
        )
        dialog._refresh_visuals()
        dialog.transform_field.setCurrentIndex(1)
        dialog.update_model()

        assert model.colour_grid[0][0] == (0.25, 0.5, 0.75, 1.0)
        assert dialog.colourmap_preview.colour_grid[0][0] == model.colour_grid[0][0]
        assert model.perlin_noise_transform is noise
        assert (
            model.to_object().block_object.perlin_noise_transform is noise.block_object
        )
        dialog.close()
    finally:
        noise.remove_from_tree()


def test_colourmap_dialog_inserts_rows_and_columns_between_sections(qapp):
    dialog = create_colourmap_dialog()
    dialog._insert_row(1)
    assert dialog.model.field2_positions == (0.0, 0.5, 1.0)
    assert len(dialog.model.colour_grid) == 3

    dialog._insert_column(1)
    assert dialog.model.field1_positions == (0.0, 0.5, 1.0)
    assert len(dialog.model.colour_grid[0]) == 3

    dialog.field_graph_selector.setCurrentIndex(1)
    assert dialog.axis_graph.frequency_min == 0.0
    dialog.close()


def test_colourmap_graph_uses_bezier_transition_curve(qapp):
    dialog = create_colourmap_dialog(
        ColourmapModel(field1_curve_points=((0.0, 0.0), (0.5, 0.2), (1.0, 1.0)))
    )

    dialog._update_axis_graph()

    assert dialog.axis_graph.curve_points[1].y() == 0.2
    dialog.close()


def test_colourmap_preview_defaults_missing_transition_curves(qapp):
    preview = ColourmapPreview(
        (0.0, 1.0),
        (0.0, 1.0),
        (
            ((0.0, 0.0, 0.0, 1.0), (1.0, 1.0, 1.0, 1.0)),
            ((0.0, 0.0, 0.0, 1.0), (1.0, 1.0, 1.0, 1.0)),
        ),
    )

    assert preview.curve_points1 == ((0.0, 0.0), (1.0, 1.0))
    assert preview.curve_points2 == ((0.0, 0.0), (1.0, 1.0))
    preview.close()


def test_colourmap_preview_matches_three_table_rows(qapp):
    preview = ColourmapPreview(
        (0.0, 1.0),
        (0.0, 0.5, 1.0),
        (
            ((0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 0.0, 1.0)),
            ((0.5, 0.5, 0.5, 1.0), (0.5, 0.5, 0.5, 1.0)),
            ((1.0, 1.0, 1.0, 1.0), (1.0, 1.0, 1.0, 1.0)),
        ),
    )
    preview.resize(280, 250)

    image = preview.grab().toImage()
    x = image.width() // 2
    top = 16
    height = image.height() - 58
    boundaries = (top + height // 3, top + 2 * height // 3)

    for boundary in boundaries:
        before = image.pixelColor(x, boundary - 1).redF()
        after = image.pixelColor(x, boundary).redF()
        assert abs(before - after) < 0.03
    assert image.pixelColor(x, top + 2).redF() < 0.05
    assert image.pixelColor(x, top + height - 3).redF() > 0.95
    preview.close()
