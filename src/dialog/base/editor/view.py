from typing import Protocol, runtime_checkable

from PySide6.QtWidgets import QAbstractButton, QDialogButtonBox

from src.components.tree.roots import root_objects
from src.components.tree.search import TreeSearch


@runtime_checkable
class HasEditorButtons(Protocol):
    """Interface for editors exposing standard action buttons."""

    @property
    def ok_button(self) -> QAbstractButton | None: ...

    @property
    def cancel_button(self) -> QAbstractButton | None: ...

    @property
    def apply_button(self) -> QAbstractButton | None: ...

    def create_button_box(
        self,
        buttons: QDialogButtonBox.StandardButton | None = None,
    ) -> QDialogButtonBox: ...


class EditorView:
    """Common interaction contract shared by popup and tab editors."""

    def __init__(self, model=None, on_apply=None, on_close=None):
        self.model = model
        self._on_apply = on_apply
        self._on_close = on_close
        self._close_notified = False

    def update_model(self):
        """Copy editor-widget values into the model."""
        return self.model

    def apply_model(self):
        """Validate and return the applied model value."""
        return self.model.apply()

    def apply_changes(self):
        """Update, apply, and publish the model's current editor state."""
        self.update_model()
        # if not self._applicable:
        #     dialog = create_notification(
        #         "Cannot apply changes",
        #         "The current editor state is invalid and cannot be applied.",
        #         parent=self,
        #     )
        #     dialog.exec()
        #     return None
        result = self.apply_model()
        if self._on_apply is not None:
            self._on_apply(result)
        return result

    @property
    def _applicable(self):
        """Return True if the current model state is valid and can be applied."""
        if self.model is None:
            return False
        return True

    def _apply(self):
        """Preserve the legacy direct-apply helper."""
        return self.apply_changes()

    def notify_closed(self, reason="window"):
        """Notify the owner once after this editor's close was requested."""
        if self._close_notified:
            return False
        self._close_notified = True
        if self._on_close is not None:
            self._on_close(self.model, reason)
        return True

    def next_available_name(self) -> str:
        """Return a unique name for a new object in the model."""
        if self.model is None or not hasattr(self.model, "node"):
            return "Undefined"

        prefix = self.model.name
        node_type = type(self.model.node.node_object)
        tree_search = TreeSearch(root_objects.get_nodes())

        existing = tree_search.find(
            lambda node: isinstance(node.node_object, node_type)
        )

        existing_names = {obj.name for obj in existing if getattr(obj, "name", None)}

        if prefix not in existing_names:
            return prefix

        index = 1
        while f"{prefix} {index:03d}" in existing_names:
            index += 1

        return f"{prefix} {index:03d}"


class EditorButtonBoxImplementation:
    """Reusable Qt implementation of the editor button interface."""

    def __init__(self):
        self.button_box = None

    @property
    def ok_button(self):
        return self._button(QDialogButtonBox.StandardButton.Ok)

    @property
    def cancel_button(self):
        return self._button(QDialogButtonBox.StandardButton.Cancel)

    @property
    def apply_button(self):
        return self._button(QDialogButtonBox.StandardButton.Apply)

    def _button(self, standard_button):
        if self.button_box is None:
            return None
        return self.button_box.button(standard_button)
