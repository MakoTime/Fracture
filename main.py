import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget
from PySide6.QtUiTools import QUiLoader

from application import ProjectController
from application.file_window import FileWindow, ProjectPreview
from components.scene import SceneViewer
from components.table import TableView
from components.tree import TreeView
from components.world_state import WorldStateView
from engine import EngineRunner


def load_main_window(project_file, menu_bar=None):
	"""Load the Designer UI and connect its application models and views."""
	loader = QUiLoader()
	loader.registerCustomWidget(SceneViewer)
	loader.registerCustomWidget(TreeView)
	loader.registerCustomWidget(TableView)
	loader.registerCustomWidget(EngineRunner)
	loader.registerCustomWidget(WorldStateView)
	ui_path = Path(__file__).parent / "UI" / "main.ui"
	window = loader.load(str(ui_path))
	if window is None:
		raise RuntimeError(loader.errorString())

	controller = ProjectController(window)
	if menu_bar is not None:
		window.setMenuBar(None)
	window = controller.setup(menu_bar=menu_bar)
	window.project_controller = controller
	if project_file is not None:
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


def load_application_window(store=None):
	"""Create the host window containing project selection and project tabs."""
	host = QMainWindow()
	host.setWindowTitle("RainFall")
	host.resize(1120, 720)
	tabs = QTabWidget()
	host.setCentralWidget(tabs)

	file_window = load_file_window(store=store)
	file_page = file_window.window
	file_page.setParent(tabs)
	file_page.setWindowFlags(Qt.WindowType.Widget)
	tabs.addTab(file_page, "Open Project")
	file_page.cancelButton.clicked.connect(host.close)
	project_windows = {}
	host_menu_bar = host.menuBar()

	def show_project_menu(project_window):
		host_menu_bar.clear()
		controller = project_window.project_controller
		file_menu = host_menu_bar.addMenu("File")
		open_action = QAction("Open Project", host)
		open_action.triggered.connect(controller.open_project)
		file_menu.addAction(open_action)
		save_action = QAction("Save", host)
		save_action.triggered.connect(controller.save_project)
		file_menu.addAction(save_action)
		save_as_action = QAction("Save As...", host)
		save_as_action.triggered.connect(controller.save_project_as)
		file_menu.addAction(save_as_action)
		file_menu.addSeparator()
		exit_action = QAction("Exit", host)
		exit_action.triggered.connect(host.close)
		file_menu.addAction(exit_action)
		edit_menu = host_menu_bar.addMenu("Edit")
		undo_action = QAction("Undo", host)
		undo_action.setEnabled(False)
		edit_menu.addAction(undo_action)
		redo_action = QAction("Redo", host)
		redo_action.setEnabled(False)
		edit_menu.addAction(redo_action)

	def add_project_tab(project_window):
		project_window.setParent(tabs)
		project_window.setMenuBar(None)
		project_window.setWindowFlags(Qt.WindowType.Widget)
		index = tabs.addTab(project_window, "Project")
		project_windows[index] = project_window
		tabs.setCurrentIndex(index)
		show_project_menu(project_window)

	def update_menu(index):
		project_window = project_windows.get(index)
		if project_window is None:
			host_menu_bar.clear()
		else:
			show_project_menu(project_window)

	tabs.currentChanged.connect(update_menu)

	def open_project(project_file):
		project_window = load_main_window(project_file, menu_bar=host_menu_bar)
		add_project_tab(project_window)

	file_window.on_project_opened = open_project

	def create_project(project_file):
		project_window = load_main_window(None, menu_bar=host_menu_bar)
		project_window.project_controller.create_project(project_file)
		add_project_tab(project_window)

	file_window.on_project_created = create_project
	host.show()
	return host


def main():
	app = QApplication(sys.argv)
	window = load_application_window()
	sys.exit(app.exec())


if __name__ == "__main__":
	main()
