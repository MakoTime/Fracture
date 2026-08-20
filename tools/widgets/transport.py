from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QToolButton

from common.icons import get_icon


class _SteppedTransportWidget(QToolButton):
    speedChanged = Signal(int)

    ICON_NAMES = ()
    ACTION_NAME = "Transport"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._speed = 1
        self.setAutoRaise(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(30, 30)
        self.setIconSize(QSize(22, 22))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setAccessibleName(self.ACTION_NAME)
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
            """
        )
        self.clicked.connect(self.advance)
        self._update_icon()

    def speed(self):
        return self._speed

    def set_speed(self, speed):
        speed = max(1, min(3, int(speed)))
        if speed == self._speed:
            self._update_icon()
            return
        self._speed = speed
        self._update_icon()
        self.speedChanged.emit(speed)

    def advance(self):
        self.set_speed(self._speed % 3 + 1)

    def reset(self):
        self.set_speed(1)

    def _update_icon(self):
        self.setIcon(get_icon(self.ICON_NAMES[self._speed - 1]))
        self.setToolTip(f"{self.ACTION_NAME} ({self._speed}x)")


class FastForwardWidget(_SteppedTransportWidget):
    """Button that cycles through one, two, and three fast-forward arrows."""

    ICON_NAMES = ("fast_forward", "fast_forward_2", "fast_forward_3")
    ACTION_NAME = "Fast forward"


class RewindWidget(_SteppedTransportWidget):
    """Button that cycles through one, two, and three rewind arrows."""

    ICON_NAMES = ("rewind", "rewind_2", "rewind_3")
    ACTION_NAME = "Rewind"
