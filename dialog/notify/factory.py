from typing import Optional

from PySide6.QtGui import QPixmap

from .model import NotifyModel
from .view import NotifyView


def create_notification(
    title: str,
    content: str,
    icon: Optional[QPixmap] = None,
    parent=None,
) -> NotifyView:
    """Build a notification dialog from its display data."""
    return NotifyView(
        NotifyModel(title=title, content=content, icon=icon),
        parent=parent,
    )