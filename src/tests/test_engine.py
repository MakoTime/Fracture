import numpy as np
import pyvista as pv

from src.dialog.mesh_filter import MeshFilterModel
from src.dialog.mesh_generate import MeshGenerateModel
from src.dialog.perlin_noise_transform import PerlinNoiseTransformModel
from src.engine import EngineRunner, EngineTaskModel, TaskStatus
from src.engine.block_objects import (
    BlockObject,
    ColourmapBlockObject,
    GeneratedMeshBlockObject,
    IslandBlockObject,
    MeshBlockObject,
    PerlinNoiseTransformBlockObject,
    WorldConfigBlockObject,
)
from src.engine.block_tasks import (
    GeneratedMeshTask,
    IslandTask,
    MeshFilterTask,
    PerlinNoiseTransformTask,
)
from src.engine.block_tasks.island import _orbit_frame, build_island_mesh
from src.objects.island import Island


class DummyBlockObject(BlockObject):
    def prepare(self):
        return self

    def process(self, prepared, progress_callback=None):
        self.validate()
        return self

    def serialise(self, path):
        return path

    def serialise_to_directory(self, directory):
        return directory


class DummyBlockTask:
    def __init__(self, block_object, label=None, order=None):
        self.block_object = block_object
        self.process_count = 0
        self.label = label
        self.order = order

    def prepare(self):
        return self.block_object.prepare()

    def process(self, prepared, progress_callback=None):
        self.process_count += 1
        if self.order is not None:
            self.order.append(self.label)
        self.block_object.validate()
        return self.block_object


class FailingBlockTask:
    def __init__(self, block_object):
        self.block_object = block_object
        self.process_count = 0

    def prepare(self):
        return self.block_object.prepare()

    def process(self, prepared, progress_callback=None):
        self.process_count += 1
        raise ValueError("permanent failure")


class ProgressBlockTask:
    def __init__(self, block_object):
        self.block_object = block_object

    def prepare(self):
        return self.block_object.prepare()

    def process(self, prepared, progress_callback=None):
        progress_callback(0.4)
        self.block_object.validate()


def test_island_uses_core_offset_and_orientation_to_derive_position():
    world_config = WorldConfigBlockObject(centre=(10.0, 20.0, 30.0))
    source = MeshBlockObject(mesh_data=pv.Sphere(radius=1.0))
    island = IslandBlockObject(
        mesh_block=source,
        world_config=world_config,
        core_offset=5.0,
        orbit_normal=(0.0, 0.0, 1.0),
        orbit_angle=90.0,
        curve_mesh=True,
    )

    task = IslandTask(island)
    result = task.process(task.prepare())
    island.commit(result)

    assert np.allclose(island.mesh_data.center, (10.0, 25.0, 30.0))
    assert island.prepare()["curve_mesh"] is True
    application_island = Island(block_object=island)
    assert application_island.core_offset == 5.0
    assert application_island.orbit_normal == (0.0, 0.0, 1.0)
    assert application_island.orbit_angle == 90.0
    assert application_island.curve_mesh is True
    assert (
        np.linalg.norm(np.asarray(island.mesh_data.center) - world_config.centre) == 5.0
    )

    world_config.update_configuration(centre=(0.0, 0.0, 0.0))
    assert not island.is_valid()


def test_island_exposes_source_mesh_colourmap_for_scene_rendering():
    colourmap = ColourmapBlockObject(name="Island colours")
    source = MeshBlockObject(
        mesh_data=pv.Plane(i_resolution=2, j_resolution=2),
        colourmap=colourmap,
    )
    source.set_colourmap_field_sources("normal_z", "elevation")
    source.set_colourmap_data_options(True, False)
    island = IslandBlockObject(mesh_block=source)

    assert island.colourmap is colourmap
    assert island.colourmap_field_sources == ("normal_z", "elevation")
    assert island.colourmap_field_inversions == (True, False)


