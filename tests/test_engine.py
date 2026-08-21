from engine import EngineRunner, EngineTaskModel, TaskStatus
from engine.block_objects import BlockObject
from engine.block_tasks import PerlinNoiseTransformTask
from engine.block_objects import PerlinNoiseTransformBlockObject
from dialog.mesh_filter import MeshFilterModel
from dialog.mesh_generate import MeshGenerateModel
from dialog.perlin_noise_transform import PerlinNoiseTransformModel
from engine.block_tasks import GeneratedMeshTask, MeshFilterTask


class DummyBlockObject(BlockObject):
    def prepare(self):
        return self

    def process(self, progress_callback=None):
        self.prepare()
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

    def process(self):
        self.process_count += 1
        if self.order is not None:
            self.order.append(self.label)
        self.block_object.process()
        return self.block_object


class FailingBlockTask:
    def __init__(self, block_object):
        self.block_object = block_object
        self.process_count = 0

    def process(self, progress_callback=None):
        self.process_count += 1
        raise ValueError("permanent failure")


class ProgressBlockTask:
    def __init__(self, block_object):
        self.block_object = block_object

    def process(self, progress_callback=None):
        progress_callback(0.4)
        self.block_object.process(progress_callback)


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
            filter_model.noise_penetration,
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
