# Changelog

All notable changes to Fracture are documented here.

## [Unreleased]

### Changed

- Project upgrades now normalize legacy datetime data before import.
- Saved-time table operations and deserialization are owned by `WorldStateModel`.

### Fixed

- Legacy datetime project data now upgrades to the current custom `WorldTime` shape.
- Loading saved times refreshes the table and updates attached island transforms.

## [2.0.0] - 2026-08-26

### Changed

- Added the version-2 project migration for custom `WorldTime` values.
