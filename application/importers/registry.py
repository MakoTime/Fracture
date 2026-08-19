import importlib
import pkgutil
from collections.abc import Callable


class ImportBindingRegistry:
    """Registry for feature-owned object importer bindings."""

    _bindings: list[Callable] = []
    _discovered = False

    @classmethod
    def register(cls, binder: Callable):
        if binder not in cls._bindings:
            cls._bindings.append(binder)
        return binder

    @classmethod
    def discover(cls, package_name="dialog"):
        if cls._discovered:
            return

        package = importlib.import_module(package_name)
        for module in pkgutil.walk_packages(
            package.__path__,
            f"{package.__name__}.",
        ):
            if module.name.endswith(".model"):
                importlib.import_module(module.name)
        cls._discovered = True

    @classmethod
    def bind_all(cls, object_importer, tree_view, parent=None):
        cls.discover()
        return [
            binder(object_importer, tree_view, parent)
            for binder in cls._bindings
        ]


def register_import_binding(binder: Callable):
    """Register a feature-owned importer binder."""
    return ImportBindingRegistry.register(binder)