def test_perlin_changes_invalidate_generated_mesh_and_dependent_island():
    transform = PerlinNoiseTransformBlockObject()
    source = GeneratedMeshBlockObject(
        mesh_data=pv.Plane(),
        perlin_noise_transform=transform,
    )
    island = IslandBlockObject(mesh_block=source)
    source.validate()
    island.validate()
    transform.validate()

    transform.mark_changed()

    assert not transform.is_valid()
    assert not source.is_valid()
    assert not island.is_valid()


def test_colourmap_perlin_changes_invalidate_dependent_island():
    transform = PerlinNoiseTransformBlockObject()
    colourmap = ColourmapBlockObject(perlin_noise_transform=transform)
    source = MeshBlockObject(
        mesh_data=pv.Plane(),
        colourmap=colourmap,
    )
    island = IslandBlockObject(mesh_block=source)
    source.validate()
    island.validate()
    transform.validate()
    colourmap.validate()

    transform.mark_changed()

    assert not source.is_valid()
    assert not island.is_valid()


def test_invalidation_reaches_parents_through_change_only_relationships():
    transform = PerlinNoiseTransformBlockObject()
    source = GeneratedMeshBlockObject(
        mesh_data=pv.Plane(),
        perlin_noise_transform=transform,
    )
    island = IslandBlockObject(mesh_block=source)
    source.validate()
    island.validate()
    transform.validate()

    transform.invalidate(force=True)

    assert not source.is_valid()
    assert not island.is_valid()


def test_island_radius_uses_orbit_normal_and_angle():
    world_config = WorldConfigBlockObject()
    source = MeshBlockObject(mesh_data=pv.Sphere(radius=1.0))

    cases = (
        (0.0, (10.0, 0.0, 0.0)),
        (90.0, (0.0, 10.0, 0.0)),
    )
    for orbit_angle, expected in cases:
        island = IslandBlockObject(
            mesh_block=source,
            world_config=world_config,
            core_offset=10.0,
            orbit_angle=orbit_angle,
        )
        result = IslandTask(island).process(island.prepare())
        assert np.allclose(result.center, expected)


def test_curved_island_mesh_follows_arc_at_core_radius():
    radius = 5.0
    source = pv.PolyData(
        np.array(
            [
                (-np.pi * radius / 2, 0.0, 0.0),
                (0.0, 0.0, 0.0),
                (np.pi * radius / 2, 0.0, 0.0),
            ]
        )
    )

    result = build_island_mesh(
        {
            "mesh_data": source,
            "centre": (0.0, 0.0, 0.0),
            "core_offset": radius,
            "orbit_normal": (0.0, 0.0, 1.0),
            "orbit_angle": 0.0,
            "curve_mesh": True,
        }
    )

    assert np.allclose(
        result.points,
        np.array(
            [
                (0.0, -radius, 0.0),
                (radius, 0.0, 0.0),
                (0.0, radius, 0.0),
            ]
        ),
    )


def test_curved_island_mesh_bends_both_surface_axes():
    radius = 5.0
    quarter_arc = np.pi * radius / 2
    source = pv.PolyData(
        np.array(
            [
                (-quarter_arc, 0.0, 0.0),
                (0.0, -quarter_arc, 0.0),
                (0.0, 0.0, 0.0),
                (0.0, quarter_arc, 0.0),
                (quarter_arc, 0.0, 0.0),
            ]
        )
    )

    result = build_island_mesh(
        {
            "mesh_data": source,
            "centre": (0.0, 0.0, 0.0),
            "core_offset": radius,
            "orbit_normal": (0.0, 0.0, 1.0),
            "orbit_angle": 0.0,
            "curve_mesh": True,
        }
    )

    assert np.allclose(
        result.points,
        np.array(
            [
                (0.0, -radius, 0.0),
                (0.0, 0.0, -radius),
                (radius, 0.0, 0.0),
                (0.0, 0.0, radius),
                (0.0, radius, 0.0),
            ]
        ),
    )


