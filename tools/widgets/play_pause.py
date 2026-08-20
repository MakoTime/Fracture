from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QToolButton

from common.icons import get_icon


class PlayPauseWidget(QToolButton):
    """Checkable play/pause control for starting and pausing work."""

    def __init__(self, playing=False, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setAutoRaise(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(30, 30)
        self.setIconSize(QSize(22, 22))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setAccessibleName("Play or pause")
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
        self.set_playing(playing)

    def is_playing(self):
        return self.isChecked()

    def set_playing(self, playing):
        self.setChecked(bool(playing))
        self._update_icon(bool(playing))

    def reset(self):
        self.set_playing(False)

    def _update_icon(self, playing):
        icon_name = "pause" if playing else "play"
        self.setIcon(get_icon(icon_name))
        self.setToolTip("Pause" if playing else "Play")
