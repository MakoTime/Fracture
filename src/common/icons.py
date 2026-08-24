import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from src.common.resources import resource_path


ICON_DIRECTORY = resource_path("icons")


def _icon(filename: str) -> QIcon:
    return QIcon(str(ICON_DIRECTORY / filename))


ALERT_OCTAGON_ICON = _icon("alert_octagon.svg")
BIN_ICON = _icon("bin.svg")
BLOOD_DROP_ICON = _icon("blood_drop.svg")
COLOUR_PALETTE_ICON = _icon("colour_palette.svg")
DASHBOARD_WARNING_ICON = _icon("dashboard_warning.svg")
EARTH_ICON = _icon("earth.svg")
FLOATING_ISLAND_ICON = _icon("floating_island.svg")
FOLDER_ICON = _icon("folder.svg")
FOLDER_COLLAPSED_ICON = _icon("folder_collapsed.svg")
FOLDER_EXPANDED_ICON = _icon("folder_expanded.svg")
GRID_ICON = _icon("grid.svg")
INFO_ICON = _icon("info.svg")
MAP_ICON = _icon("map.svg")
ORBIT_ICON = _icon("orbit.svg")
NOTES_ICON = _icon("notes.svg")
PAUSE_ICON = _icon("pause.svg")
PLAY_ICON = _icon("play.svg")
REWIND_ICON = _icon("rewind.svg")
FAST_FORWARD_ICON = _icon("fast_forward.svg")
REWIND_2_ICON = _icon("rewind_2.svg")
REWIND_3_ICON = _icon("rewind_3.svg")
FAST_FORWARD_2_ICON = _icon("fast_forward_2.svg")
FAST_FORWARD_3_ICON = _icon("fast_forward_3.svg")
RAIN_UMBRELLA_ICON = _icon("rain_umbrella.svg")
SAVE_ICON = _icon("save.svg")
VISIBLE_ICON = _icon("visible.svg")
INVISIBLE_ICON = _icon("invisible.svg")
PHOTO_CHANGED_FILTER_ICON = _icon("photo_changed_filter.svg")
SHAPE_CUBE_ICON = _icon("shape_cube.svg")


ICONS = {
    "alert_octagon": ALERT_OCTAGON_ICON,
    "bin": BIN_ICON,
    "blood_drop": BLOOD_DROP_ICON,
    "colour_palette": COLOUR_PALETTE_ICON,
    "dashboard_warning": DASHBOARD_WARNING_ICON,
    "earth": EARTH_ICON,
    "floating_island": FLOATING_ISLAND_ICON,
    "folder": FOLDER_ICON,
    "folder_collapsed": FOLDER_COLLAPSED_ICON,
    "folder_expanded": FOLDER_EXPANDED_ICON,
    "grid": GRID_ICON,
    "info": INFO_ICON,
    "map": MAP_ICON,
    "orbit": ORBIT_ICON,
    "notes": NOTES_ICON,
    "pause": PAUSE_ICON,
    "play": PLAY_ICON,
    "rewind": REWIND_ICON,
    "fast_forward": FAST_FORWARD_ICON,
    "rewind_2": REWIND_2_ICON,
    "rewind_3": REWIND_3_ICON,
    "fast_forward_2": FAST_FORWARD_2_ICON,
    "fast_forward_3": FAST_FORWARD_3_ICON,
    "rain_umbrella": RAIN_UMBRELLA_ICON,
    "save": SAVE_ICON,
    "visible": VISIBLE_ICON,
    "invisible": INVISIBLE_ICON,
    "photo_changed_filter": PHOTO_CHANGED_FILTER_ICON,
    "shape_cube": SHAPE_CUBE_ICON,
}


def get_icon(name: str) -> QIcon:
    """Return a named application icon."""
    try:
        return ICONS[name]
    except KeyError as error:
        raise KeyError(f"unknown icon: {name}") from error
