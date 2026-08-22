import json
from pathlib import Path

from components.tree.roots import (
    colourmap_root,
    mesh_root,
    root_objects,
    transform_root,
)
from dialog.perlin_noise_transform import PerlinNoiseTransformModel
from engine.block_objects import (
    ColourmapBlockObject,
    GeneratedMeshBlockObject,
    MeshBlockObject,
    PerlinNoiseTransformBlockObject,
)
from objects.generated_mesh import GeneratedMesh
from objects.colourmap import ColourmapObject
from objects.mesh_object import MeshObject
from application.project_version import CURRENT_PROJECT_VERSION, upgrade_project_data


PROJECT_FILE = "project.json"
BLOCK_DATA_DIRECTORY = "block_data"


class ProjectSerializer:
    """Serialize project metadata separately from engine block payloads."""

    def save(self, project_directory, table_model, scene_viewer):
        requested_path = Path(project_directory)
        if requested_path.suffix.lower() == ".json":
            directory = requested_path.parent
            project_file = requested_path
        else:
            directory = requested_path
            project_file = directory / PROJECT_FILE
        block_directory = directory / BLOCK_DATA_DIRECTORY
        block_directory.mkdir(parents=True, exist_ok=True)
        objects = []

        for node in self._walk_nodes(mesh_root):
            mesh_object = node.node_object
            if not isinstance(mesh_object, MeshObject):
                raise TypeError(f"Unsupported project object: {type(mesh_object).__name__}")
            block = mesh_object.mesh_block_object
            block_path = block.serialise_to_directory(block_directory)
            in_scene = mesh_object in scene_viewer.scene_model.objects
            if not in_scene:
                block.release()
            item = {
                "type": "generated_mesh"
                if isinstance(mesh_object, GeneratedMesh)
                else "mesh",
                "guid": block.guid,
                "name": block.name,
                "comments": block.comments,
                "visible": mesh_object.visible,
                "in_scene": in_scene,
                "parent_guid": self._parent_guid(node),
                "child_references": self._child_references(block),
                "colourmap_reference": (
                    block.colourmap.guid if block.colourmap is not None else None
                ),
                "colourmap_field_sources": list(block.colourmap_field_sources),
                "colourmap_field_inversions": list(block.colourmap_field_inversions),
                "block_data": f"{BLOCK_DATA_DIRECTORY}/{block_path.name}",
            }
            if isinstance(mesh_object, GeneratedMesh):
                grid_path = block.grid_serialised_path
                item["grid_data"] = f"{BLOCK_DATA_DIRECTORY}/{grid_path.name}"
                transform = block.perlin_noise_transform
                item["transform_reference"] = (
                    transform.guid if transform is not None else None
                )
            objects.append(item)

        for node in self._walk_nodes(transform_root):
            transform = node.node_object
            if not hasattr(transform, "block_object"):
                raise TypeError(f"Unsupported project object: {type(transform).__name__}")
            item = PerlinNoiseTransformModel(
                name=transform.name,
                frequencies=transform.block_object.frequencies,
                amplitudes=transform.block_object.amplitudes,
                seed=transform.block_object.seed,
                guid=transform.guid,
                curve_mode=transform.block_object.curve_mode,
                curve_points=transform.block_object.curve_points,
                curve_handles=transform.block_object.curve_handles,
                frequency_start=transform.block_object.frequency_start,
                frequency_end=transform.block_object.frequency_end,
                sample_count=transform.block_object.sample_count,
                manual_sampling=transform.block_object.manual_sampling,
                preset=transform.block_object.preset,
                preset_options=transform.block_object.preset_options,
            ).to_json()
            item["comments"] = transform.block_object.comments
            item["parent_guid"] = self._parent_guid(node)
            item["child_references"] = self._child_references(
                transform.block_object
            )
            objects.append(item)

        for node in self._walk_nodes(colourmap_root):
            colourmap = node.node_object
            if not isinstance(colourmap, ColourmapObject):
                raise TypeError(
                    f"Unsupported project object: {type(colourmap).__name__}"
                )
            block_path = colourmap.block_object.serialise(
                block_directory / f"{colourmap.guid}.colourmap.json"
            )
            item = {
                    "type": "colourmap",
                    "guid": colourmap.guid,
                    "name": colourmap.name,
                    "comments": colourmap.block_object.comments,
                    "visible": colourmap.visible,
                    "parent_guid": self._parent_guid(node),
                    "child_references": self._child_references(
                        colourmap.block_object
                    ),
                    "block_data": f"{BLOCK_DATA_DIRECTORY}/{block_path.name}",
                }
            transform = colourmap.block_object.perlin_noise_transform
            item["transform_reference"] = (
                transform.guid if transform is not None else None
            )
            objects.append(item)

        data = {"version": CURRENT_PROJECT_VERSION, "objects": objects}
        directory.mkdir(parents=True, exist_ok=True)
        project_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return project_file

    def load(
        self,
        project_file,
        object_importer,
        tree_model,
        table_model,
        scene_viewer,
    ):
        project_path = Path(project_file)
        data = upgrade_project_data(
            json.loads(project_path.read_text(encoding="utf-8"))
        )

        self._clear_current_project(
            table_model,
            scene_viewer,
            getattr(object_importer, "engine_runner", None),
            tree_model,
        )
        loaded = {}
        pending = list(data.get("objects", []))
        while pending:
            remaining = []
            for item in pending:
                is_transform = item.get("type") == "perlin_noise_transform"
                is_colourmap = item.get("type") == "colourmap"
                default_parent = (
                    transform_root
                    if is_transform
                    else colourmap_root
                    if is_colourmap
                    else mesh_root
                )
                parent = (
                    default_parent
                    if item.get("parent_guid") is None
                    else loaded.get(item["parent_guid"])
                )
                if parent is None:
                    remaining.append(item)
                    continue
                if is_transform:
                    transform = PerlinNoiseTransformModel.from_json(item).to_object()
                    transform.block_object.comments = item.get("comments", "")
                    object_importer.register(
                        transform,
                        parent=parent,
                        add_to_scene=False,
                    )
                    loaded[transform.guid] = transform
                    continue
                if is_colourmap:
                    block = ColourmapBlockObject.load(
                        project_path.parent / item["block_data"]
                    )
                    colourmap = ColourmapObject(
                        name=item["name"],
                        block_object=block,
                        comments=item.get("comments", ""),
                        visible=item.get("visible", True),
                        guid=item["guid"],
                        auto_register_root=False,
                    )
                    object_importer.register(
                        colourmap,
                        parent=parent,
                        add_to_scene=False,
                    )
                    loaded[colourmap.guid] = colourmap
                    continue
                block_path = project_path.parent / item["block_data"]
                block_class = (
                    GeneratedMeshBlockObject
                    if item.get("type") == "generated_mesh"
                    else MeshBlockObject
                )
                if item.get("type") == "generated_mesh":
                    block = block_class.load(
                        block_path,
                        grid_path=project_path.parent / item["grid_data"],
                        name=item["name"],
                        guid=item["guid"],
                        comments=item.get("comments", ""),
                        load_data=item.get("in_scene", False),
                    )
                else:
                    block = block_class.load(
                        block_path,
                        name=item["name"],
                        guid=item["guid"],
                        comments=item.get("comments", ""),
                        load_data=item.get("in_scene", False),
                    )
                object_type = item.get("type", "mesh")
                if object_type == "generated_mesh":
                    grid_data = block.grid_data
                    object_class = GeneratedMesh
                else:
                    grid_data = None
                    object_class = MeshObject
                object_kwargs = {
                    "name": item["name"],
                    "block_object": block,
                    "comments": item.get("comments", ""),
                    "visible": item.get("visible", False),
                    "guid": item["guid"],
                    "auto_register_root": False,
                }
                if object_class is GeneratedMesh:
                    object_kwargs["grid_data"] = grid_data
                mesh_object = object_class(
                    **object_kwargs,
                )
                sources = item.get(
                    "colourmap_field_sources", block.colourmap_field_sources
                )
                if len(sources) == 2:
                    block.set_colourmap_field_sources(*sources)
                inversions = item.get(
                    "colourmap_field_inversions",
                    block.colourmap_field_inversions,
                )
                if len(inversions) == 2:
                    block.set_colourmap_data_options(*inversions)
                object_importer.register(
                    mesh_object,
                    parent=parent,
                    add_to_scene=item.get("in_scene", False),
                )
                if item.get("in_scene", False):
                    mesh_object.set_visible(item.get("visible", False))
                loaded[mesh_object.guid] = mesh_object
            if len(remaining) == len(pending):
                raise ValueError("Project contains an unresolved tree parent")
            pending = remaining

        self._restore_block_relationships(data.get("objects", []), loaded)
        self._restore_mesh_child_nodes(loaded)
        tree_model.refresh()
        return list(loaded.values())

    @staticmethod
    def _walk_nodes(parent):
        for node in parent.children:
            if getattr(node, "is_block_child", False):
                continue
            yield node
            yield from ProjectSerializer._walk_nodes(node)

    @staticmethod
    def _parent_guid(node):
        parent = node.parent
        if parent is None or parent is mesh_root:
            return None
        return getattr(parent.node_object, "guid", None)

    @staticmethod
    def _child_references(block):
        return [
            {
                "guid": child.guid,
                "dependent": block._child_dependencies.get(child, False),
            }
            for child in block.child_block_objects
        ]

    @staticmethod
    def _restore_block_relationships(items, loaded):
        for item in items:
            parent = loaded.get(item.get("guid"))
            if parent is None:
                continue
            parent_block = getattr(parent, "block_object", None)
            if parent_block is None:
                continue
            for reference in item.get("child_references", []):
                child = loaded.get(reference.get("guid"))
                child_block = getattr(child, "block_object", None)
                if child_block is None:
                    raise ValueError(
                        f"Project contains an unresolved child reference "
                        f"{reference.get('guid')}"
                    )
                if (
                    isinstance(parent_block, GeneratedMeshBlockObject)
                    and isinstance(child_block, PerlinNoiseTransformBlockObject)
                ):
                    parent_block.set_perlin_noise_transform(child_block)
                elif (
                    isinstance(parent_block, ColourmapBlockObject)
                    and isinstance(child_block, PerlinNoiseTransformBlockObject)
                ):
                    parent_block.set_perlin_noise_transform(child_block)
                elif isinstance(parent_block, MeshBlockObject) and isinstance(
                    child_block, ColourmapBlockObject
                ):
                    parent_block.set_colourmap(child_block)
                else:
                    parent_block.add_child_block_object(
                        child_block,
                        dependent=bool(reference.get("dependent", False)),
                    )
            transform_guid = item.get("transform_reference")
            if transform_guid is not None and isinstance(
                parent_block,
                (GeneratedMeshBlockObject, ColourmapBlockObject),
            ):
                transform = loaded.get(transform_guid)
                transform_block = getattr(transform, "block_object", None)
                if not isinstance(transform_block, PerlinNoiseTransformBlockObject):
                    raise ValueError(
                        f"Project contains an unresolved transform reference "
                        f"{transform_guid}"
                    )
                parent_block.set_perlin_noise_transform(transform_block)
            colourmap_guid = item.get("colourmap_reference")
            if colourmap_guid is not None and isinstance(
                parent_block, MeshBlockObject
            ):
                colourmap = loaded.get(colourmap_guid)
                colourmap_block = getattr(colourmap, "block_object", None)
                if not isinstance(colourmap_block, ColourmapBlockObject):
                    raise ValueError(
                        f"Project contains an unresolved colourmap reference "
                        f"{colourmap_guid}"
                    )
                parent_block.set_colourmap(colourmap_block)

    @staticmethod
    def _restore_mesh_child_nodes(loaded):
        objects = tuple(loaded.values())
        for mesh_object in objects:
            if not isinstance(mesh_object, MeshObject):
                continue
            child_blocks = mesh_object.mesh_block_object.child_block_objects
            children = tuple(
                object_base
                for object_base in objects
                if getattr(object_base, "block_object", None) in child_blocks
            )
            mesh_object.node.set_block_child_objects(children)

    @staticmethod
    def _clear_current_project(
        table_model,
        scene_viewer,
        engine_runner=None,
        tree_model=None,
    ):
        if tree_model is not None:
            tree_model.beginResetModel()
        if engine_runner is not None and hasattr(engine_runner, "clear"):
            engine_runner.clear()
        objects = []
        for root in (mesh_root, transform_root, colourmap_root):
            objects.extend(
                node.node_object
                for node in ProjectSerializer._walk_nodes(root)
                if hasattr(node, "node_object")
            )
        for object_base in objects:
            object_base.destroy()
        if hasattr(scene_viewer, "clear_scene"):
            scene_viewer.clear_scene()
        table_model.beginResetModel()
        table_model.table_manager.get_data().clear()
        table_model.endResetModel()
        mesh_root.children.clear()
        transform_root.children.clear()
        colourmap_root.children.clear()
        root_objects.nodes[:] = [mesh_root, transform_root, colourmap_root]
        if tree_model is not None:
            tree_model.endResetModel()