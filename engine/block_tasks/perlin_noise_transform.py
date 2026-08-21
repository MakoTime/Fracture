class PerlinNoiseTransformTask:
    """Prepare a Perlin transform block for the engine task pipeline."""

    def __init__(self, block_object):
        self.block_object = block_object

    def process(self, progress_callback=None):
        return self.block_object.process(progress_callback)