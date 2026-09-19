# Agent notes

Conventions for humans and coding agents working in this repo. Fresh sessions should read [MILESTONES.md](MILESTONES.md) for current progress.

## Changelog

User-visible work must land with a bullet under `## [Unreleased]` in `CHANGELOG.md` **in the same change** as the code (Keep a Changelog: Added / Changed / Fixed / Removed).

Do this when the change affects the operator, rails, modal keys, overlay, install, keymap, or documented behavior. Skip it for refactors, tests, comments, and internal-only edits.

Write one short user-facing line, not a commit subject. Describe the product behavior. Do not name user files or debug-scene geometry. Do not invent a version heading or bump `blender_manifest.toml` — that happens at release.

```markdown
## [Unreleased]

### Added
- Shift+Alt+R starts Slide Rotate in Mesh Edit Mode.
```

If `[Unreleased]` has no matching subsection yet, add it. Leave dated `## [x.y.z]` sections untouched.

Do not rewrite a dated changelog bullet. If later work revises that behavior, add a new **Fixed** / **Changed** / **Removed** line. Rewrite an **Unreleased** bullet in place only when it leaked a debug scene.

## Unit and regression tests

Strict, not optional.

- **Every new behavior ships with unit tests in the same change.** Geometry, rail scoring, polar solve, fallback, clamp, axis-lock cycling, mouse-angle wrap, precision, snap, numeric parsing, world↔local, status text. If a function is worth writing, it is worth a pytest. Keep that logic in `core/` so tests run without Blender.
- **Every new bug gets a regression test that fails before the fix and passes after.** Reproduce with the smallest numeric fixture (points, rails, axis, theta). Do not patch and move on. If a regression is truly impractical (live GPU handler, window event timing), say why in the handoff **and** still extract the logic so the next similar bug can be unit-tested.
- Run `pytest` before calling a milestone done. `scripts/validate_addon.py` covers registration, keymap, poll, execute, and reload — it does not replace unit tests.
- Do not special-case a user `.blend` in tests. Use generic synthetic geometry.

```sh
python3 -m pytest
"/Applications/Blender 5.1.app/Contents/MacOS/blender" \
  --factory-startup -b --python scripts/validate_addon.py
```

## Where code lives

| Area | Path |
| --- | --- |
| Vectors / matrices | `core/vec.py` |
| Rail solve, clamp, overlay segments | `core/geometry.py` |
| X/Y/Z lock cycling | `core/axis.py` |
| Mouse angle, snap, numeric input, status text | `core/input.py` |
| Pivots, world↔local | `core/transforms.py` |
| Dataclasses | `core/types.py` |
| Modal operator + reload | `ui/operators.py` |
| GPU rail overlay | `ui/overlay.py` |
| Sidebar | `ui/panel.py` |
| Registration / symlink reload | `__init__.py` |
| Pure tests | `tests/` |
| Blender smoke | `scripts/validate_addon.py` |

Keep `core/` free of `bpy`. `ui/operators.py` only maps Blender events onto those functions.

## Do not

- Commit, push, tag, or release unless explicitly asked.
- Unregister the add-on from inside an operator execute (use `schedule_reload()`).
- Steal `R`, `Shift+R`, `Ctrl+R`, or `Shift+Ctrl+R`. Default shortcut is **Shift+Alt+R** on the Mesh keymap.
