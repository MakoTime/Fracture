# Fracture

Fracture is a PySide6 desktop application for simulating and creating a a fractured planet with floating islands

## Requirements

- Windows
- Python 3.10 or newer
- A working OpenGL-capable desktop environment for the PyVista viewer

## Setup

Open PowerShell in the project directory and create a virtual environment:

```powershell
py -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation for the current terminal session, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

Then activate the environment again and install the dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run

With the virtual environment active:

```powershell
python main.py
```

The application opens with a PyVista scene viewer, a tree for imported objects, and a table for objects loaded into the active scene.

## Tests

Run the test suite from the project root:

```powershell
python -m pytest -q
```

The tests use Qt's offscreen platform where possible. Tests that create a real VTK render window may require a desktop OpenGL environment on Windows.

## Project Layout

```text
application/   Project-level composition and shared application setup
common/        Shared icons and application utilities
components/    Scene, table, and tree components
dialog/        Dialog models, views, and factories
objects/       Domain objects and object registration/import behavior
tools/         Reusable widgets, dropdowns, and UI helpers
UI/            Qt Designer UI files
icons/         SVG icon assets
main.py        Application entry point
```

## Basic Workflow

1. Right-click the `Meshes` tree node.
2. Choose `Import Mesh`.
3. Select a mesh file and enter its metadata.
4. Enable `Add to scene/table` if the mesh should be loaded into the active scene immediately.
5. Leave it unchecked to add the imported object to the tree only.
6. Use the tree or table controls to manage visibility and scene membership.
