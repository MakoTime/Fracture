from collections.abc import Iterable

from PySide6.QtWidgets import QMenu, QWidget

from .model import DropdownModel, DropdownOption
from .view import DropdownView


def create_dropdown(
    options: Iterable,
    current_value=None,
    parent: QWidget | None = None,
) -> DropdownView:
    """Build a dropdown from labels, pairs, or DropdownOption values."""
    model = DropdownModel.from_options(options, current_value)
    return DropdownView(model, parent=parent)


def create_dropdown_menu(options: Iterable, parent: QWidget | None = None) -> QMenu:
    """Build a context-style dropdown menu from label/callback pairs."""
    menu = QMenu(parent)
    for option in options:
        if isinstance(option, DropdownOption):
            label = option.label
            callback = option.value
            enabled = option.enabled
            icon = option.icon
        else:
            label, callback, *details = option
            enabled = True
            icon = details[0] if details else None
        action = menu.addAction(label)
        action.setEnabled(enabled)
        if icon is not None:
            action.setIcon(icon)
        if callable(callback):
            action.triggered.connect(
                lambda checked=False, callback=callback: callback()
            )
    return menu
