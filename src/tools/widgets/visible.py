from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QToolButton

from src.common.icons import get_icon


class VisibleWidget(QToolButton):
    """Checkable eye control for showing or hiding an object."""

    def __init__(self, visible=False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setAutoRaise(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(30, 30)
        self.setIconSize(QSize(22, 22))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setAccessibleName("Object visibility")
        self.setStyleSheet(
            """
            QToolButton {
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 3px;
            }
            QToolButton:hover {
                background-color: rgba(70, 120, 180, 35);
                border-color: rgba(70, 120, 180, 100);
            }
            QToolButton:focus {
                border-color: #4682b4;
            }
            QToolButton:checked {
                background-color: rgba(70, 140, 90, 35);
            }
            QToolButton:checked:hover {
                background-color: rgba(70, 140, 90, 60);
            }
            """
        )
        self.toggled.connect(self._update_icon)
        self.set_visible(visible)

    def is_visible(self):
        return self.isChecked()

    def set_visible(self, visible):
        visible = bool(visible)
        self.setChecked(visible)
        self._update_icon(visible)

    def _update_icon(self, visible):
        icon_name = "visible" if visible else "invisible"
        self.setIcon(get_icon(icon_name))
        self.setToolTip("Hide object" if visible else "Show object")
