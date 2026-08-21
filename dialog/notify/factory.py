from typing import Optional

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialogButtonBox

from .model import NotifyModel
from .view import NotifyView


def create_notification(
    title: str,
    content: str,
    icon: Optional[QPixmap] = None,
    parent=None,
    confirm=False,
) -> NotifyView:
    """Build a notification dialog from its display data."""
    view = NotifyView(
        NotifyModel(title=title, content=content, icon=icon),
        parent=parent,
    )
    if not confirm:
        view.button_box.setStandardButtons(
            QDialogButtonBox.StandardButton.Ok
        )
    return view