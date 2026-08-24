from PySide6.QtWidgets import QHBoxLayout, QWidget

from .play_pause import PlayPauseWidget
from .transport import FastForwardWidget, RewindWidget


class MediaControlsWidget(QWidget):
    """Mutually exclusive rewind, play/pause, and fast-forward controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rewind_button = RewindWidget(self)
        self.play_pause_button = PlayPauseWidget(parent=self)
        self.fast_forward_button = FastForwardWidget(self)

        controls = QHBoxLayout(self)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.addWidget(self.rewind_button)
        controls.addWidget(self.play_pause_button)
        controls.addWidget(self.fast_forward_button)
        controls.addStretch(1)

        self.rewind_button.clicked.connect(self._rewind_clicked)
        self.play_pause_button.clicked.connect(self._play_pause_clicked)
        self.fast_forward_button.clicked.connect(self._fast_forward_clicked)

    def _rewind_clicked(self):
        self.play_pause_button.reset()
        self.fast_forward_button.reset()

    def _play_pause_clicked(self):
        self.rewind_button.reset()
        self.fast_forward_button.reset()

    def _fast_forward_clicked(self):
        self.rewind_button.reset()
        self.play_pause_button.reset()
