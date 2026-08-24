from dataclasses import dataclass

from PySide6.QtGui import QPixmap


@dataclass(frozen=True)
class NotifyModel:
    """Data displayed by a notification dialog."""

    title: str
    content: str
    icon: QPixmap | None = None
