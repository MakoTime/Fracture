import json
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QFileDialog, QDialog, QTreeView, QWidget

from components.tree import TreeModel
from components.tree.roots import transform_root
from dialog.perlin_noise_transform import (
    PerlinNoiseTransformModel,
    create_perlin_noise_transform_dialog,
)
from engine.block_tasks import PerlinNoiseTransformTask
from objects.perlin_noise_transform import PerlinNoiseTransformObject
from tools.dropdown import create_dropdown_menu
from common.icons import get_icon


class TransformController:
    """Create, import, register, and remove transform objects."""

    def __init__(
        self,
        object_importer,
        tree_view: QTreeView,
        parent: Optional[QWidget] = None,
        engine_runner=None,
    ):
        self.object_importer = object_importer
        self.tree_view = tree_view
        self.parent = parent
        self.engine_runner = engine_runner
        if hasattr(tree_view, "add_context_menu_factory"):
            tree_view.add_context_menu_factory(self._create_context_menu_for_index)
        elif hasattr(tree_view, "set_context_menu_factory"):
            tree_view.set_context_menu_factory(self._create_context_menu_for_index)

    def _create_context_menu_for_index(self, index, parent):
        return self.create_context_menu(index.internalPointer(), parent)

    def create_perlin_noise_transform(self):
        dialog = create_perlin_noise_transform_dialog(parent=self.parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return self._register(dialog.update_model().to_object())

    def import_perlin_noise_transform(self):
        path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Import Perlin Noise Transform",
            "",
            "Transform JSON (*.json);;All files (*)",
        )
        if not path:
            return None
        try:
            with open(path, "r", encoding="utf-8") as stream:
                data = json.load(stream)
            if data.get("type") != "perlin_noise_transform":
                raise ValueError("unsupported transform type")
            from dialog.perlin_noise_transform import PerlinNoiseTransformModel

            model = PerlinNoiseTransformModel.from_json(data)
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            return None
        return self._register(model.to_object())

    def create_context_menu(self, node, parent=None):
        options = []
        if node is transform_root:
            options.extend(
                (
                    ("Create Perlin noise transform", self.create_perlin_noise_transform),
                    ("Import Perlin noise transform", self.import_perlin_noise_transform),
                )
            )
        elif isinstance(node.node_object, PerlinNoiseTransformObject):
            options.extend(
                (
                    ("Edit", lambda: self.edit(node.node_object)),
                    ("Delete", lambda: self.delete(node.node_object), get_icon("bin")),
                )
            )
        return create_dropdown_menu(options, parent)

    def edit(self, transform):
        block = transform.block_object
        model = PerlinNoiseTransformModel(
            name=transform.name,
            frequencies=block.frequencies,
            amplitudes=block.amplitudes,
            seed=block.seed,
            guid=transform.guid,
            curve_mode=block.curve_mode,
            curve_points=block.curve_points,
            curve_handles=block.curve_handles,
            frequency_start=block.frequency_start,
            frequency_end=block.frequency_end,
            sample_count=block.sample_count,
            manual_sampling=block.manual_sampling,
            preset=block.preset,
            preset_options=block.preset_options,
            application_mode=block.application_mode,
            penetration=block.penetration,
        )
        dialog = create_perlin_noise_transform_dialog(model, parent=self.parent)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        updated = dialog.update_model()
        block.update_configuration(
            **{
                field_name: getattr(updated, field_name)
                for field_name in (
                    "frequencies",
                    "amplitudes",
                    "seed",
                    "curve_mode",
                    "curve_points",
                    "curve_handles",
                    "frequency_start",
                    "frequency_end",
                    "sample_count",
                    "manual_sampling",
                    "preset",
                    "preset_options",
                    "application_mode",
                    "penetration",
                )
            }
        )
        transform._on_name_changed(updated.name.strip() or transform.name)
        self._enqueue_task(transform)
        self._refresh_and_select(transform)
        return transform

    def _register(self, transform):
        self.object_importer.register(
            transform,
            parent=transform_root,
            add_to_scene=False,
        )
        self._refresh_and_select(transform)
        self._enqueue_task(transform)
        return transform

    def _enqueue_task(self, transform):
        if self.engine_runner is None:
            return None
        task = PerlinNoiseTransformTask(transform.block_object)
        if hasattr(self.engine_runner, "task_model"):
            return self.engine_runner.enqueue_block_task(
                f"Generate {transform.name}",
                task,
                on_finished=lambda finished: self._finish_task(transform, finished),
            )
        return self.engine_runner.enqueue_block_task(f"Generate {transform.name}", task)

    def _finish_task(self, transform, task):
        if task.error:
            return
        self.object_importer.refresh_object(transform)

    def _remove_task(self, block):
        if self.engine_runner is not None and hasattr(
            self.engine_runner, "remove_block_task"
        ):
            return self.engine_runner.remove_block_task(block)
        return False

    def delete(self, transform):
        if not self.object_importer.confirm_remove(transform, self.parent):
            return None
        self._remove_task(transform.block_object)
        self.object_importer.remove(transform)
        self._refresh_and_select(None)
        return transform

    def _refresh_and_select(self, transform):
        tree_model = self.tree_view.model()
        if not isinstance(tree_model, TreeModel):
            return
        tree_model.refresh()
        if transform is None:
            return
        root_index = tree_model.index(
            tree_model.root_data.index(transform_root),
            0,
        )
        child_index = tree_model.index(
            transform_root.children.index(transform.node),
            0,
            root_index,
        )
        self.tree_view.expand(root_index)
        self.tree_view.setCurrentIndex(child_index)
        self.tree_view.scrollTo(child_index)
