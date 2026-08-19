import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtUiTools import QUiLoader

from application import ProjectController
from components.scene import SceneViewer
from components.table import TableView
from components.tree import TreeView


def load_main_window():
	"""Load the Designer UI and connect its application models and views."""
	loader = QUiLoader()
	loader.registerCustomWidget(SceneViewer)
	loader.registerCustomWidget(TreeView)
	loader.registerCustomWidget(TableView)
	ui_path = Path(__file__).parent / "UI" / "main.ui"
	window = loader.load(str(ui_path))
	if window is None:
		raise RuntimeError(loader.errorString())

	window = ProjectController(window).setup()
	return window

def main():
	app = QApplication(sys.argv)
	window = load_main_window()
	window.show()
	sys.exit(app.exec())


if __name__ == "__main__":
	main()
