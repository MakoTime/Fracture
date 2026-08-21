from pathlib import Path

import numpy as np
import pyvista as pv
from PySide6.QtGui import QImage

from engine.block_objects import MeshBlockObject


class MeshImportTask:
    """Transient operation that creates a durable mesh block."""

    BITMAP_EXTENSIONS = {".bmp", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}

    def __init__(self, model):
        self.model = model
        self.block_object = MeshBlockObject(
            name=model.name,
            guid=model.guid,
            comments=model.comments,
        )

    def process(self, progress_callback=None):
        report = progress_callback or (lambda progress: None)
        report(0.0)
        if Path(self.model.source_path).suffix.lower() in self.BITMAP_EXTENSIONS:
            mesh = self._load_bitmap(report)
        else:
            mesh = pv.read(self.model.source_path)
            report(0.65)
        mesh.scale(self.model.scale, inplace=True)
        report(0.75)
        mesh.rotate_x(self.model.rotation[0], inplace=True)
        mesh.rotate_y(self.model.rotation[1], inplace=True)
        mesh.rotate_z(self.model.rotation[2], inplace=True)
        report(0.9)
        mesh.translate(self.model.offset, inplace=True)
        self.block_object.set_mesh_data(mesh)
        self.block_object.process()
        report(1.0)
        return self.block_object

    def _load_bitmap(self, progress_callback):
        image = QImage(self.model.source_path)
        if image.isNull():
            raise ValueError(
                f"Unable to load elevation bitmap: {self.model.source_path}"
            )
        grayscale = image.convertToFormat(QImage.Format.Format_Grayscale8)
        width, height = grayscale.width(), grayscale.height()
        rows = []
        for y in range(height):
            rows.append([grayscale.pixel(x, y) & 0xFF for x in range(width)])
            progress_callback(0.1 + 0.55 * ((y + 1) / height))
        elevations = np.asarray(rows, dtype=float)
        elevations = np.clip(
            elevations,
            self.model.low_threshold,
            self.model.high_threshold,
        )
        elevations *= self.model.vertical_scale
        x_coordinates, y_coordinates = np.meshgrid(
            np.arange(width, dtype=float),
            np.arange(height, dtype=float),
            indexing="ij",
        )
        return pv.StructuredGrid(x_coordinates, y_coordinates, elevations.T)