# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-09-20

### Added
- Slide Curve: slide a selected loop or path toward a fitted curve (open: pinned polynomial; closed: Fourier harmonics) while vertices stay on rails. `[` `]` or mouse wheel changes Order; X/Y/Z fits in that plane.

### Changed
- Slide Curve starts at factor 0 (the current pose). Drag away from the pivot, or type a value, toward 1 to approach the fitted curve. Factor is clamped to 0–1.

### Fixed
- The Slide Tools sidebar no longer errors when drawing the Curve button.
- Slide Curve no longer slams vertices to the far ends of their rails at tiny factors.
- Slide Curve factor 1 now slides each vertex to the closest point on its rail to the fitted curve, so verts use the rail travel the overlay allows.

## [0.2.0] - 2026-09-20

### Added
- Shift+Alt+R opens a Slide pie (Rotate left, Scale right, Flatten top). Flick, click, or tap R / S / F.
- Slide Scale: scale from the transform pivot while vertices stay on automatically chosen rails.
- Slide Flatten: project the selection onto its best-fit plane (or an X/Y/Z lock plane) while vertices slide on rails.

### Changed
- The add-on is named Slide Tools (sidebar, F3, extension id). Slide Rotate, Slide Scale, and Slide Flatten are the three operators.
- Shift+Alt+R no longer starts Rotate immediately; pick Rotate from the pie (or Mesh → Transform).

### Fixed
- Axis-locked Slide Scale (for example Y lock at 0) now reaches the pivot plane along each rail instead of stopping slightly short when the rail is tilted.
- Loop vertices keep sliding on their connected edges; through-face rails are only borrowed when a vertex has no unselected neighbor (face interiors).
- Rotate no longer snaps a vertex onto the pivot when its rail points at it; it eases along that edge instead.

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

