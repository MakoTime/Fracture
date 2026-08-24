"""Project metadata versioning and upgrade steps.

Keep schema migrations here so loading an older project does not spread
version checks throughout the persistence code.
"""

from collections.abc import Callable
from typing import Any

CURRENT_PROJECT_VERSION = 1
LEGACY_FORMAT_KEY = "format"
VERSION_KEY = "version"

UpgradeStep = Callable[[dict[str, Any]], dict[str, Any]]


def _upgrade_v0_to_v1(data: dict[str, Any]) -> dict[str, Any]:
    """Upgrade the original metadata shape to the versioned shape."""
    upgraded = dict(data)
    upgraded.pop(LEGACY_FORMAT_KEY, None)
    upgraded[VERSION_KEY] = 1
    return upgraded


UPGRADE_STEPS: dict[int, UpgradeStep] = {
    0: _upgrade_v0_to_v1,
}


def upgrade_project_data(data: dict[str, Any]) -> dict[str, Any]:
    """Upgrade project metadata to ``CURRENT_PROJECT_VERSION``.

    Files written before the dedicated version field existed used
    ``format: 1`` and are treated as version 0.
    """
    version = data.get(VERSION_KEY)
    if version is None:
        version = 0 if LEGACY_FORMAT_KEY in data else None
    if not isinstance(version, int):
        raise ValueError("Project metadata has no valid version")
    if version > CURRENT_PROJECT_VERSION:
        raise ValueError(
            f"Project version {version} is newer than supported version "
            f"{CURRENT_PROJECT_VERSION}"
        )

    upgraded = dict(data)
    while version < CURRENT_PROJECT_VERSION:
        try:
            upgrade = UPGRADE_STEPS[version]
        except KeyError as error:
            raise ValueError(
                f"No upgrade path from project version {version}"
            ) from error
        upgraded = upgrade(upgraded)
        version = upgraded[VERSION_KEY]
    return upgraded
