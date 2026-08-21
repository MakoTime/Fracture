import math

from PySide6.QtWidgets import QDoubleSpinBox


class DynamicSpinbox(QDoubleSpinBox):
    """Double spin box whose step is one tenth of its current range."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._update_step(self.minimum(), self.maximum())

    def setRange(self, minimum, maximum):
        super().setRange(minimum, maximum)
        self._update_step(minimum, maximum)

    def setMinimum(self, minimum):
        super().setMinimum(minimum)
        self._update_step(self.minimum(), self.maximum())

    def setMaximum(self, maximum):
        super().setMaximum(maximum)
        self._update_step(self.minimum(), self.maximum())

    def _update_step(self, minimum, maximum):
        span = abs(float(maximum) - float(minimum))
        if span == 0.0:
            return
        exponent = math.floor(math.log10(span))
        self.setSingleStep(10.0 ** (exponent - 1))
        self.setDecimals(max(self.decimals(), max(0, -exponent + 1)))