import pytest

from src.tools.dropdown import DropdownModel, DropdownOption, create_dropdown_menu


def test_dropdown_model_coerces_options_and_selects_first_value():
    model = DropdownModel.from_options(["One", ("Two", 2)])

    assert [option.label for option in model.options] == ["One", "Two"]
    assert [option.value for option in model.options] == ["One", 2]
    assert model.current_value == "One"


def test_dropdown_model_rejects_unavailable_value():
    model = DropdownModel.from_options(["One"])

    with pytest.raises(ValueError, match="not available"):
        model.set_current("Missing")


def test_dropdown_menu_connects_callbacks_and_preserves_disabled_state(qapp):
    triggered = []
    menu = create_dropdown_menu(
        [
            ("Run", lambda: triggered.append("run")),
            DropdownOption("Disabled", enabled=False),
        ]
    )

    actions = menu.actions()
    assert [action.text() for action in actions] == ["Run", "Disabled"]
    assert actions[1].isEnabled() is False

    actions[0].trigger()
    assert triggered == ["run"]


def test_dropdown_menu_discards_qt_triggered_boolean(qapp):
    class Handler:
        def __init__(self):
            self.called = 0

        def run(self):
            self.called += 1

    handler = Handler()
    menu = create_dropdown_menu([("Run", handler.run)])

    menu.actions()[0].trigger()

    assert handler.called == 1
