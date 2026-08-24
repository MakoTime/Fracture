import numpy as np
import pytest

from engine.block_objects import (
    MeshBlockObject,
    PerlinNoiseTransformBlockObject,
    TransformBlockObject,
)
from objects.perlin_noise_transform import PerlinNoiseTransformObject
from objects.transform import TransformObject


def test_transform_block_is_an_abstract_contract():
    with pytest.raises(TypeError):
        TransformBlockObject()


def test_perlin_transform_is_deterministic_and_preserves_input():
    values = np.ones((6, 6, 6), dtype=float)
    transform = PerlinNoiseTransformBlockObject(seed=7)

    transformed = transform.apply(values)

    assert transformed.shape == values.shape
    np.testing.assert_array_equal(values, np.ones((6, 6, 6)))
    np.testing.assert_array_equal(transformed, transform.apply(values))
    assert not np.array_equal(transformed, values)


def test_perlin_process_calculates_transformed_values():
    values = np.ones((3, 3, 3), dtype=float)
    transform = PerlinNoiseTransformBlockObject(seed=7)

    processed = transform.calculate_values(values)

    np.testing.assert_array_equal(processed, transform.apply(values))
    assert transform.is_valid()


def test_perlin_process_calculates_noise_field():
    transform = PerlinNoiseTransformBlockObject(seed=7)

    processed = transform.calculate_field((3, 4, 5))

    assert processed.shape == (3, 4, 5)
    np.testing.assert_array_equal(processed, transform.noise_field((3, 4, 5)))


def test_perlin_transform_supports_multiple_frequency_bands():
    values = np.ones((8, 8, 8), dtype=float)
    single = PerlinNoiseTransformBlockObject(
        frequencies=(2,), amplitudes=(1.0,), seed=3
    )
    multiple = PerlinNoiseTransformBlockObject(
        frequencies=(2, 7), amplitudes=(1.0, 0.25), seed=3
    )

    assert not np.array_equal(single.apply(values), multiple.apply(values))


def test_perlin_transform_validates_frequency_bands():
    with pytest.raises(ValueError):
        PerlinNoiseTransformBlockObject(frequencies=(2,), amplitudes=(1.0, 0.5))
    with pytest.raises(ValueError):
        PerlinNoiseTransformBlockObject(frequencies=(0,), amplitudes=(1.0,))


def test_transform_object_wraps_transform_block():
    block = PerlinNoiseTransformBlockObject()
    transform = TransformObject("Transform", block)

    assert transform.block_object is block
    assert transform.apply(np.ones((2, 2, 2))).shape == (2, 2, 2)


def test_mesh_scene_data_load_is_owned_by_process(tmp_path):
    import pyvista as pv

    path = tmp_path / "mesh.vtp"
    pv.Sphere().save(path)
    block = MeshBlockObject.load(path, load_data=False)

    assert block.mesh_data is None
    prepared = block.prepare()
    processed = block.execute(prepared, load_payload=True)

    assert processed is block
    assert block.mesh_data is not None


def test_perlin_transform_object_creates_specialized_block():
    transform = PerlinNoiseTransformObject()

    assert isinstance(transform, TransformObject)
    assert isinstance(transform.block_object, PerlinNoiseTransformBlockObject)
