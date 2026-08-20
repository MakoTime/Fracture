from dataclasses import dataclass, field
from pathlib import Path
import shutil
from typing import Any
from uuid import uuid4

import pyvista as pv

from .base_block_object import BlockObject


@dataclass
class MeshBlockObject(BlockObject):
    """Engine-owned mesh payload used by a mesh object."""

    mesh_data: Any = None
    name: str = "Mesh"
    guid: str = field(default_factory=lambda: str(uuid4()))
    comments: str = ""
    serialised_path: Path | None = field(default=None, repr=False, compare=False)
    def __post_init__(self):
        BlockObject.__init__(self, self.name, self.guid, self.comments)

    BITMAP_EXTENSIONS = {".bmp", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}

    def prepare(self):
        if self.mesh_data is None:
            raise ValueError("Mesh block has no mesh data")
        return self

    def process(self, progress_callback=None):
        self.prepare()
        if progress_callback:
            progress_callback(1.0)
        return self

    def serialise(self, path):
        """Save the processed mesh payload to a project block-data file."""
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        if self.mesh_data is None:
            if self.serialised_path is None or not self.serialised_path.exists():
                raise ValueError("Cannot save an unprocessed mesh block")
            if self.serialised_path.resolve() != output.resolve():
                shutil.copy2(self.serialised_path, output)
        else:
            self.mesh_data.save(str(output))
        self.serialised_path = output
        return output

    save = serialise

    def serialise_to_directory(self, directory):
        """Save this block using the payload format already in use."""
        if self.mesh_data is not None:
            suffix = ".vts" if isinstance(self.mesh_data, pv.StructuredGrid) else ".vtp"
        elif self.serialised_path is not None:
            suffix = self.serialised_path.suffix
        else:
            raise ValueError("Cannot save an unprocessed mesh block")
        return self.serialise(Path(directory) / f"{self.guid}{suffix}")

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        name: str = "Mesh",
        guid: str | None = None,
        comments: str = "",
        load_data: bool = True,
    ):
        """Load a mesh payload from a project block-data file."""
        payload_path = Path(path)
        return cls(
            mesh_data=pv.read(str(payload_path)) if load_data else None,
            name=name,
            guid=guid,
            comments=comments,
            serialised_path=payload_path,
        )


    @property
    def scene_data(self):
        """Return the renderable dataset held by this block."""
        if self.mesh_data is None:
            if self.serialised_path is None:
                raise ValueError("Mesh block has no serialised payload")
            self.mesh_data = pv.read(str(self.serialised_path))
        return self.mesh_data

    def release(self):
        """Release the in-memory payload while retaining its disk location."""
        if self.serialised_path is None:
            raise ValueError("Cannot release a mesh block without a serialised payload")
        self.mesh_data = None
