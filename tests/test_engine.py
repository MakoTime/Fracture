from engine import EngineRunner, EngineTaskModel, TaskStatus


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
