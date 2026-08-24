from engine.block_objects import PerlinNoiseTransformBlockObject

from .mesh_generate import MeshGenerateTask


class GeneratedMeshTask:
    """Regenerate an existing generated-mesh block in place."""

    def __init__(self, model, block_object):
        self.model = model
        self.block_object = block_object

    def prepare(self):
        return {
            "transform": self._perlin_noise_block(),
            "generation": MeshGenerateTask(self.model).prepare(),
        }

    def process(self, prepared, progress_callback=None):
        return self.execute(prepared, progress_callback)

    def execute(self, prepared, progress_callback=None):
        transform = prepared["transform"]
        self.block_object.set_perlin_noise_transform(transform)
        if transform is not None:
            self.model.perlin_noise_transform = transform
        generated_task = MeshGenerateTask(self.model)
        generated_task.execute(
            prepared["generation"],
            progress_callback,
        )
        self.block_object.set_grid_data(generated_task.grid_data)
        self.block_object.set_mesh_data(generated_task.block_object.mesh_data)
        self.block_object.set_mask_mesh_data(generated_task.block_object.mask_mesh_data)
        self.block_object.noise_enabled = generated_task.block_object.noise_enabled
        self.block_object.set_perlin_noise_transform(
            generated_task.block_object.perlin_noise_transform
        )
        self.block_object.commit()
        return self.block_object

    def _perlin_noise_block(self):
        transform = getattr(self.model, "perlin_noise_transform", None)
        if transform is None:
            return None
        if isinstance(transform, PerlinNoiseTransformBlockObject):
            candidate = transform
        elif hasattr(transform, "block_object"):
            candidate = transform.block_object
        else:
            candidate = transform.to_object().block_object
        current = self.block_object.perlin_noise_transform
        if current is not None and current.guid == candidate.guid:
            return current
        return candidate
