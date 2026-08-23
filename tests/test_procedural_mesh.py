import numpy as np

from dialog.mesh_procedural.model import MeshProceduralModel
from dialog.perlin_noise_transform import PerlinNoiseTransformModel
from engine import EngineTaskModel, TaskStatus
from engine.block_objects import ProceduralMeshBlock
from engine.block_tasks import ProceduralMeshTask
from objects.procedural_mesh import ProceduralMeshObject


def _model(**values):
    values.setdefault(
        "perlin_noise_transform",
        PerlinNoiseTransformModel(seed=17).to_object(),
    )
    values.setdefault("grid_size", (5, 5, 5))
    return MeshProceduralModel(**values)


def test_procedural_task_builds_deterministic_thresholded_scalar_grid():
    model = _model()
    first = ProceduralMeshTask(model)
    second = ProceduralMeshTask(model)

    first_result = first.process(first.prepare())
    second_result = second.process(second.prepare())

    np.testing.assert_array_equal(
        first_result["grid_data"], second_result["grid_data"]
    )
    np.testing.assert_array_equal(
        first_result["mesh_data"].points,
        second_result["mesh_data"].points,
    )
    assert first_result["grid_data"].size == 5 * 5 * 5
    assert first_result["mesh_data"].n_points > 0


def test_procedural_task_leaves_empty_space_without_transform():
    task = ProceduralMeshTask(MeshProceduralModel(grid_size=(2, 3, 4)))

    result = task.process(task.prepare())

    assert result["grid_data"].shape == (2, 3, 4)
    assert np.all(result["grid_data"] == 0.0)
    assert result["mesh_data"].n_points == 0


def test_procedural_model_shows_grid_by_default():
    assert MeshProceduralModel().show_grid is True


def test_procedural_thresholds_zero_values_outside_range():
    broad_task = ProceduralMeshTask(_model())
    broad = broad_task.process(broad_task.prepare())
    narrow_model = _model(lower_threshold=0.45, upper_threshold=0.55)
    narrow_task = ProceduralMeshTask(narrow_model)
    narrow = narrow_task.process(narrow_task.prepare())

    broad_values = broad["grid_data"]
    narrow_values = narrow["grid_data"]
    assert narrow_values.size == broad_values.size
    assert np.count_nonzero(narrow_values) < np.count_nonzero(broad_values)
    assert narrow["mesh_data"].n_points > 0


def test_procedural_model_creates_procedural_mesh_object():
    mesh = _model().generate()

    assert isinstance(mesh, ProceduralMeshObject)
    assert isinstance(mesh.mesh_block_object, ProceduralMeshBlock)
    assert mesh.grid_shape == (5, 5, 5)
    assert mesh.mesh_data.n_points > 0


def test_procedural_task_runner_commits_result(qapp):
    model = _model()
    task = ProceduralMeshTask(model)
    task.block_object.invalidate(force=True)
    runner = EngineTaskModel()
    finished = []

    runner.enqueue_block_task(
        "Generate procedural mesh",
        task,
        on_finished=finished.append,
    )
    assert runner.wait_for_done()
    qapp.processEvents()

    assert finished and finished[0].status is TaskStatus.COMPLETED
    assert task.block_object.is_valid()
    assert task.block_object.mesh_data.n_points > 0
