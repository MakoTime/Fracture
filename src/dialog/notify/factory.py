from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialogButtonBox

from .model import NotifyModel
from .view import NotifyView


def create_notification(
    title: str,
    content: str,
    icon: QPixmap | None = None,
    parent=None,
    confirm=False,
    actions=None,
) -> NotifyView:
    """Build a notification dialog from its display data."""
    view = NotifyView(
        NotifyModel(title=title, content=content, icon=icon),
        parent=parent,
    )
    if not confirm:
        view.button_box.setStandardButtons(QDialogButtonBox.StandardButton.Ok)
    if actions is not None:
        view.set_actions(actions)
    return view
