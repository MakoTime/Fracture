from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from .model import NotifyModel


class NotifyView(QDialog):
    """Compact warning-style dialog for displaying a notification."""

    def __init__(self, model: NotifyModel, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Notification")
        self.resize(420, 220)

        self.notify_icon = QLabel()
        self.notify_icon.setFixedSize(40, 40)
        self.notify_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notify_icon.setScaledContents(True)

        self.title = QLabel()
        self.title.setWordWrap(True)
        self.title.setStyleSheet("font-size: 12pt; font-weight: 600;")

        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        header_layout.addWidget(self.notify_icon)
        header_layout.addWidget(self.title, 1)

        self.content = QLabel()
        self.content.setMinimumHeight(56)
        self.content.setWordWrap(True)
        self.content.setAlignment(
            Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignTop
        )
        self.content.setTextInteractionFlags(
            Qt.TextInteractionFlag.LinksAccessibleByMouse
            | Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)
        layout.addLayout(header_layout)
        layout.addWidget(self.content, 1)
        layout.addWidget(self.button_box)

        self.set_model(model)

    def set_model(self, model: NotifyModel):
        """Apply notification data to the dialog widgets."""
        self.title.setText(model.title)
        self.content.setText(model.content)
        self.set_icon(model.icon)

    def set_icon(self, icon: Optional[QPixmap]):
        """Update the header image, clearing it when no image is supplied."""
        self.notify_icon.clear()
        if icon is not None and not icon.isNull():
            self.notify_icon.setPixmap(icon)