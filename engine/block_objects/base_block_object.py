from abc import ABC, abstractmethod
from uuid import uuid4


class BlockObject(ABC):
    def __init__(self, name="", guid=None, comments=""):
        self.name = name
        self.guid = guid or str(uuid4())
        self.comments = comments
        self._valid = True
        self._invalidation_callbacks = []
        self._change_callbacks = []
        self._destruction_callbacks = []
        self._parent_block_objects = []
        self._change_parent_block_objects = []
        self._child_block_objects = []
        self._parent_dependencies = {}
        self._child_dependencies = {}
        self._destroyed = False

    def __hash__(self):
        """Hash blocks by their stable project GUID."""
        return hash(self.guid)
        
    def invalidate(self, force=False):
        """Mark the block invalid and notify any task manager watching it."""
        self._invalidate(set(), force=force)

    def _invalidate(self, visited, force=False):
        if self in visited:
            return
        visited.add(self)
        if not force and not self._valid:
            return
        self._valid = False
        for callback in tuple(self._invalidation_callbacks):
            callback(self)
        for parent in tuple(self._parent_block_objects):
            parent._invalidate(visited, force=force)

    def mark_changed(self):
        """Invalidate this block and every parent that consumes it."""
        if self._destroyed:
            return False
        self._mark_changed({})
        return True

    def _mark_changed(self, visited, invalidates=True):
        previous = visited.get(self, False)
        if self in visited and (previous or not invalidates):
            return
        visited[self] = previous or invalidates
        if invalidates:
            self._valid = False
            for callback in tuple(self._invalidation_callbacks):
                callback(self)
        for callback in tuple(self._change_callbacks):
            callback(self)
        for parent in tuple(self._parent_block_objects):
            parent._mark_changed(visited, invalidates=True)
        for parent in tuple(self._change_parent_block_objects):
            parent._mark_changed(visited, invalidates=False)

    def add_parent_block_object(self, parent, dependent=False):
        """Register a parent and whether it depends on this block's lifetime."""
        if parent is self:
            raise ValueError("A block object cannot be its own parent")
        if parent not in self._parent_block_objects:
            self._parent_block_objects.append(parent)
        self._parent_dependencies[parent] = bool(dependent)
        if self not in parent._child_block_objects:
            parent._child_block_objects.append(self)
        parent._child_dependencies[self] = bool(dependent)

    def remove_parent_block_object(self, parent):
        """Remove a parent dependency from this block."""
        if parent in self._parent_block_objects:
            self._parent_block_objects.remove(parent)
        self._parent_dependencies.pop(parent, None)
        if self in parent._child_block_objects:
            parent._child_block_objects.remove(self)
        parent._child_dependencies.pop(self, None)

    def add_child_block_object(self, child, dependent=False):
        """Register a child and whether this block depends on its lifetime."""
        child.add_parent_block_object(self, dependent=dependent)

    def remove_child_block_object(self, child):
        """Remove a child dependency from this block."""
        child.remove_parent_block_object(self)

    def add_change_child_block_object(self, child):
        """Register a child whose changes update this block without scheduling it."""
        if self not in child._change_parent_block_objects:
            child._change_parent_block_objects.append(self)

    def remove_change_child_block_object(self, child):
        """Remove a change-only child relationship."""
        if self in child._change_parent_block_objects:
            child._change_parent_block_objects.remove(self)

    @property
    def child_block_objects(self):
        return tuple(self._child_block_objects)

    def validate(self):
        """Mark the block valid after successful processing."""
        if self._destroyed:
            raise RuntimeError("Cannot validate a destroyed block object")
        self._valid = True

    def add_invalidation_callback(self, callback):
        """Register a callback invoked when this block becomes invalid."""
        if callback not in self._invalidation_callbacks:
            self._invalidation_callbacks.append(callback)

    def add_change_callback(self, callback):
        """Register a callback invoked for explicit block changes."""
        if callback not in self._change_callbacks:
            self._change_callbacks.append(callback)

    def remove_change_callback(self, callback):
        """Stop notifying a callback about explicit block changes."""
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)

    def add_destruction_callback(self, callback):
        """Register a callback invoked when this block is destroyed."""
        if callback not in self._destruction_callbacks:
            self._destruction_callbacks.append(callback)

    def remove_destruction_callback(self, callback):
        """Stop notifying a callback when this block is destroyed."""
        if callback in self._destruction_callbacks:
            self._destruction_callbacks.remove(callback)

    def destroy(self):
        """Destroy this block and dependent parents exactly once."""
        if self._destroyed:
            return False
        self._destroyed = True
        self.invalidate()
        for callback in tuple(self._destruction_callbacks):
            callback(self)
        for parent in tuple(self._parent_block_objects):
            parent._on_child_destroyed(
                self,
                dependent=self._parent_dependencies.get(parent, False),
            )
        for parent in tuple(self._parent_block_objects):
            self.remove_parent_block_object(parent)
        for child in tuple(self._child_block_objects):
            self.remove_child_block_object(child)
        return True

    def _on_child_destroyed(self, child, dependent=False):
        """Handle a child lifetime ending."""
        del child
        self.mark_changed()
        if dependent:
            self.destroy()

    def remove_invalidation_callback(self, callback):
        """Stop notifying a callback when this block becomes invalid."""
        if callback in self._invalidation_callbacks:
            self._invalidation_callbacks.remove(callback)

    def is_valid(self):
        """Check if the block object is still valid."""
        return self._valid

    def is_destroyed(self):
        """Return whether this block can no longer be processed."""
        return self._destroyed

    @abstractmethod
    def prepare(self):
        """Prepare the block object for use in a project.

        This method is called when the block object is added to a project and
        should be used to perform any necessary initialization or validation.
        """
        pass

    @abstractmethod
    def process(self, progress_callback=None):
        """Process the block object to generate any derived data.

        This method is called after the block object has been prepared and
        should be used to perform any necessary processing or computation.
        """
        pass

    @abstractmethod
    def serialise(self, path):
        """
        Serialise any serialisable objects owned by the block object after the result is processed.
        """
        pass
    
    @abstractmethod
    def serialise_to_directory(self, directory):
        """
        Serialise any serialisable objects owned by the block object after the result is processed.
        """
        pass