def test_curve_mesh_does_not_bend_at_zero_core_radius():
    source = pv.PolyData(np.array([(-1.0, 0.0, 0.0), (1.0, 0.0, 0.0)]))

    prepared = {
        "mesh_data": source,
        "centre": (0.0, 0.0, 0.0),
        "core_offset": 0.0,
        "orbit_normal": (0.0, 0.0, 1.0),
    }
    result = build_island_mesh(
        {
            **prepared,
            "curve_mesh": True,
        }
    )
    uncurved = build_island_mesh(prepared)

    assert np.allclose(result.points, uncurved.points)


def test_island_orbit_speed_advances_angle_without_changing_radius():
    island = IslandBlockObject(orbit_speed=15.0, orbit_angle=20.0)

    assert island.orbit_angle_at_time(0.0) == 20.0
    assert island.orbit_angle_at_time(4.0) == 80.0


def test_island_orbit_transform_moves_baked_mesh_without_rebuilding_it():
    world_config = WorldConfigBlockObject(centre=(2.0, 3.0, 4.0))
    source = MeshBlockObject(mesh_data=pv.Sphere(radius=1.0))
    island = IslandBlockObject(
        mesh_block=source,
        world_config=world_config,
        core_offset=5.0,
        orbit_normal=(0.0, 0.0, 1.0),
        orbit_angle=90.0,
        orbit_speed=30.0,
    )
    island.commit(IslandTask(island).process(island.prepare()))
    initial_points = np.asarray(island.mesh_data.points).copy()

    transform = island.orbit_transform_at_time(3.0)
    homogeneous_points = np.column_stack(
        (np.asarray(island.mesh_data.points), np.ones(island.mesh_data.n_points))
    )
    transformed_points = (transform @ homogeneous_points.T).T[:, :3]
    expected_radial, _, _ = _orbit_frame(island.orbit_normal, 180.0)

    assert np.allclose(
        transformed_points.mean(axis=0), world_config.centre + 5.0 * expected_radial
    )
    assert np.allclose(island.mesh_data.points, initial_points)


def test_island_orbit_normal_is_normalized_and_controls_angle_motion():
    island = IslandBlockObject(
        orbit_normal=(0.0, 0.0, 2.0),
        orbit_angle=10.0,
        orbit_speed=15.0,
    )

    assert island.orbit_normal == (0.0, 0.0, 1.0)
    assert island.orbit_angle_at_time(4.0) == 70.0


def test_island_orbit_frame_is_orthonormal_at_both_poles():
    for orbit_angle in (0.0, 180.0, 360.0):
        radial, tangent, local_up = _orbit_frame(np.array((0.0, 1.0, 0.0)), orbit_angle)

        assert np.isclose(np.linalg.norm(radial), 1.0)
        assert np.isclose(np.linalg.norm(tangent), 1.0)
        assert np.isclose(np.linalg.norm(local_up), 1.0)
        assert np.isclose(np.dot(radial, tangent), 0.0)
        assert np.isclose(np.dot(radial, local_up), 0.0)
        assert np.isclose(np.dot(tangent, local_up), 0.0)


def test_island_mesh_local_up_follows_radial_direction_at_poles():
    source = pv.PolyData(
        np.array(
            [
                (-1.0, 0.0, 0.0),
                (1.0, 0.0, 0.0),
                (0.0, -1.0, 0.0),
                (0.0, 1.0, 0.0),
                (0.0, 0.0, -1.0),
                (0.0, 0.0, 1.0),
            ]
        )
    )
    for orbit_angle, expected in ((0.0, (0.0, 0.0, 5.0)), (180.0, (0.0, 0.0, -5.0))):
        result = build_island_mesh(
            {
                "mesh_data": source,
                "centre": (0.0, 0.0, 0.0),
                "core_offset": 5.0,
                "orbit_normal": (0.0, 1.0, 0.0),
                "orbit_angle": orbit_angle,
            }
        )

        assert np.allclose(result.center, expected)
        local_up = np.asarray(result.points[5] - result.center)
        local_up /= np.linalg.norm(local_up)
        assert np.allclose(local_up, np.asarray(expected) / 5.0)


