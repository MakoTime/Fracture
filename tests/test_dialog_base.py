from PySide6.QtWidgets import QDialogButtonBox, QTabWidget

from dialog.base.editor import EditorModel
from dialog.base.popup_editor import PopupEditorView
from dialog.base.tab_editor import TabEditorView


def test_editor_view_applies_and_closes_workspace_tab(qapp):
    applied = []
    view = TabEditorView(EditorModel(), on_apply=applied.append)
    buttons = view.create_button_box()
    tabs = QTabWidget()
    tabs.addTab(view, "Editor")

    assert view.ok_button is buttons.button(QDialogButtonBox.StandardButton.Ok)
    assert view.cancel_button is buttons.button(QDialogButtonBox.StandardButton.Cancel)
    assert view.apply_button is buttons.button(QDialogButtonBox.StandardButton.Apply)

    buttons.button(QDialogButtonBox.StandardButton.Ok).click()

    assert applied == [view.model]
    assert tabs.count() == 0
    view.close()


def test_editor_close_callback_is_called_once_for_cancel(qapp):
    closed = []
    view = PopupEditorView(
        EditorModel(),
        on_close=lambda model, reason: closed.append((model, reason)),
    )
    view.create_button_box().button(QDialogButtonBox.StandardButton.Cancel).click()
    view.reject()

    assert closed == [(view.model, "cancel")]
    view.close()
