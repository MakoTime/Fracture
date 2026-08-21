from .mesh_generate import MeshGenerateTask


class GeneratedMeshTask:
    """Regenerate an existing generated-mesh block in place."""

    def __init__(self, model, block_object):
        self.model = model
        self.block_object = block_object

    def process(self, progress_callback=None):
        transform = self._perlin_noise_block()
        self.block_object.set_perlin_noise_transform(transform)
        if transform is not None:
            transform.process()
            transform.validate()
            self.model.perlin_noise_transform = transform
        generated = MeshGenerateTask(self.model).process(progress_callback)
        self.block_object.set_grid_data(generated.grid_data)
        self.block_object.mesh_data = generated.mesh_data
        self.block_object.mask_mesh_data = generated.mask_mesh_data
        self.block_object.noise_enabled = generated.noise_enabled
        self.block_object.set_perlin_noise_transform(
            generated.perlin_noise_transform
        )
        self.block_object.validate()
        return self.block_object

    def _perlin_noise_block(self):
        transform = getattr(self.model, "perlin_noise_transform", None)
        if transform is None:
            return None
        return getattr(transform, "block_object", transform)