def _drain_engine(model, qapp, cycles=5):
    for _ in range(cycles):
        assert model.wait_for_done()
        qapp.processEvents()


def test_engine_task_waits_when_explicitly_paused(qapp):
    completed = []
    model = EngineTaskModel()
    model.pause()
    task = model.enqueue("Bitmap import", lambda: completed.append(True))

    assert task.status is TaskStatus.QUEUED
    assert completed == []

    model.play()
    assert model.wait_for_done()
    qapp.processEvents()

    assert completed == [True]
    assert task.status is TaskStatus.COMPLETED
    assert task.progress == 1.0


def test_engine_task_model_plays_by_default(qapp):
    model = EngineTaskModel()
    completed = []

    model.enqueue("Immediate task", lambda: completed.append(True))
    assert model.wait_for_done()
    qapp.processEvents()

    assert model.paused is False
    assert completed == [True]


def test_engine_runner_starts_in_play_state(qapp):
    runner = EngineRunner()

    assert runner.task_model.paused is False
    assert runner.state_label.text() == "Running"


def test_engine_runner_displays_task_status(qapp):
    runner = EngineRunner()
    runner.enqueue_task("Mesh build", lambda: None)

    assert runner.task_table.rowCount() == 1
    assert runner.task_table.item(0, 1).text() == "Queued"

    runner.play()
    assert runner.task_model.wait_for_done()
    qapp.processEvents()

    assert runner.task_table.rowCount() == 0


def test_engine_task_reports_progress(qapp):
    model = EngineTaskModel()
    progress_values = []
    model.task_updated.connect(lambda task: progress_values.append(task.progress))

    def work(report):
        report(0.25)
        report(0.75)

    model.enqueue("Progressive task", work)
    model.play()
    assert model.wait_for_done()
    qapp.processEvents()

    assert 0.25 in progress_values
    assert 0.75 in progress_values
    assert progress_values[-1] == 1.0


def test_invalidated_block_is_reprocessed_by_task_model(qapp):
    model = EngineTaskModel()
    block_task = DummyBlockTask(DummyBlockObject())

    model.enqueue_block_task("Rebuild block", block_task)
    assert model.wait_for_done()
    qapp.processEvents()
    assert block_task.process_count == 1
    assert block_task.block_object.is_valid()

    block_task.block_object.invalidate()
    assert model.wait_for_done()
    qapp.processEvents()

    assert block_task.process_count == 2
    assert block_task.block_object.is_valid()


def test_failed_block_task_is_not_retried(qapp):
    model = EngineTaskModel()
    block_task = FailingBlockTask(DummyBlockObject())

    model.enqueue_block_task("Failing block", block_task)
    assert model.wait_for_done()
    qapp.processEvents()

    assert block_task.process_count == 1
    assert len(model.tasks) == 1
    assert model.tasks[0].status is TaskStatus.FAILED


def test_block_task_forwards_progress(qapp):
    model = EngineTaskModel()
    progress_values = []
    model.task_updated.connect(lambda task: progress_values.append(task.progress))

    model.enqueue_block_task("Progress block", ProgressBlockTask(DummyBlockObject()))
    assert model.wait_for_done()
    qapp.processEvents()

    assert 0.4 in progress_values
    assert progress_values[-1] == 1.0


def test_replacing_queued_block_task_uses_latest_task(qapp):
    model = EngineTaskModel()
    model.pause()
    block = DummyBlockObject()
    first = DummyBlockTask(block)
    second = DummyBlockTask(block)

    model.enqueue_block_task("First", first)
    model.enqueue_block_task("Second", second)
    model.play()
    assert model.wait_for_done()
    qapp.processEvents()

    assert first.process_count == 0
    assert second.process_count == 1


def test_mark_changed_propagates_change_callbacks_to_parents():
    child = DummyBlockObject(name="Child")
    parent = DummyBlockObject(name="Parent")
    parent.add_child_block_object(child)
    changes = []
    child.add_change_callback(lambda block: changes.append(block.name))
    parent.add_change_callback(lambda block: changes.append(block.name))

    child.mark_changed()

    assert changes == ["Child", "Parent"]
    assert not child.is_valid()
    assert not parent.is_valid()


