from typing import Optional

from PySide6.QtWidgets import QWidget

from .model import MeshProceduralModel
from .view import MeshProceduralView


def create_mesh_procedural_dialog(
	model: Optional[MeshProceduralModel] = None,
	parent: Optional[QWidget] = None,
	on_apply=None,
	on_close=None,
	tree_search=None,
	transforms=(),
	deduper=None,
) -> MeshProceduralView:
	"""Build the procedural mesh workspace with its editor dependencies."""
	return MeshProceduralView(
		model=model or MeshProceduralModel(),
		parent=parent,
		on_apply=on_apply,
		on_close=on_close,
		tree_search=tree_search,
		transforms=transforms,
		deduper=deduper or (lambda name: name),
	)
