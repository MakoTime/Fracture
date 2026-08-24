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
        self.selected_action = None
        self.setWindowTitle("Notification")
        self.resize(380, 180)

        self.notify_icon = QLabel()
        self.notify_icon.setFixedSize(32, 32)
        self.notify_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notify_icon.setScaledContents(True)

        self.title = QLabel()
        self.title.setWordWrap(True)
        self.title.setStyleSheet("font-size: 12pt; font-weight: 600;")

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        header_layout.addWidget(self.notify_icon)
        header_layout.addWidget(self.title, 1)

        self.content = QLabel()
        self.content.setMinimumHeight(40)
        self.content.setWordWrap(True)
        self.content.setAlignment(
            Qt.AlignmentFlag.AlignLeading | Qt.AlignmentFlag.AlignTop
        )
        self.content.setTextInteractionFlags(
            Qt.TextInteractionFlag.LinksAccessibleByMouse
            | Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(8)
        layout.addLayout(header_layout)
        layout.addWidget(self.content, 1)
        layout.addWidget(self.button_box)

        self.set_model(model)

    def set_actions(self, actions):
        """Replace the standard buttons with named actions."""
        self.button_box.clear()
        for label, role in actions:
            button = self.button_box.addButton(label, role)
            button.clicked.connect(
                lambda _checked=False, action=label: self._choose_action(action)
            )

    def _choose_action(self, action):
        self.selected_action = action
        if action == "Cancel":
            self.reject()
        else:
            self.accept()

    def set_model(self, model: NotifyModel):
        """Apply notification data to the dialog widgets."""
        self.title.setText(model.title)
        self.content.setText(model.content)
        self.set_icon(model.icon)

    def set_icon(self, icon: QPixmap | None):
        """Update the header image, clearing it when no image is supplied."""
        self.notify_icon.clear()
        if icon is not None and not icon.isNull():
            self.notify_icon.setPixmap(icon)
