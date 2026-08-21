from engine import EngineRunner, EngineTaskModel, TaskStatus
from engine.block_objects import BlockObject
from engine.block_tasks import PerlinNoiseTransformTask
from engine.block_objects import PerlinNoiseTransformBlockObject


class DummyBlockObject(BlockObject):
    def prepare(self):
        return self

    def process(self, progress_callback=None):
        return self

    def serialise(self, path):
        return path


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
        return self.block_object


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


def test_destroyed_dependent_child_destroys_parent():
    child = DummyBlockObject(name="Child")
    parent = DummyBlockObject(name="Parent")
    parent.add_child_block_object(child, dependent=True)

    child.destroy()

    assert child.is_destroyed()
    assert parent.is_destroyed()


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
