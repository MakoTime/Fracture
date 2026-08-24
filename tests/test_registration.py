from itertools import pairwise
from types import SimpleNamespace

import numpy as np
import pyvista as pv
from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QWidget

from application.importers import (
    ColourmapController,
    MeshImportController,
    ObjectImporterModel,
    TransformController,
)
from application.importers.island_controller import IslandController
from application.importers.world_config_controller import WorldConfigController
from components.scene import ShapeController
from components.table import TableManager, TableModel, TableView
from components.tree import TreeModel
from components.tree.roots import (
    colourmap_root,
    island_root,
    mesh_root,
    root_objects,
    world_config,
)
from dialog.mesh_edit.model import MeshEditModel
from dialog.mesh_filter import MeshFilterModel
from dialog.mesh_generate import GenerateMeshWindow, MeshGenerateModel
from dialog.mesh_import.model import MeshImportModel
from dialog.mesh_mask import SurfaceMaskModel
from dialog.mesh_mask.view import MaskCanvas
from dialog.perlin_noise_transform import PerlinNoiseTransformModel
from engine.block_objects import (
    GeneratedMeshBlockObject,
    IslandBlockObject,
    MeshBlockObject,
)
from engine.block_tasks import (
    IslandTask,
    MeshFilterTask,
    MeshGenerateTask,
    MeshImportTask,
)
from engine.block_tasks.generated_mesh import GeneratedMeshTask
from objects.generated_mesh import GeneratedMesh
from objects.island import Island
from objects.mesh_object import MeshObject
from objects.object_base import ObjectBase
from tests.viewable_test_object import ViewableTestObject


def _perlin_transform(size=4, seed=0, amplitude=1.0):
    return PerlinNoiseTransformModel(
        frequencies=(size,),
        amplitudes=(amplitude,),
        seed=seed,
    ).to_object()


def test_bitmap_elevation_map_creates_structured_grid(qapp, tmp_path):
    image = QImage(2, 2, QImage.Format.Format_RGB32)
    image.setPixelColor(0, 0, QColor(0, 0, 0))
    image.setPixelColor(1, 0, QColor(64, 64, 64))
    image.setPixelColor(0, 1, QColor(128, 128, 128))
    image.setPixelColor(1, 1, QColor(255, 255, 255))
    source_path = tmp_path / "elevation.png"
    assert image.save(str(source_path))

    model = MeshImportModel(source_path=str(source_path))
    mesh = MeshImportController._load_mesh(model)

    assert mesh.dimensions == (2, 2, 1)
    assert mesh.n_points == 4
    assert mesh.points[:, 2].tolist() == [0.0, 64.0, 128.0, 255.0]


def test_elevation_settings_threshold_and_scale_mesh(qapp, tmp_path):
    image = QImage(2, 1, QImage.Format.Format_RGB32)
    image.setPixelColor(0, 0, QColor(10, 10, 10))
    image.setPixelColor(1, 0, QColor(200, 200, 200))
    source_path = tmp_path / "thresholded.png"
    assert image.save(str(source_path))

    model = MeshImportModel(
        source_path=str(source_path),
        low_threshold=50,
        high_threshold=100,
        vertical_scale=2,
    )
    mesh = MeshImportController._load_mesh(model)

    assert mesh.points[:, 2].tolist() == [100.0, 200.0]


def test_mesh_root_menu_separates_import_types(qapp):
    controller = MeshImportController(
        object_importer=SimpleNamespace(),
        tree_view=SimpleNamespace(),
    )

    menu = controller.create_context_menu(mesh_root)

    assert [action.text() for action in menu.actions()] == [
        "Generate Mesh",
        "Generate Procedural Mesh",
        "Import mesh from 3D object",
        "Import Mesh from elevation data",
    ]


def test_mesh_menu_includes_colourmap_editor(qapp):
    controller = MeshImportController(
        object_importer=SimpleNamespace(),
        tree_view=SimpleNamespace(),
    )
    mesh = MeshObject("Terrain", auto_register_root=False)

    menu = controller.create_context_menu(mesh.node)

    assert "Edit Colourmap" in [action.text() for action in menu.actions()]


def test_perlin_transform_menu_includes_edit_action(qapp):
    controller = TransformController(
        object_importer=SimpleNamespace(),
        tree_view=SimpleNamespace(),
    )
    transform = PerlinNoiseTransformModel(
        name="Editable transform",
    ).to_object()

    menu = controller.create_context_menu(transform.node)

    assert [action.text() for action in menu.actions()] == ["Edit", "Delete"]
    transform.remove_from_tree()


def test_colourmap_root_menu_includes_new_action(qapp):
    controller = ColourmapController(
        object_importer=SimpleNamespace(),
        tree_view=SimpleNamespace(),
    )

    menu = controller.create_context_menu(colourmap_root)

    assert [action.text() for action in menu.actions()] == ["New Colourmap"]


def test_world_config_menu_only_allows_editing(qapp):
    controller = WorldConfigController(tree_view=SimpleNamespace())

    menu = controller.create_context_menu(world_config.node)

    assert [action.text() for action in menu.actions()] == ["Edit"]
    assert not root_objects.remove(world_config.node)


