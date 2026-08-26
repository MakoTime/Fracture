"""Project metadata versioning and upgrade steps.

Keep schema migrations here so loading an older project does not spread
version checks throughout the persistence code.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any

CURRENT_PROJECT_VERSION = "2.0.0"
LEGACY_FORMAT_KEY = "format"
VERSION_KEY = "version"

UpgradeStep = Callable[[dict[str, Any]], dict[str, Any]]


def _upgrade_v0_to_v1(data: dict[str, Any]) -> dict[str, Any]:
    """Upgrade the original metadata shape to the versioned shape."""
    upgraded = dict(data)
    upgraded.pop(LEGACY_FORMAT_KEY, None)
    upgraded[VERSION_KEY] = "1.0.0"
    return upgraded


def _world_time_payload(value: Any) -> dict[str, int] | None:
    """Convert a legacy datetime value to the current WorldTime payload."""
    if isinstance(value, dict):
        if not {"year", "month", "day"}.issubset(value):
            return None
        return {
            "year": int(value["year"]),
            "month": int(value["month"]),
            "day": int(value["day"]),
            "hours": int(value.get("hours", 0)),
            "minutes": int(value.get("minutes", 0)),
            "seconds": int(value.get("seconds", 0)),
            "milliseconds": int(value.get("milliseconds", 0)),
        }
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return {
        "year": parsed.year,
        "month": parsed.month - 1,
        "day": parsed.day - 1,
        "hours": parsed.hour,
        "minutes": parsed.minute,
        "seconds": parsed.second,
        "milliseconds": parsed.microsecond // 1000,
    }


def _default_world_time() -> dict[str, int]:
    return {
        "year": 0,
        "month": 0,
        "day": 0,
        "hours": 0,
        "minutes": 0,
        "seconds": 0,
        "milliseconds": 0,
    }


def _upgrade_v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy datetime values before world-state import."""
    upgraded = dict(data)
    world_state = dict(upgraded.get("world_state") or {})
    world_time = _world_time_payload(
        world_state.get("date_time", world_state.get("datetime"))
    )
    if world_time is None:
        world_time = _world_time_payload(world_state.get("world_time"))
    world_state["date_time"] = world_time or _default_world_time()

    saved_times = dict(world_state.get("saved_times") or {})
    rows = []
    for row in saved_times.get("rows", []):
        upgraded_row = dict(row)
        row_time = _world_time_payload(upgraded_row.get("date"))
        if row_time is None:
            row_time = _world_time_payload(upgraded_row.get("date_time"))
        upgraded_row["date"] = row_time or world_state["date_time"]
        upgraded_row.pop("date_time", None)
        rows.append(upgraded_row)
    saved_times["rows"] = rows
    world_state["saved_times"] = saved_times
    upgraded["world_state"] = world_state
    upgraded[VERSION_KEY] = "2.0.0"
    return upgraded


UPGRADE_STEPS: dict[int, UpgradeStep] = {
    0: _upgrade_v0_to_v1,
    1: _upgrade_v1_to_v2,
}


def upgrade_project_data(data: dict[str, Any]) -> dict[str, Any]:
    """Upgrade project metadata to ``CURRENT_PROJECT_VERSION``.

    Files written before the dedicated version field existed used
    ``format: 1`` and are treated as version 0.
    """
    raw_version = data.get(VERSION_KEY)
    if raw_version is None:
        version = 0 if LEGACY_FORMAT_KEY in data else None
    elif isinstance(raw_version, int):
        version = raw_version
    elif isinstance(raw_version, str):
        parts = raw_version.split(".")
        if len(parts) != 3 or not all(part.isdigit() for part in parts):
            version = None
        else:
            version = int(parts[0])
    else:
        version = None
    if version is None:
        raise ValueError("Project metadata has no valid version")
    current_major = int(CURRENT_PROJECT_VERSION.split(".", 1)[0])
    if version > current_major:
        raise ValueError(
            f"Project version {version} is newer than supported version "
            f"{CURRENT_PROJECT_VERSION}"
        )

    upgraded = dict(data)
    while version < current_major:
        try:
            upgrade = UPGRADE_STEPS[version]
        except KeyError as error:
            raise ValueError(
                f"No upgrade path from project version {version}"
            ) from error
        upgraded = upgrade(upgraded)
        version = int(upgraded[VERSION_KEY].split(".", 1)[0])
    return upgraded
