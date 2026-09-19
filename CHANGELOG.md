# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-09-19

### Added
- Status bar shows Confirm, Cancel, Precision, Snap, Clamp, and X/Y/Z while Slide Rotate is running, like native R.
- Mesh → Transform → Slide Rotate, next to native Rotate.
- X/Y/Z lock draws a thick anti-aliased infinite axis line through the pivot, colored like native R (theme Axis X/Y/Z mixed with the same light blend).

### Fixed
- Confirm and Redo Last no longer spam the Info editor with “vertices stayed still”.
- Pressing Shift after moving keeps the current angle and only slows further mouse motion.

## [0.1.0] - 2026-09-19

### Added
- GitHub Release zip from `./scripts/release.sh` (tagged `v*` builds via Actions).
- Face-interior vertices borrow through-rails from the coplanar face so they slide with the boundary instead of along in-face edges.
- Slide Rotate mesh operator: rotate a selection around the transform pivot while vertices slide on automatically chosen connected edges.
- Shift+Alt+R Mesh Edit shortcut, Vertex/Edge menus, F3 search, and a tiny 3D View sidebar with a development Reload button.
- View-plane rotation like native R, including orthogonal views, with X/Y/Z axis lock cycling (current orientation, then Global/Local, then back to View).
- Extend Rails on by default, toggle Clamp with C, Shift precision, Ctrl angle snap, simple typed-degree input, and a modal rail overlay.
- Redo Last properties for angle, extend rails, and axis lock.

### Changed
- Pressing X, Y, or Z re-chooses rails for the new axis, so interior through-rails can appear after axis lock.

### Fixed
- Axis-locked rotation follows the mouse after orbiting to the other side of the model, like native R.