def test_perlin_transform_registration_enqueues_block_task(qapp):
    queued = []
    importer = SimpleNamespace(
        register=lambda transform, parent, add_to_scene: transform,
    )
    runner = SimpleNamespace(
        enqueue_block_task=lambda name, task: queued.append((name, task))
    )
    controller = TransformController(
        object_importer=importer,
        tree_view=SimpleNamespace(model=lambda: None),
        engine_runner=runner,
    )

    controller._register(PerlinNoiseTransformModel().to_object())

    assert len(queued) == 1
    assert queued[0][0].startswith("Generate Perlin Noise Transform")


def test_generate_mesh_opens_standalone_window(qapp):
    class FakeSceneViewer(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.plotter = SimpleNamespace(
                add_mesh=lambda *args, **kwargs: None,
                render=lambda: None,
            )

        def clear_scene(self):
            pass

        def zoom_camera(self, factor):
            pass

    import dialog.mesh_generate.view as generate_view

    original_viewer = generate_view.SceneViewer
    generate_view.SceneViewer = FakeSceneViewer
    controller = MeshImportController(
        object_importer=SimpleNamespace(),
        tree_view=SimpleNamespace(),
    )
    try:
        window = controller.generate_mesh()

        wait_loop = QEventLoop()
        poll = QTimer()
        poll.timeout.connect(
            lambda: wait_loop.quit() if window._preview_ready else None
        )
        poll.start(10)
        QTimer.singleShot(2_000, wait_loop.quit)
        wait_loop.exec()
        poll.stop()

        assert window.windowTitle() == "Generate Mesh"
        assert window._preview_ready is True
        assert window.isVisible() is True
        window.close()
    finally:
        generate_view.SceneViewer = original_viewer


def test_generate_mesh_flexible_checkbox_controls_grid_size_editing(qapp):
    window = GenerateMeshWindow(deduper=lambda name: name)

    assert window.flexible_grid.isChecked()
    assert window.grid_size.isEnabled()

    window.flexible_grid.setChecked(False)
    assert window.model.flexible_grid is False
    assert window.grid_size.isEnabled() is False

    window.flexible_grid.setChecked(True)
    assert window.model.flexible_grid is True
    assert window.grid_size.isEnabled()
    window.close()


def test_generate_mesh_grid_point_size_is_adaptive_within_bounds():
    minimum = GenerateMeshWindow.GRID_POINT_SIZE_MIN
    maximum = GenerateMeshWindow.GRID_POINT_SIZE_MAX

    assert GenerateMeshWindow._adaptive_grid_point_size(1) == maximum
    assert GenerateMeshWindow._adaptive_grid_point_size(1_000) == 7.0
    assert GenerateMeshWindow._adaptive_grid_point_size(1_000_000) == minimum


def test_generate_mesh_resizes_flexible_masks_with_grid():
    mask = np.array([[True, False], [False, True]])

    resized = GenerateMeshWindow._resize_mask(mask, (4, 4))

    assert resized.shape == (4, 4)
    np.testing.assert_array_equal(
        resized,
        np.array(
            [
                [True, True, False, False],
                [True, True, False, False],
                [False, False, True, True],
                [False, False, True, True],
            ]
        ),
    )


def test_generate_mesh_grid_point_alpha_slider_updates_preview_setting(qapp):
    window = GenerateMeshWindow(deduper=lambda name: name)

    window.grid_point_alpha.setValue(35)

    assert window.grid_point_alpha_value.text() == "35%"
    window.close()


def test_mesh_generate_model_creates_empty_mesh():
    model = MeshGenerateModel(name="Grid", grid_size=(2, 3, 4))

    mesh = model.generate()

    assert mesh.name == "Grid"
    assert isinstance(mesh, GeneratedMesh)
    assert mesh.mesh_data.n_points == 0
    assert mesh.grid_shape == (2, 3, 4)
    assert mesh.grid_data.dtype == float
    assert model.grid_points().shape == (24, 3)


def test_mesh_generate_model_creates_generation_block_task():
    model = MeshGenerateModel(name="Grid", grid_size=(2, 3, 4))

    task = model.to_mesh_generate_task()
    block = task.execute(task.prepare())

    assert isinstance(task, MeshGenerateTask)
    assert block is task.block_object
    assert isinstance(block, GeneratedMeshBlockObject)
    assert block.name == "Grid"
    assert block.mesh_data.n_points == 0
    assert task.grid_data.shape == (2, 3, 4)
    assert task.grid_data.dtype == float


def test_generate_mesh_grid_points_use_block_values_as_scalars():
    model = MeshGenerateModel(grid_size=(2, 2, 2))
    values = np.arange(8, dtype=float).reshape((2, 2, 2))

    point_cloud = GenerateMeshWindow._build_grid_point_cloud(
        model.grid_points(),
        values,
    )

    np.testing.assert_array_equal(point_cloud.point_data["grid_value"], values.ravel())


def test_mesh_generate_task_extracts_scalar_isosurface():
    values = np.zeros((3, 3, 3), dtype=float)
    values[1:, :, :] = 1.0

    mesh = MeshGenerateTask._build_surface_mesh(values, isovalue=0.5)

    assert mesh.n_points > 0
    assert mesh.n_cells > 0


def test_mesh_generate_noise_is_limited_to_surface_penetration():
    model = MeshGenerateModel(
        grid_size=(5, 5, 5),
        noise_enabled=True,
        noise_penetration=1,
        perlin_noise_transform=_perlin_transform(seed=11),
    )
    model.set_mask("x", np.array([[True, False, True, True, True]] * 5))
    field = MeshGenerateTask(model)._build_grid_data((5, 5, 5))

    assert field[2, 3, 3] == 1.0
    assert np.any(field[:, 0, 2] != 1.0)
    assert np.all(field[:, :, 1] == 0.0)

    model.perlin_noise_transform.block_object.seed = 12
    other_field = MeshGenerateTask(model)._build_grid_data((5, 5, 5))
    assert not np.array_equal(field, other_field)


def test_mesh_generate_noise_perturbs_a_masked_surface_field():
    model = MeshGenerateModel(grid_size=(4, 4, 4))
    model.set_mask("x", np.array([[False, True, True, True]] * 4))
    baseline = MeshGenerateTask(model)._build_grid_data((4, 4, 4))
    model.noise_enabled = True
    model.perlin_noise_transform = _perlin_transform(amplitude=0.5)
    noisy = MeshGenerateTask(model)._build_grid_data((4, 4, 4))

    assert not np.array_equal(noisy, baseline)


def test_mesh_generate_noise_does_nothing_without_a_perlin_transform():
    model = MeshGenerateModel(
        grid_size=(4, 4, 4),
        noise_enabled=True,
    )
    model.set_mask("x", np.array([[False, True, True, True]] * 4))

    task = MeshGenerateTask(model)
    field = task._build_grid_data((4, 4, 4))

    active_mask = task._build_active_mask((4, 4, 4))
    assert np.all(field[active_mask] == 1.0)
    assert np.all(field[~active_mask] == 0.0)


def test_mesh_generate_noise_follows_an_interior_mask_edge():
    model = MeshGenerateModel(
        grid_size=(5, 5, 5),
        noise_enabled=True,
        perlin_noise_transform=_perlin_transform(seed=11),
        noise_penetration=1,
    )
    mask = np.ones((5, 5), dtype=bool)
    mask[1, 1] = False
    model.set_mask("x", mask)

    field = MeshGenerateTask(model)._build_grid_data((5, 5, 5))

    assert np.all(field[:, 1, 1] == 0.0)
    assert np.any(field[:, 0:3, 1:3] != 1.0)
    assert field[2, 3, 3] == 1.0


def test_mesh_generate_noise_displaces_the_contour_band():
    model = MeshGenerateModel(
        grid_size=(5, 5, 5),
        noise_enabled=True,
        perlin_noise_transform=_perlin_transform(seed=11),
    )
    model.set_mask("x", np.array([[True, False, True, True, True]] * 5))
    task = MeshGenerateTask(model)

    field = task._build_grid_data((5, 5, 5))

    active_values = field[task._build_active_mask((5, 5, 5))]
    assert active_values.min() < 0.75
    assert active_values.max() > 0.75


def test_mesh_generate_transform_frequency_and_penetration_change_mesh_shape():
    mask = np.ones((12, 12), dtype=bool)
    mask[6:, :] = False
    base_settings = dict(
        grid_size=(12, 12, 12),
        noise_enabled=True,
        x_mask=mask,
    )
    low_frequency = (
        MeshGenerateModel(
            **base_settings,
            perlin_noise_transform=_perlin_transform(size=2, seed=11),
            noise_penetration=1,
        )
        .generate()
        .mesh_data
    )
    high_frequency = (
        MeshGenerateModel(
            **base_settings,
            perlin_noise_transform=_perlin_transform(size=8, seed=11),
            noise_penetration=1,
        )
        .generate()
        .mesh_data
    )
    deep_penetration = (
        MeshGenerateModel(
            **base_settings,
            perlin_noise_transform=_perlin_transform(seed=11),
            noise_penetration=6,
        )
        .generate()
        .mesh_data
    )

    assert not np.array_equal(low_frequency.points, high_frequency.points)
    assert deep_penetration.n_points != high_frequency.n_points


def test_mesh_generate_transform_displacement_blends_from_original_field():
    mask = np.ones((8, 8), dtype=bool)
    mask[4:, :] = False
    model = MeshGenerateModel(
        grid_size=(8, 8, 8),
        noise_enabled=True,
        noise_penetration=4,
        x_mask=mask,
    )
    baseline = MeshGenerateTask(model)._build_grid_data((8, 8, 8))

    model.perlin_noise_transform = _perlin_transform()
    displaced = MeshGenerateTask(model)._build_grid_data((8, 8, 8))

    active = MeshGenerateTask(model)._build_active_mask((8, 8, 8))
    assert np.all(baseline[active] == 1.0)
    assert not np.array_equal(baseline, displaced)


def test_mesh_generate_surface_distance_uses_mask_edges_not_grid_edges():
    active_mask = np.ones((5, 5, 5), dtype=bool)
    active_mask[:, 2, 2] = False

    distance = MeshGenerateTask._build_surface_distance(active_mask, 3)

    assert distance[2, 1, 2] == 0
    assert distance[2, 0, 2] == 1
    assert distance[2, 0, 0] == -1


def test_mesh_generate_penetration_one_targets_nodes_adjacent_to_falling_edge():
    active_mask = np.ones((6, 6, 6), dtype=bool)
    active_mask[3:, :, :] = False

    distance = MeshGenerateTask._build_surface_distance(active_mask, 1)

    assert np.all(distance[2, :, :] == 0)
    assert np.all(distance[:2, :, :] == -1)
    assert np.all(distance[3:, :, :] == -1)


def test_mesh_generate_noise_uses_configured_contour_levels():
    model = MeshGenerateModel(
        grid_size=(4, 4, 4),
        noise_enabled=True,
        perlin_noise_transform=_perlin_transform(),
    )
    model.set_mask("x", np.array([[False, True, True, True]] * 4))
    task = MeshGenerateTask(model)

    block = task.execute(task.prepare())

    assert task._contour_levels() == (0.75,)
    assert block.mesh_data.n_points > 0
    assert block.mask_mesh_data.n_points > 0


def test_mesh_generate_masks_remain_zero_after_noise_is_applied():
    model = MeshGenerateModel(
        grid_size=(4, 4, 4),
        noise_enabled=True,
        perlin_noise_transform=_perlin_transform(),
        flexible_masks=False,
    )
    model.set_mask("x", np.array([[False, True, True, True]] * 4))

    field = MeshGenerateTask(model)._build_grid_data((4, 4, 4))

    assert np.all(field[:, :, 0] == 0.0)
    assert np.any(field[:, :, 1:] != 0.0)


def test_mesh_generate_flexible_mask_can_displace_both_sides_of_edge():
    model = MeshGenerateModel(
        grid_size=(6, 6, 6),
        noise_enabled=True,
        perlin_noise_transform=_perlin_transform(),
        noise_penetration=2,
        flexible_masks=True,
    )
    model.set_mask("x", np.array([[True, False, True, True, True, True]] * 6))

    field = MeshGenerateTask(model)._build_grid_data((6, 6, 6))

    assert np.any(field[:, :, 1] != 0.0)


def test_surface_masks_penetrate_their_corresponding_grid_axis():
    model = MeshGenerateModel(grid_size=(3, 4, 5))
    model.set_mask("x", np.array([[True, False, True, False, True]] * 4))
    model.set_mask("y", np.ones((3, 5), dtype=bool))
    model.set_mask("z", np.ones((3, 4), dtype=bool))

    field = MeshGenerateTask(model)._build_grid_data((3, 4, 5))

    assert field.shape == (3, 4, 5)
    assert np.all(field[:, :, 0])
    assert not np.any(field[:, :, 1])
    assert np.all(field[:, :, 2])


def test_blank_surface_masks_are_full():
    model = MeshGenerateModel(grid_size=(2, 3, 4))

    field = MeshGenerateTask(model)._build_grid_data((2, 3, 4))

    assert np.all(field == 1.0)


def test_surface_mask_view_axes_preserve_world_orientation():
    for axis, stored_shape, view_axes, view_shape in (
        ("X", (2, 3), ("Y", "Z"), (3, 2)),
        ("Y", (2, 4), ("X", "Z"), (4, 2)),
        ("Z", (2, 3), ("X", "Y"), (3, 2)),
    ):
        model = SurfaceMaskModel(axis, stored_shape)
        values = np.arange(np.prod(view_shape)).reshape(view_shape) % 2 == 0

        assert model.view_axes == view_axes
        assert model.view_shape == view_shape
        model.set_view_values(values)
        np.testing.assert_array_equal(model.view_values(), values)


def test_surface_mask_canvas_top_row_maps_to_high_vertical_index():
    for axis, shape in (("X", (2, 3)), ("Y", (2, 3)), ("Z", (2, 3))):
        model = SurfaceMaskModel(axis, shape)
        view_values = np.zeros(model.view_shape, dtype=bool)
        view_values[0, 0] = True

        model.set_view_values(view_values)

        expected = np.zeros(shape, dtype=bool)
        expected[0, -1] = True
        np.testing.assert_array_equal(model.mask, expected)


def test_surface_mask_drag_interpolation_fills_skipped_cells():
    cells = MaskCanvas._line_cells((0, 0), (5, 8))

    assert cells[0] == (0, 0)
    assert cells[-1] == (5, 8)
    assert len(cells) == 9
    assert all(
        max(abs(next_row - row), abs(next_column - column)) <= 1
        for (row, column), (next_row, next_column) in pairwise(cells)
    )


def test_generated_mesh_validates_three_dimensional_scalar_field():
    mesh = GeneratedMesh("Grid", grid_data=[[[1, 0], [0, 1]]])

    assert mesh.grid_shape == (1, 2, 2)
    assert mesh.grid_data.dtype == float
    assert mesh.grid_data.tolist() == [[[1.0, 0.0], [0.0, 1.0]]]

    try:
        GeneratedMesh("Invalid", grid_data=[[True, False]])
    except ValueError as error:
        assert "three-dimensional scalar field" in str(error)
    else:
        raise AssertionError("two-dimensional scalar data should be rejected")


def test_generated_mesh_rejects_non_finite_scalar_values():
    try:
        GeneratedMesh("Invalid", grid_data=[[[float("nan")]]])
    except ValueError as error:
        assert "finite" in str(error)
    else:
        raise AssertionError("non-finite scalar data should be rejected")


def test_generate_mesh_apply_creates_mesh(qapp):
    generated = []
    window = GenerateMeshWindow(on_apply=generated.append, deduper=lambda name: name)
    window.name_field.setText("Applied Grid")
    window.grid_size.set_value((2, 2, 2))

    window._apply()

    assert generated[0].name == "Applied Grid"
    assert generated[0].mesh_data.n_points == 0
    window.close()


def test_mesh_object_menu_includes_edit_action(qapp):
    controller = MeshImportController(
        object_importer=SimpleNamespace(),
        tree_view=SimpleNamespace(),
    )
    mesh_object = MeshImportModel(mesh_data=object()).to_mesh_object()

    menu = controller.create_context_menu(mesh_object.node)

    assert [action.text() for action in menu.actions()] == [
        "Edit Colourmap",
        "Edit Mesh",
        "Show in scene",
        "Delete",
    ]


def test_generated_mesh_menu_includes_edit_generation_action(qapp):
    controller = MeshImportController(
        object_importer=SimpleNamespace(),
        tree_view=SimpleNamespace(),
    )
    mesh_object = MeshGenerateModel(
        name="Generated",
        grid_size=(2, 3, 4),
        noise_enabled=True,
    ).generate()

    menu = controller.create_context_menu(mesh_object.node)

    assert [action.text() for action in menu.actions()] == [
        "Edit Generation",
        "Filter Mesh",
        "Edit Colourmap",
        "Edit Mesh",
        "Show in scene",
        "Delete",
    ]


def test_mesh_filter_requires_an_explicit_transform():
    source = GeneratedMesh(
        "Source",
        grid_data=np.random.default_rng(4).random((4, 4, 4)),
    )
    model = MeshFilterModel.from_mesh(source)

    assert model.perlin_noise_transform is None
    assert model.filter_enabled is False
    try:
        model.generate()
    except ValueError as error:
        assert "transform" in str(error)
    else:
        raise AssertionError("a filter without a transform should be rejected")


def test_mesh_filter_returns_regular_mesh_with_baked_dependencies():
    source = GeneratedMesh(
        "Source",
        grid_data=np.random.default_rng(4).random((8, 8, 8)),
    )
    transform = _perlin_transform(size=4)
    model = MeshFilterModel.from_mesh(source)
    model.perlin_noise_transform = transform
    model.noise_enabled = True

    filtered = model.generate()

    assert isinstance(filtered, MeshObject)
    assert type(filtered.mesh_block_object).__name__ == "MeshBlockObject"
    assert not isinstance(filtered, GeneratedMesh)
    assert filtered.mesh_block_object.child_block_objects == (
        transform.block_object,
        source.mesh_block_object,
    )


def test_mesh_filter_surface_displacement_modifies_the_marching_cubes_grid():
    source = GeneratedMesh(
        "Source",
        grid_data=np.random.default_rng(4).random((8, 8, 8)),
    )
    transform = _perlin_transform(size=4, seed=9)
    transform.block_object.update_configuration(application_mode="surface_displacement")
    task = MeshFilterTask(
        source.mesh_block_object,
        transform.block_object,
        0.25,
        0.75,
    )

    task.execute(task.prepare())

    assert task.mesh_data.n_points > 0
    assert task.mesh_data.n_cells > 0
    assert not np.array_equal(task.grid_data, source.grid_data)


def test_mesh_filter_noise_mask_removes_values_outside_noise_range():
    source = GeneratedMesh(
        "Source",
        grid_data=np.ones((8, 8, 8)),
    )
    transform = _perlin_transform(size=4, seed=9)
    transform.block_object.update_configuration(application_mode="noise_mask")
    task = MeshFilterTask(
        source.mesh_block_object,
        transform.block_object,
        0.49,
        0.51,
    )

    task.execute(task.prepare())

    assert np.any(task.grid_data == 0.0)
    assert np.any(task.grid_data == 1.0)


def test_mesh_filter_uses_source_transform_and_invalidates_source_mesh():
    transform = _perlin_transform(size=4)
    source = GeneratedMesh(
        "Source",
        grid_data=np.random.default_rng(5).random((8, 8, 8)),
        block_object=GeneratedMeshBlockObject(
            name="Source",
            grid_data=np.random.default_rng(5).random((8, 8, 8)),
            perlin_noise_transform=transform.block_object,
        ),
    )
    model = MeshFilterModel.from_mesh(source)
    model.perlin_noise_transform = transform
    model.noise_enabled = True

    filtered = model.generate()

    assert filtered.mesh_block_object.child_block_objects == (
        transform.block_object,
        source.mesh_block_object,
    )
    source.mesh_block_object.validate()
    filtered.mesh_block_object.validate()
    transform.block_object.invalidate(force=True)

    assert not source.mesh_block_object.is_valid()
    assert not filtered.mesh_block_object.is_valid()


def test_generated_mesh_transform_setter_keeps_same_transform_child():
    transform = _perlin_transform(size=4)
    block = GeneratedMeshBlockObject(
        name="Source",
        grid_data=np.ones((4, 4, 4)),
        perlin_noise_transform=transform.block_object,
    )
    block.validate()

    assert (
        block.set_perlin_noise_transform(transform.block_object)
        is transform.block_object
    )
    assert block.is_valid()
    assert transform.block_object in block.child_block_objects


def test_generated_mesh_generation_settings_can_reopen():
    model = MeshGenerateModel(
        name="Generated",
        grid_size=(2, 3, 4),
        flexible_grid=False,
        flexible_masks=False,
        show_mask_surface=False,
        noise_enabled=True,
        noise_minimum=0.2,
        noise_maximum=0.8,
        noise_penetration=2,
        perlin_noise_transform=_perlin_transform(size=7, seed=23),
    )
    model.set_mask("x", np.ones((3, 4), dtype=bool))
    mesh_object = model.generate()

    reopened = MeshGenerateModel.from_generated_mesh(mesh_object)

    assert reopened.name == model.name
    assert reopened.grid_size == model.grid_size
    assert reopened.flexible_grid is False
    assert reopened.flexible_masks is False
    assert reopened.show_mask_surface is False
    assert reopened.noise_enabled is True
    assert reopened.noise_minimum == 0.2
    assert reopened.noise_maximum == 0.8
    assert reopened.perlin_noise_transform.frequencies == (7,)
    assert reopened.perlin_noise_transform.seed == 23
    assert reopened.noise_penetration == 2
    np.testing.assert_array_equal(reopened.x_mask, model.x_mask)


def test_edit_generation_masks_rebuild_from_the_unmasked_source():
    initial_mask = np.ones((6, 6), dtype=bool)
    initial_mask[:3, :] = False
    model = MeshGenerateModel(grid_size=(6, 6, 6), x_mask=initial_mask)
    mesh_object = model.generate()

    reopened = MeshGenerateModel.from_generated_mesh(mesh_object)
    updated_mask = np.ones((6, 6), dtype=bool)
    updated_mask[3:, :] = False
    reopened.set_mask("x", updated_mask)
    rebuilt = reopened.generate()

    assert rebuilt.mesh_data.n_points > 0


def test_edit_generation_rebuilds_from_the_held_grid():
    held_grid = np.zeros((3, 3, 3), dtype=float)
    held_grid[1:, :, :] = 1.0
    mesh_object = GeneratedMesh("Held Grid", grid_data=held_grid)

    model = MeshGenerateModel.from_generated_mesh(mesh_object)
    rebuilt = MeshGenerateTask(model)._build_grid_data((3, 3, 3))

    np.testing.assert_array_equal(rebuilt, held_grid)


def test_edit_generation_noise_changes_the_held_grid():
    held_grid = np.zeros((4, 4, 4), dtype=float)
    held_grid[1:, :, :] = 1.0
    mesh_object = GeneratedMesh("Held Grid", grid_data=held_grid)
    model = MeshGenerateModel.from_generated_mesh(mesh_object)
    model.noise_enabled = True
    model.perlin_noise_transform = _perlin_transform()

    rebuilt = MeshGenerateTask(model)._build_grid_data((4, 4, 4))

    assert not np.array_equal(rebuilt, held_grid)


def test_edit_generation_clears_removed_perlin_transform():
    model = MeshGenerateModel(
        grid_size=(3, 3, 3),
        noise_enabled=True,
        perlin_noise_transform=None,
    )
    block = GeneratedMeshBlockObject(
        grid_data=np.ones((3, 3, 3)),
        perlin_noise_transform=_perlin_transform().block_object,
        noise_enabled=True,
    )

    generated_task = GeneratedMeshTask(model, block)
    generated_task.execute(generated_task.prepare())

    assert block.perlin_noise_transform is None
    assert block.noise_enabled is False


def test_mesh_edit_model_updates_existing_mesh(qapp):
    mesh_object = MeshImportModel(
        name="Original",
        comments="old",
        mesh_data=object(),
    ).to_mesh_object()
    model = MeshEditModel.from_mesh_object(mesh_object)
    model.name = "Edited"
    model.comments = "new"
    model.scale = (2.0, 2.0, 2.0)

    assert model.apply() is mesh_object
    assert mesh_object.name == "Edited"
    assert mesh_object.comments == "new"
    assert mesh_object.scale == (2.0, 2.0, 2.0)
    assert mesh_object.node.name == "Edited"


def test_object_base_registers_as_global_root_by_default(qapp):
    object_base = ObjectBase("Root Object")

    assert object_base.node in root_objects.get_nodes()
    assert object_base.node.parent is None


def test_mesh_import_creates_mesh_object_as_child_only(qapp):
    mesh_object = MeshImportModel(
        name="Imported Mesh",
        guid="mesh-guid",
        comments="test mesh",
        mesh_data=object(),
    ).to_mesh_object()

    mesh_root.add_child(mesh_object.node)

    assert isinstance(mesh_object, MeshObject)
    assert mesh_object.node not in root_objects.get_nodes()
    assert mesh_object.node.parent is mesh_root
    assert mesh_root.children == [mesh_object.node]
    assert mesh_object.guid == "mesh-guid"
    assert mesh_object.visible is False
    assert mesh_object.comments == "test mesh"
    assert mesh_object.metadata["comments"] == "test mesh"
    assert isinstance(mesh_object.mesh_block_object, MeshBlockObject)
    assert mesh_object.mesh_block_object.mesh_data is mesh_object.mesh_data


def test_mesh_import_block_is_a_factory():
    import_task = MeshImportTask(
        MeshImportModel(name="Imported Mesh", guid="mesh-guid")
    )

    assert not isinstance(import_task, MeshBlockObject)


def test_tree_and_table_read_mesh_identity_from_block(qapp):
    table_manager = TableManager()
    table_model = TableModel(table_manager)
    mesh_object = MeshImportModel(
        name="Initial name",
        guid="initial-guid",
        mesh_data=object(),
    ).to_mesh_object()
    mesh_root.add_child(mesh_object.node)
    mesh_object.add_to_table(table_manager)
    tree_model = TreeModel(root_objects.get_nodes())

    mesh_object.block_object.name = "Block name"
    mesh_object.block_object.guid = "block-guid"

    root_index = tree_model.index(root_objects.get_nodes().index(mesh_root), 0)
    mesh_index = tree_model.index(0, 0, root_index)
    assert tree_model.data(mesh_index, Qt.DisplayRole) == "Block name"
    assert (
        table_model.data(
            table_model.index(0, table_model.NAME),
            Qt.DisplayRole,
        )
        == "Block name"
    )
    assert mesh_object.name == "Block name"
    assert mesh_object.guid == "block-guid"


def test_object_base_registers_table_data(qapp):
    table_manager = TableManager()
    object_base = ViewableTestObject("Table Object")

    object_base.add_to_table(table_manager)

    assert table_manager.get_data() == [object_base.row_data]
    assert table_manager.get_data()[0].name == "Table Object"


def test_table_model_exposes_rows_added_after_view_creation(qapp):
    table_manager = TableManager()
    table_model = TableModel(table_manager)
    object_base = ViewableTestObject("Live Row")

    table_model.add_row(object_base.row_data)

    assert table_model.rowCount() == 1
    assert (
        table_model.data(
            table_model.index(0, table_model.NAME),
            Qt.DisplayRole,
        )
        == "Live Row"
    )


def test_table_visibility_controls_scene_actor(qapp):
    class FakeScene:
        def __init__(self):
            self.visibility_changes = []

        def add_object(self, object_base):
            pass

        def set_object_visibility(self, object_base, visible):
            self.visibility_changes.append((object_base, visible))

    table_manager = TableManager()
    table_model = TableModel(table_manager)
    object_base = ViewableTestObject("Visible Row")
    scene = FakeScene()
    object_base.add_to_scene(scene)
    table_model.add_row(object_base.row_data)

    visible_index = table_model.index(0, table_model.VISIBLE)
    assert table_model.setData(
        visible_index, Qt.CheckState.Unchecked, Qt.CheckStateRole
    )
    assert object_base.visible is False
    assert scene.visibility_changes == [(object_base, False)]

    assert table_model.setData(visible_index, 2, Qt.CheckStateRole)
    assert object_base.visible is True
    assert scene.visibility_changes == [
        (object_base, False),
        (object_base, True),
    ]


def test_shape_controller_attaches_table_interface_and_owns_shapes():
    class FakeScene:
        def __init__(self):
            self.added = []
            self.removed = []

        def add_shape(self, object_base, shape):
            self.added.append((object_base, shape))

        def remove_shape(self, object_base, shape):
            self.removed.append((object_base, shape))
            return True

    class FakeTable:
        def __init__(self):
            self.refreshed = []

        def refresh_object(self, object_base):
            self.refreshed.append(object_base)

    object_base = ViewableTestObject("Shape owner")
    scene = FakeScene()
    table = FakeTable()
    table_model = TableModel(TableManager())
    table_model.add_row(object_base.row_data)
    controller = ShapeController(scene, table)
    controller.attach(object_base)

    shape = object_base.shape_interface.add_line([(0, 0, 0), (1, 0, 0)])

    assert TableModel.Headers[TableModel.SHAPES] == "Shapes"
    assert (
        table_model.data(
            table_model.index(0, TableModel.SHAPES),
            Qt.DisplayRole,
        )
        is object_base.shape_interface
    )
    assert object_base.row_data.other is object_base.shape_interface
    assert object_base.shape_interface.shapes == (shape,)
    assert str(object_base.shape_interface) == "Shapes (1)"
    assert scene.added == [(object_base, shape)]
    assert table.refreshed == [object_base]

    object_base.shape_interface.clear()
    assert scene.removed == [(object_base, shape)]


def test_island_registers_orbit_shape_with_orbit_icon_button(qapp):
    import pyvista as pv

    from components.tree import TreeManager
    from engine.block_objects import (
        IslandBlockObject,
        MeshBlockObject,
        WorldConfigBlockObject,
    )
    from objects.island import Island

    class FakeScene:
        def add_object(self, object_base):
            del object_base

        def add_shape(self, object_base, shape):
            del object_base, shape

        def set_shape_visibility(self, object_base, shape, visible):
            del object_base, shape, visible
            return True

        def remove_shape(self, object_base, shape):
            del object_base, shape
            return True

        def remove_object(self, object_base):
            del object_base
            return True

    table_manager = TableManager()
    table_model = TableModel(table_manager)
    scene = FakeScene()
    importer = ObjectImporterModel(
        table_model=table_model,
        tree_manager=TreeManager(),
        scene_viewer=scene,
    )
    island = Island(
        block_object=IslandBlockObject(
            mesh_block=MeshBlockObject(mesh_data=pv.Sphere()),
            world_config=WorldConfigBlockObject(),
            core_offset=5.0,
        )
    )
    island.block_object.commit(
        island.block_object.process(island.block_object.prepare())
    )
    importer.register(island)
    table = TableView(table_manager=table_manager)

    button = table.indexWidget(table.model().index(0, table.model().SHAPES))
    assert button is not None
    assert not button.icon().isNull()
    assert button.isChecked()
    button.click()
    assert island.orbit_shape.visible is False

    island.destroy()
    table.close()


def test_scene_uses_unique_actor_names_for_multiple_islands():
    import pyvista as pv

    from components.scene.view import SceneViewer
    from engine.block_objects import (
        IslandBlockObject,
        MeshBlockObject,
        WorldConfigBlockObject,
    )
    from objects.island import Island

    class FakeActor:
        def SetVisibility(self, visible):
            self.visible = visible

    class FakePlotter:
        def __init__(self):
            self.names = []

        def add_mesh(self, payload, name, **kwargs):
            del payload, kwargs
            self.names.append(name)
            return FakeActor()

    viewer = SceneViewer.__new__(SceneViewer)
    viewer.plotter = FakePlotter()
    viewer.scene_model = SimpleNamespace(add_object=lambda object_base: None)
    viewer.reset_camera = lambda: None
    viewer._actors = {}

    islands = []
    for angle in (0.0, 90.0):
        block = IslandBlockObject(
            mesh_block=MeshBlockObject(mesh_data=pv.Sphere()),
            world_config=WorldConfigBlockObject(),
            core_offset=5.0,
            orbit_angle=angle,
        )
        block.commit(block.process(block.prepare()))
        islands.append(Island(block_object=block))

    viewer.add_object(islands[0])
    viewer.add_object(islands[1])

    assert len(set(viewer.plotter.names)) == 2


def test_table_remove_unloads_object_but_keeps_tree_node(qapp):
    class FakeScene:
        def __init__(self):
            self.objects = []
            self.scene_model = SimpleNamespace(objects=self.objects)

        def add_object(self, object_base):
            self.objects.append(object_base)

        def remove_object(self, object_base):
            self.objects.remove(object_base)
            return True

    table_manager = TableManager()
    table_model = TableModel(table_manager)
    object_base = ViewableTestObject("Removable")
    scene = FakeScene()
    object_base.add_to_scene(scene)
    object_base.add_to_table(table_manager)
    assert scene.objects == [object_base]

    assert table_model.remove_row(0) is True
    assert table_model.rowCount() == 0
    assert scene.objects == []
    assert object_base.node in root_objects.get_nodes()


def test_island_delete_refreshes_tree_model_after_removal():
    class FakeTreeModel:
        def __init__(self):
            self.refresh_count = 0

        def refresh(self):
            self.refresh_count += 1

    class FakeTreeView:
        def __init__(self, model):
            self._model = model

        def model(self):
            return self._model

    class FakeImporter:
        def confirm_remove(self, object_base, parent=None):
            return True

        def remove(self, object_base):
            island_root.remove_child(object_base.node)
            return object_base

    object_base = ObjectBase("Island", auto_register_root=False)
    island_root.add_child(object_base.node)
    model = FakeTreeModel()
    controller = IslandController(
        object_importer=FakeImporter(),
        tree_view=FakeTreeView(model),
    )

    try:
        assert controller.delete(object_base) is object_base
        assert object_base.node not in island_root.children
        assert model.refresh_count == 1
    finally:
        object_base.remove_from_tree()


def test_island_controller_binds_loaded_island_regeneration_task():
    queued = []
    source = MeshBlockObject(mesh_data=pv.Sphere())
    island = Island(
        block_object=IslandBlockObject(
            mesh_block=source,
            world_config=world_config.block_object,
        ),
        auto_register_root=False,
    )
    runner = SimpleNamespace(
        enqueue_block_task=lambda name, task, on_finished=None: queued.append(
            (name, task, on_finished)
        )
    )
    controller = IslandController(
        object_importer=SimpleNamespace(),
        tree_view=SimpleNamespace(model=lambda: None),
        engine_runner=runner,
    )

    controller.bind_loaded_tasks([island])

    assert len(queued) == 1
    assert isinstance(queued[0][1], IslandTask)


def test_show_mesh_restores_scene_and_table_pipeline(qapp):
    class FakeScene:
        def __init__(self):
            self.objects = []
            self.scene_model = SimpleNamespace(objects=self.objects)

        def add_object(self, object_base):
            self.objects.append(object_base)

        def remove_object(self, object_base):
            self.objects.remove(object_base)
            return True

        def set_object_visibility(self, object_base, visible):
            pass

    table_manager = TableManager()
    table_model = TableModel(table_manager)
    scene = FakeScene()
    controller = MeshImportController(
        object_importer=ObjectImporterModel(
            table_model=table_model,
            tree_manager=SimpleNamespace(),
            scene_viewer=scene,
        ),
        tree_view=SimpleNamespace(),
    )
    mesh_object = MeshObject("Deferred Mesh", mesh_data=object())

    controller.show_mesh(mesh_object)

    assert scene.objects == [mesh_object]
    assert table_manager.get_data() == [mesh_object.row_data]
    assert mesh_object.visible is True


def test_delete_mesh_removes_scene_table_and_tree_membership(qapp):
    class FakeScene:
        def __init__(self):
            self.objects = []
            self.scene_model = SimpleNamespace(objects=self.objects)

        def add_object(self, object_base):
            self.objects.append(object_base)

        def remove_object(self, object_base):
            self.objects.remove(object_base)
            return True

        def set_object_visibility(self, object_base, visible):
            pass

    table_manager = TableManager()
    table_model = TableModel(table_manager)
    scene = FakeScene()
    mesh_object = MeshObject("Delete Me", mesh_data=object())
    mesh_root.add_child(mesh_object.node)
    mesh_object.add_to_scene(scene)
    table_model.add_row(mesh_object.row_data)
    tree_model = TreeModel([mesh_root])
    controller = MeshImportController(
        object_importer=ObjectImporterModel(
            table_model=table_model,
            tree_manager=SimpleNamespace(),
            scene_viewer=scene,
        ),
        tree_view=SimpleNamespace(model=lambda: tree_model),
    )

    controller.delete_mesh(mesh_object)

    assert table_manager.get_data() == []
    assert scene.objects == []
    assert mesh_object.node not in mesh_root.children