def test_invalid_child_is_reprocessed_before_its_parent(qapp):
    model = EngineTaskModel()
    order = []
    child = DummyBlockObject(name="Child")
    parent = DummyBlockObject(name="Parent")
    parent.add_child_block_object(child)
    child_task = DummyBlockTask(child, label="child", order=order)
    parent_task = DummyBlockTask(parent, label="parent", order=order)

    model.enqueue_block_task("Child", child_task)
    model.enqueue_block_task("Parent", parent_task)
    assert model.wait_for_done()
    qapp.processEvents()
    order.clear()

    child.invalidate()
    for _ in range(3):
        assert model.wait_for_done()
        qapp.processEvents()

    assert order == ["child", "parent"]
    assert child.is_valid()
    assert parent.is_valid()


def test_two_input_parent_reprocesses_only_the_invalid_input(qapp):
    model = EngineTaskModel()
    order = []
    transform = DummyBlockObject(name="Transform")
    source = DummyBlockObject(name="Source")
    filtered = DummyBlockObject(name="Filtered")
    filtered.add_child_block_object(transform)
    filtered.add_child_block_object(source)
    transform_task = DummyBlockTask(transform, label="transform", order=order)
    source_task = DummyBlockTask(source, label="source", order=order)
    filtered_task = DummyBlockTask(filtered, label="filtered", order=order)

    model.enqueue_block_task("Transform", transform_task)
    model.enqueue_block_task("Source", source_task)
    model.enqueue_block_task("Filtered", filtered_task)
    _drain_engine(model, qapp)
    order.clear()

    transform.invalidate()
    _drain_engine(model, qapp)

    assert order == ["transform", "filtered"]
    assert transform_task.process_count == 2
    assert source_task.process_count == 1
    assert filtered_task.process_count == 2
    assert transform.is_valid()
    assert source.is_valid()
    assert filtered.is_valid()


def test_two_input_parent_reprocesses_source_without_reprocessing_transform(qapp):
    model = EngineTaskModel()
    order = []
    transform = DummyBlockObject(name="Transform")
    source = DummyBlockObject(name="Source")
    filtered = DummyBlockObject(name="Filtered")
    filtered.add_child_block_object(transform)
    filtered.add_child_block_object(source)
    transform_task = DummyBlockTask(transform, label="transform", order=order)
    source_task = DummyBlockTask(source, label="source", order=order)
    filtered_task = DummyBlockTask(filtered, label="filtered", order=order)

    model.enqueue_block_task("Transform", transform_task)
    model.enqueue_block_task("Source", source_task)
    model.enqueue_block_task("Filtered", filtered_task)
    _drain_engine(model, qapp)
    order.clear()

    source.invalidate()
    _drain_engine(model, qapp)

    assert order == ["source", "filtered"]
    assert transform_task.process_count == 1
    assert source_task.process_count == 2
    assert filtered_task.process_count == 2


def test_invalidation_while_paused_is_processed_once_after_resume(qapp):
    model = EngineTaskModel()
    block_task = DummyBlockTask(DummyBlockObject())
    model.pause()
    model.enqueue_block_task("Rebuild block", block_task)
    block_task.block_object.invalidate()

    model.play()
    _drain_engine(model, qapp)

    assert block_task.process_count == 2
    assert block_task.block_object.is_valid()


