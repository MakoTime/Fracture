import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtUiTools import QUiLoader

from application import ProjectController
from application.file_window import FileWindow, ProjectPreview
from components.scene import SceneViewer
from components.table import TableView
from components.tree import TreeView
from engine import EngineRunner


def load_main_window(project_file):
	"""Load the Designer UI and connect its application models and views."""
	loader = QUiLoader()
	loader.registerCustomWidget(SceneViewer)
	loader.registerCustomWidget(TreeView)
	loader.registerCustomWidget(TableView)
	loader.registerCustomWidget(EngineRunner)
	ui_path = Path(__file__).parent / "UI" / "main.ui"
	window = loader.load(str(ui_path))
	if window is None:
		raise RuntimeError(loader.errorString())

	controller = ProjectController(window)
	window = controller.setup()
	controller.load_project(project_file)
	return window


def load_file_window(store=None):
	"""Load the startup project-selection window from Designer UI."""
	loader = QUiLoader()
	loader.registerCustomWidget(ProjectPreview)
	ui_path = Path(__file__).parent / "UI" / "file_window.ui"
	window = loader.load(str(ui_path))
	if window is None:
		raise RuntimeError(loader.errorString())
	return FileWindow(window, store=store)

def main():
	app = QApplication(sys.argv)
	file_window = load_file_window()
	if file_window.window.exec() != QDialog.DialogCode.Accepted:
		sys.exit(0)
	window = load_main_window(file_window.selected_project)
	window.show()
	sys.exit(app.exec())


if __name__ == "__main__":
	main()
