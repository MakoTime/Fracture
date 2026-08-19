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

    def _show_context_menu(self, position: QPoint):
        if self._context_menu_factory is None:
            return
        index = self.indexAt(position)
        if not index.isValid():
            return
        self.setCurrentIndex(index)
        menu = self._context_menu_factory(index, self._main_window())
        if isinstance(menu, QMenu):
            menu.exec(self.viewport().mapToGlobal(position))

    def _main_window(self):
        """Find the actual application window above a docked tree."""
        widget = self
        while widget.parentWidget() is not None:
            widget = widget.parentWidget()
        return widget