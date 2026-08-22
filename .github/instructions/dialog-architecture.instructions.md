---
name: Dialog Architecture
description: "Use when creating or modifying dialogs, dialog factories, dialog views, dialog models, or dialog tests in this project."
applyTo:
  - "dialog/**/*.py"
  - "tests/**/*dialog*.py"
  - "tests/test_registration.py"
  - "tests/test_transform_registration.py"
---

# Dialog Architecture

Dialogs use a three-part structure:

- `model.py` contains state, validation, defaults, transformations, and domain operations.
- `view.py` contains Qt widgets, layouts, signals, user interaction, and presentation logic.
- `factory.py` creates and configures the view and provides the public construction API.
- `__init__.py` re-exports the public factory, view, and model symbols where appropriate.

## Model Rules

- Keep domain state and business logic in the model.
- Do not import Qt widgets into the model.
- Make model methods testable without displaying a dialog.
- Validate user-editable values in the model before creating domain objects.
- Preserve existing model APIs when adding UI behavior.
- Use explicit defaults in the model constructor.
- Return domain objects or model values from model operations rather than Qt widgets.

## View Rules

- Keep Qt widget construction and layout code in `view.py`.
- Views should receive a model and optional callbacks rather than constructing domain state implicitly.
- Connect signals to small view methods that update the model or refresh the UI.
- Keep domain calculations out of signal handlers when they belong in the model.
- Use `QDialog.DialogCode.Accepted` and `QDialog.DialogCode.Rejected` for modal results.
- Close the dialog only after a successful apply or explicit cancel.
- Clean up timers, preview widgets, and asynchronous callbacks when the view closes.
- Do not create native preview widgets from deferred callbacks after the window is hidden or closed.
- Give important controls accessible names or tooltips when their purpose is not obvious.

## Factory Rules

- Put public dialog construction in `factory.py`.
- Factories should accept the model and callback dependencies explicitly.
- Factories should configure the parent, callbacks, and optional behavior.
- Avoid putting business logic in factories.
- Keep factory functions small and predictable.
- Match the existing naming convention, such as `create_*_dialog`.
- Re-export public factory functions from the dialog package's `__init__.py`.

Example:

```python
def create_mesh_filter_dialog(
    model=None,
    parent=None,
    on_apply=None,
    transforms=(),
):
    return MeshFilterView(
        model=model or MeshFilterModel(),
        parent=parent,
        on_apply=on_apply,
        transforms=transforms,
    )
```

## Testing Rules

- Test model behavior without creating a `QApplication` where possible.
- Test factory and view construction with the shared `qapp` fixture.
- Close every created dialog or window in the test.
- Test accepted, cancelled, and invalid-input paths.
- Test that callbacks receive the expected model or domain object.
- Test deferred UI work after closing a dialog.
- Use lightweight test doubles for scene viewers and native preview widgets.
- Do not allow tests to block on an unattended modal notification.