def test_generated_and_filter_tasks_complete_after_transform_invalidation(qapp):
    transform = PerlinNoiseTransformModel(frequencies=(2,)).to_object()
    generation = MeshGenerateModel(
        name="Source",
        grid_size=(5, 5, 5),
        noise_enabled=True,
        perlin_noise_transform=transform,
    )
    source = generation.generate()
    runner = EngineTaskModel()

    runner.enqueue_block_task(
        "Generate transform",
        PerlinNoiseTransformTask(transform.block_object),
    )
    runner.enqueue_block_task(
        "Regenerate source",
        GeneratedMeshTask(generation, source.mesh_block_object),
    )
    _drain_engine(runner, qapp)

    transform.block_object.invalidate(force=True)
    filter_model = MeshFilterModel.from_mesh(source)
    filter_model.perlin_noise_transform = transform
    filter_model.noise_enabled = True
    filtered = filter_model.generate()

    runner.enqueue_block_task(
        "Regenerate source after filter apply",
        GeneratedMeshTask(generation, source.mesh_block_object),
    )
    runner.enqueue_block_task(
        "Filter source",
        MeshFilterTask(
            source.mesh_block_object,
            transform.block_object,
            filter_model.noise_minimum,
            filter_model.noise_maximum,
            block_object=filtered.mesh_block_object,
        ),
    )
    _drain_engine(runner, qapp, cycles=8)

    assert all(task.status is TaskStatus.COMPLETED for task in runner.tasks)
    assert source.mesh_block_object.is_valid()
    assert filtered.mesh_block_object.is_valid()


def test_destroyed_child_without_task_binding_does_not_block_parent(qapp):
    model = EngineTaskModel()
    child = DummyBlockObject(name="Child")
    parent = DummyBlockObject(name="Parent")
    parent.add_child_block_object(child)
    child_task = DummyBlockTask(child)
    parent_task = DummyBlockTask(parent)

    model.enqueue_block_task("Child", child_task)
    model.enqueue_block_task("Parent", parent_task)
    assert model.wait_for_done()
    qapp.processEvents()

    model.remove_block_task(child)
    child.destroy()

    for _ in range(3):
        assert model.wait_for_done()
        qapp.processEvents()
    assert parent_task.process_count == 2
    assert parent.is_valid()


def test_invalid_child_without_task_binding_is_reported_immediately():
    model = EngineTaskModel()
    child = DummyBlockObject(name="Unregistered child")
    parent = DummyBlockObject(name="Parent")
    parent.add_child_block_object(child)
    child.invalidate()

    try:
        model.enqueue_block_task("Parent", DummyBlockTask(parent))
    except ValueError as error:
        assert "No block task is registered" in str(error)
    else:
        raise AssertionError("invalid unregistered children must not remain queued")


def test_destroyed_dependent_child_destroys_parent():
    child = DummyBlockObject(name="Child")
    parent = DummyBlockObject(name="Parent")
    parent.add_child_block_object(child, dependent=True)

    child.destroy()

    assert child.is_destroyed()
    assert parent.is_destroyed()


def test_invalidation_handles_dependency_cycles_once():
    first = DummyBlockObject(name="First")
    second = DummyBlockObject(name="Second")
    first.add_child_block_object(second)
    second.add_child_block_object(first)
    callbacks = []
    first.add_invalidation_callback(lambda block: callbacks.append(block.name))
    second.add_invalidation_callback(lambda block: callbacks.append(block.name))

    first.invalidate()

    assert callbacks == ["First", "Second"]


def test_destroyed_non_dependent_child_only_invalidates_parent():
    child = DummyBlockObject(name="Child")
    parent = DummyBlockObject(name="Parent")
    parent.add_child_block_object(child)

    child.destroy()

    assert child.is_destroyed()
    assert not parent.is_destroyed()
    assert not parent.is_valid()


def test_destroyed_block_destruction_is_idempotent():
    block = DummyBlockObject(name="Disposable")
    calls = []
    block.add_destruction_callback(lambda destroyed: calls.append(destroyed))

    assert block.destroy() is True
    assert block.destroy() is False
    assert calls == [block]


def test_perlin_block_task_is_visible_while_engine_is_paused(qapp):
    runner = EngineRunner()
    runner.pause()
    block = PerlinNoiseTransformBlockObject(guid="paused-perlin")

    task = runner.enqueue_block_task(
        "Generate Perlin Noise Transform",
        PerlinNoiseTransformTask(block),
    )

    assert task.status is TaskStatus.QUEUED
    assert runner.task_table.rowCount() == 1
    assert runner.task_table.item(0, 0).text() == "Generate Perlin Noise Transform"
