from pathlib import Path

from PySide6.QtGui import QIcon


ICON_DIRECTORY = Path(__file__).resolve().parent.parent / "icons"


def _icon(filename: str) -> QIcon:
	return QIcon(str(ICON_DIRECTORY / filename))


ALERT_OCTAGON_ICON = _icon("alert_octagon.svg")
BLOOD_DROP_ICON = _icon("blood_drop.svg")
DASHBOARD_WARNING_ICON = _icon("dashboard_warning.svg")
FOLDER_ICON = _icon("folder.svg")
FOLDER_COLLAPSED_ICON = _icon("folder_collapsed.svg")
FOLDER_EXPANDED_ICON = _icon("folder_expanded.svg")
GRID_ICON = _icon("grid.svg")
INFO_ICON = _icon("info.svg")
MAP_ICON = _icon("map.svg")
NOTES_ICON = _icon("notes.svg")
RAIN_UMBRELLA_ICON = _icon("rain_umbrella.svg")
SAVE_ICON = _icon("save.svg")
VISIBLE_ICON = _icon("visible.svg")
INVISIBLE_ICON = _icon("invisible.svg")


ICONS = {
	"alert_octagon": ALERT_OCTAGON_ICON,
	"blood_drop": BLOOD_DROP_ICON,
	"dashboard_warning": DASHBOARD_WARNING_ICON,
	"folder": FOLDER_ICON,
	"folder_collapsed": FOLDER_COLLAPSED_ICON,
	"folder_expanded": FOLDER_EXPANDED_ICON,
	"grid": GRID_ICON,
	"info": INFO_ICON,
	"map": MAP_ICON,
	"notes": NOTES_ICON,
	"rain_umbrella": RAIN_UMBRELLA_ICON,
	"save": SAVE_ICON,
	"visible": VISIBLE_ICON,
	"invisible": INVISIBLE_ICON,
}


def get_icon(name: str) -> QIcon:
	"""Return a named application icon."""
	try:
		return ICONS[name]
	except KeyError as error:
		raise KeyError(f"unknown icon: {name}") from error