from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QHBoxLayout,
    QSpinBox,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from qtpy.QtWidgets import QDoubleSpinBox


class CompactSpinBox(QWidget):
    """Spinbox with large, tightly stacked increment and decrement buttons."""

    valueChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.spinbox = QSpinBox()
        self.spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spinbox.setMinimumWidth(42)
        self.spinbox.valueChanged.connect(self.valueChanged)

        self.up_button = self._create_button(QStyle.StandardPixmap.SP_ArrowUp)
        self.down_button = self._create_button(QStyle.StandardPixmap.SP_ArrowDown)
        self.up_button.clicked.connect(self.spinbox.stepUp)
        self.down_button.clicked.connect(self.spinbox.stepDown)

        buttons = QVBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(0)
        buttons.addWidget(self.up_button)
        buttons.addWidget(self.down_button)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.addWidget(self.spinbox)
        layout.addLayout(buttons)

    @staticmethod
    def _create_button(pixmap):
        button = QToolButton()
        button.setIcon(button.style().standardIcon(pixmap))
        button.setIconSize(QSize(12, 12))
        button.setFixedSize(20, 13)
        button.setAutoRepeat(True)
        button.setAutoRepeatDelay(350)
        button.setAutoRepeatInterval(60)
        return button

    def setRange(self, minimum, maximum):
        self.spinbox.setRange(minimum, maximum)

    def setValue(self, value):
        self.spinbox.setValue(value)

    def value(self):
        return self.spinbox.value()


class NormalizedSpinBox(QDoubleSpinBox):
    """Editor for normalized values in the inclusive range from zero to one."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRange(0.0, 1.0)
        self.setDecimals(3)
        self.setSingleStep(0.01)
