from typing import Callable, Optional

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QMenu, QTreeView


class TreeView(QTreeView):
    """Custom QTreeView for displaying hierarchical data."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setItemsExpandable(True)
        self.setRootIsDecorated(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self._context_menu_factory: Optional[Callable] = None
        self._context_menu_factories = []
        self.expanded.connect(self._on_expanded)
        self.collapsed.connect(self._on_collapsed)

    def _on_expanded(self, index):
        model = self.model()
        if hasattr(model, "set_expanded"):
            model.set_expanded(index, True)

    def _on_collapsed(self, index):
        model = self.model()
        if hasattr(model, "set_expanded"):
            model.set_expanded(index, False)

    def set_context_menu_factory(self, factory: Optional[Callable]):
        """Set a callback that builds a menu for a clicked tree index."""
        self._context_menu_factory = factory
        self._context_menu_factories = [factory] if factory is not None else []

    def add_context_menu_factory(self, factory: Callable):
        """Add a callback that contributes actions to a clicked tree menu."""
        if factory not in self._context_menu_factories:
            self._context_menu_factories.append(factory)

    def _show_context_menu(self, position: QPoint):
        if not self._context_menu_factories:
            return
        index = self.indexAt(position)
        if not index.isValid():
            return
        self.setCurrentIndex(index)
        menu = QMenu(self._main_window())
        for factory in self._context_menu_factories:
            factory_menu = factory(index, menu)
            if isinstance(factory_menu, QMenu):
                menu.addActions(factory_menu.actions())
        if isinstance(menu, QMenu):
            if not menu.actions():
                return
            menu.exec(self.viewport().mapToGlobal(position))

    def _main_window(self):
        """Find the actual application window above a docked tree."""
        widget = self
        while widget.parentWidget() is not None:
            widget = widget.parentWidget()
        return widget