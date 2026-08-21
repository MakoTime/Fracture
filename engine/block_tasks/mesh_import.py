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

    def prepare(self):
        return {
            "source_path": self.model.source_path,
            "scale": self.model.scale,
            "rotation": self.model.rotation,
            "offset": self.model.offset,
            "low_threshold": self.model.low_threshold,
            "high_threshold": self.model.high_threshold,
            "vertical_scale": self.model.vertical_scale,
        }

    def process(self, prepared, progress_callback=None):
        return self.execute(prepared, progress_callback)

    def execute(self, prepared, progress_callback=None):
        report = progress_callback or (lambda progress: None)
        report(0.0)
        if Path(prepared["source_path"]).suffix.lower() in self.BITMAP_EXTENSIONS:
            mesh = self._load_bitmap(prepared, report)
        else:
            mesh = pv.read(prepared["source_path"])
            report(0.65)
        mesh.scale(prepared["scale"], inplace=True)
        report(0.75)
        mesh.rotate_x(prepared["rotation"][0], inplace=True)
        mesh.rotate_y(prepared["rotation"][1], inplace=True)
        mesh.rotate_z(prepared["rotation"][2], inplace=True)
        report(0.9)
        mesh.translate(prepared["offset"], inplace=True)
        self.block_object.set_mesh_data(mesh)
        self.block_object.commit()
        report(1.0)
        return self.block_object

    def _load_bitmap(self, prepared, progress_callback):
        image = QImage(prepared["source_path"])
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
            prepared["low_threshold"],
            prepared["high_threshold"],
        )
        elevations *= prepared["vertical_scale"]
        x_coordinates, y_coordinates = np.meshgrid(
            np.arange(width, dtype=float),
            np.arange(height, dtype=float),
            indexing="ij",
        )
        return pv.StructuredGrid(x_coordinates, y_coordinates, elevations.T)