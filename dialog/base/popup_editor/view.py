from PySide6.QtWidgets import QDialog, QDialogButtonBox

from ..editor import EditorButtonBoxImplementation, EditorView


class PopupEditorView(QDialog, EditorButtonBoxImplementation, EditorView):
    """Editor view for modal popup dialogs."""

    def __init__(self, model, parent=None, on_apply=None, on_close=None):
        QDialog.__init__(self, parent)
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
                | QDialogButtonBox.StandardButton.Ok
            )
        self.button_box = QDialogButtonBox(buttons, self)
        self.button_box.rejected.connect(self._cancel)
        self.button_box.clicked.connect(self._button_clicked)
        return self.button_box

    def _cancel(self):
        self.reject_editor()

    def accept_editor(self):
        self._close_reason = "ok"
        return self.accept()

    def reject_editor(self):
        self._close_reason = "cancel"
        return self.reject()

    def done(self, result):
        self.notify_closed(self._close_reason or ("ok" if result else "window"))
        QDialog.done(self, result)

    def _button_clicked(self, button):
        role = self.button_box.buttonRole(button)
        if role in (
            QDialogButtonBox.ButtonRole.ApplyRole,
            QDialogButtonBox.ButtonRole.AcceptRole,
        ):
            result = self.apply_changes()
            if role == QDialogButtonBox.ButtonRole.AcceptRole and result is not None:
                self.accept_editor()
