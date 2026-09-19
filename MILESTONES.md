# Milestones

Session tracker for Slide Rotate. Read **Current**, then [AGENTS.md](AGENTS.md).

**Current:** done (M0–M5). Treat new work as Unreleased bugfixes unless a milestone is opened.

## Protocol

- One milestone in progress at a time.
- New behavior gets unit tests in the same change. New bugs get a failing-then-passing regression test.
- User-visible work gets an Unreleased changelog bullet in the same change.
- Do not commit unless asked.
- After RNA schema changes, restart Blender.

## M0 — Scaffolding and reload loop

Status: **done**

- [x] `blender_manifest.toml`, package layout, GPL license
- [x] `scripts/link-dev.sh` symlink into Blender 5.1 extensions
- [x] Mesh keymap Shift+Alt+R
- [x] N-panel with Reload when `scripts/link-dev.sh` exists
- [x] CHANGELOG, AGENTS.md (changelog + unit/regression culture), README
- [x] pytest skeleton
- [x] `scripts/validate_addon.py`

## M1 — Geometry kernel + crude modal

Status: **done**

- [x] `core/geometry.py` rails, polar `t`, projection fallback, clamp
- [x] pytest: loop rails, freeze, clamp, X-axis plane, fallback, no drift
- [x] execute/modal apply from originals; median/cursor/active pivots
- [x] View axis so ortho views rotate around the perpendicular axis

## M2 — Native-feeling modal (includes axis lock)

Status: **done**

- [x] Screen-space angle around projected pivot; mouse-delta fallback
- [x] Shift precision, `C` clamp, header status, GPU rail overlay
- [x] X/Y/Z lock cycling with unit tests
- [x] Mesh Vertex/Edge menus; non-uniform scale world↔local tests

## M3 — Transform extras

Status: **done**

- [x] Ctrl snap using `snap_angle_increment_3d` / precision variant
- [x] Simple numeric degrees
- [x] Bounding-box pivot
- [x] Redo Last properties (`angle`, `extend_rails`, `lock_letter`)

## M4 — Docs and known limits

Status: **done**

- [x] README invoke, shortcut, math, limitations, manual checks
- [x] CHANGELOG Unreleased
- [x] Tracker complete

## M5 — Face-interior through-rails

Status: **done**

- [x] When 1-ring rails are a poor match for the rotational tangent, copy leaving edges from the coplanar face island onto that vertex
- [x] X/Y/Z lock restores the start pose and re-scores rails for the new axis
- [x] pytest: in-face neighbors lose, borrowed through-rail wins, strong 1-ring rails stay, interior theta slide, axis-dependent borrow
- [x] Blender smoke: subdivided face interiors move on through-rails
- [x] CHANGELOG / README

## Deviations from the original spec

- Blender 5.1 extension (`blender_manifest.toml`), not `bl_info`-only.
- Default shortcut is Shift+Alt+R, not an unspecified later keymap.
- Colinear opposite rails merge into one bidirectional clamp interval.
- Polar-angle intersection in the rotation plane, with projection fallback.
- Axis lock is core (M2), not a later extra.
- Logic lives in `core/` so pytest can run without bpy.
