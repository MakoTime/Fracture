---
name: Python Testing
description: "Use when adding or modifying Python code or tests in the Fracture project, especially Qt, PyVista, engine, serialization, and registration behavior."
applyTo:
  - "**/*.py"
---

# Python Testing

- Use the project interpreter at `.venv/Scripts/python.exe`.
- Run the narrowest relevant test first with `-q` or a specific test node.
- Run the full suite with `.venv/Scripts/python.exe -m pytest` before finishing behavior changes.
- Keep tests deterministic and independent of test order.
- Use the existing `qapp` fixture for Qt tests.
- Set up test doubles for scene, table, tree, and engine collaborators when native widgets are not under test.
- Close Qt windows and dialogs created by tests.
- Avoid modal dialogs that require manual interaction in automated tests.
- Treat native VTK and PyVista widgets as lifecycle-sensitive; do not leave deferred callbacks targeting closed widgets.
- Test project clearing and loading with assertions for scene, table, tree, and engine state.
- Do not modify production behavior solely to silence warnings unless the warning is caused by the change.
