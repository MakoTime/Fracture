from PySide6.QtWidgets import QDialogButtonBox, QMainWindow, QTabWidget

from ..editor import EditorButtonBoxImplementation, EditorView


class TabEditorView(QMainWindow, EditorButtonBoxImplementation, EditorView):
    """Editor view for workspaces where editors live in tabs."""

    def __init__(self, model, parent=None, on_apply=None, on_close=None):
        QMainWindow.__init__(self, parent)
        EditorButtonBoxImplementation.__init__(self)
        EditorView.__init__(
            self,
            model,
            on_apply=on_apply,
            on_close=on_close,
        )
        self._close_reason = None

    def create_button_box(self, buttons=None):
        if buttons is None:
            buttons = (
                QDialogButtonBox.StandardButton.Cancel
                | QDialogButtonBox.StandardButton.Apply
                | QDialogButtonBox.StandardButton.Ok
            )
        self.button_box = QDialogButtonBox(buttons, self)
        self.button_box.rejected.connect(self._cancel)
        self.button_box.clicked.connect(self._button_clicked)
        return self.button_box

    def _cancel(self):
        self.close_editor("cancel")

    def close_editor(self, reason="window"):
        self._close_reason = reason
        return self.close()

    def _button_clicked(self, button):
        role = self.button_box.buttonRole(button)
        if role in (
            QDialogButtonBox.ButtonRole.ApplyRole,
            QDialogButtonBox.ButtonRole.AcceptRole,
        ):
            result = self.apply_changes()
            if role == QDialogButtonBox.ButtonRole.AcceptRole and result is not None:
                self.close_editor("ok")

    def closeEvent(self, event):
        """Remove this editor from its workspace tab when it closes."""
        tabs = self.parentWidget()
        while tabs is not None and not isinstance(tabs, QTabWidget):
            tabs = tabs.parentWidget()
        if tabs is not None:
            tab_index = tabs.indexOf(self)
            if tab_index >= 0:
                tabs.removeTab(tab_index)
        self.notify_closed(self._close_reason or "window")
        QMainWindow.closeEvent(self, event)
