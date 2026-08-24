from collections.abc import Callable

from PySide6.QtWidgets import QLineEdit


class NameField(QLineEdit):
    """Name editor whose value is initialized through a tree deduper."""

    def __init__(self, prefix, deduper: Callable[[str], str], parent=None):
        if not callable(deduper):
            raise TypeError("NameField requires a callable deduper")
        self._deduper = deduper
        super().__init__(str(prefix).strip(), parent)

    def unique_name(self):
        """Return the current text after resolving it through the deduper."""
        return self._deduper(self.text().strip())
