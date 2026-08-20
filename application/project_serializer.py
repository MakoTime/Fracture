import json
from pathlib import Path

from components.tree.roots import mesh_root, root_objects
from engine.block_objects import MeshBlockObject
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
            objects.append(
                {
                    "type": "mesh",
                    "guid": block.guid,
                    "name": block.name,
                    "comments": block.comments,
                    "visible": mesh_object.visible,
                    "in_scene": in_scene,
                    "parent_guid": self._parent_guid(node),
                    "block_data": f"{BLOCK_DATA_DIRECTORY}/{block_path.name}",
                }
            )

        data = {"version": CURRENT_PROJECT_VERSION, "objects": objects}
        directory.mkdir(parents=True, exist_ok=True)
        project_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return project_file

    def load(self, project_file, object_importer, tree_model, table_model, scene_viewer):
        project_path = Path(project_file)
        data = upgrade_project_data(
            json.loads(project_path.read_text(encoding="utf-8"))
        )

        self._clear_current_project(table_model, scene_viewer)
        loaded = {}
        pending = list(data.get("objects", []))
        while pending:
            remaining = []
            for item in pending:
                parent = mesh_root if item.get("parent_guid") is None else loaded.get(item["parent_guid"])
                if parent is None:
                    remaining.append(item)
                    continue
                block_path = project_path.parent / item["block_data"]
                block = MeshBlockObject.load(
                    block_path,
                    name=item["name"],
                    guid=item["guid"],
                    comments=item.get("comments", ""),
                    load_data=item.get("in_scene", False),
                )
                mesh_object = MeshObject(
                    name=item["name"],
                    block_object=block,
                    comments=item.get("comments", ""),
                    visible=item.get("visible", False),
                    guid=item["guid"],
                    auto_register_root=False,
                )
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

        tree_model.refresh()
        return list(loaded.values())

    @staticmethod
    def _walk_nodes(parent):
        for node in parent.children:
            yield node
            yield from ProjectSerializer._walk_nodes(node)

    @staticmethod
    def _parent_guid(node):
        parent = node.parent
        if parent is None or parent is mesh_root:
            return None
        return getattr(parent.node_object, "guid", None)

    @staticmethod
    def _clear_current_project(table_model, scene_viewer):
        scene_viewer.clear_scene()
        table_model.beginResetModel()
        table_model.table_manager.get_data().clear()
        table_model.endResetModel()
        mesh_root.children.clear()
        root_objects.nodes[:] = [mesh_root]