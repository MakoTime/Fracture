# RainFall Project Rules

- Use the project virtual environment for Python commands.
- Run tests with `.venv/Scripts/python.exe -m pytest`.
- Preserve existing public APIs and local project patterns.
- Keep changes focused on the requested behavior.
- Use `apply_patch` for manual code edits.
- Do not commit changes or create branches unless explicitly requested.
- Run a focused validation after an edit, followed by the relevant broader test suite when practical.
- Do not hide or weaken a failing test to make the suite pass.
- Keep Qt and PyVista lifecycle behavior safe in offscreen tests.
