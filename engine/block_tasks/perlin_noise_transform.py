class PerlinNoiseTransformTask:
    """Prepare a Perlin transform block for the engine task pipeline."""

    def __init__(self, block_object):
        self.block_object = block_object

    def prepare(self):
        return self.block_object.prepare()

    def process(self, prepared, progress_callback=None):
        self.block_object.validate()
        if progress_callback:
            progress_callback(1.0)
        return self.block_object