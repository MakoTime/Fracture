from PySide6.QtGui import QAction


def setup_menu(main_window):
	"""Populate the menus created by the main window UI."""
	file_menu = main_window.menuFile
	edit_menu = main_window.menuEdit

	open_action = QAction("Open", main_window)
	save_action = QAction("Save", main_window)
	exit_action = QAction("Exit", main_window)
	exit_action.triggered.connect(main_window.close)

	file_menu.addAction(open_action)
	file_menu.addAction(save_action)
	file_menu.addSeparator()
	file_menu.addAction(exit_action)

	undo_action = edit_menu.addAction("Undo")
	redo_action = edit_menu.addAction("Redo")
	undo_action.setEnabled(False)
	redo_action.setEnabled(False)

	main_window.open_action = open_action
	main_window.save_action = save_action
	main_window.exit_action = exit_action
	main_window.undo_action = undo_action
	main_window.redo_action = redo_action

	return {
		"open": open_action,
		"save": save_action,
		"exit": exit_action,
		"undo": undo_action,
		"redo": redo_action,
	}
