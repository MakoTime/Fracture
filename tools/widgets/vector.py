from PySide6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLabel, QWidget


class _VectorWidget(QWidget):
    def __init__(self, dimensions, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._spins = []

        for axis in "xyz"[:dimensions]:
            label = QLabel(axis.upper())
            spin = QDoubleSpinBox()
            spin.setRange(-1_000_000.0, 1_000_000.0)
            spin.setDecimals(4)
            spin.setSingleStep(0.1)
            spin.setToolTip(f"{axis.upper()} component")
            setattr(self, axis, spin)
            self._spins.append(spin)
            layout.addWidget(label)
            layout.addWidget(spin)

    def value(self):
        return tuple(spin.value() for spin in self._spins)

    def set_value(self, value):
        if len(value) != len(self._spins):
            raise ValueError(f"expected {len(self._spins)} values")
        for spin, component in zip(self._spins, value):
            spin.setValue(float(component))


class Vector3Widget(_VectorWidget):
    def __init__(self, parent=None):
        super().__init__(3, parent)
        
        

class Vector2Widget(_VectorWidget):
    def __init__(self, parent=None):
        super().__init__(2, parent)