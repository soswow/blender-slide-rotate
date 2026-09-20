# Agent notes

Conventions for humans and coding agents working in this repo. Fresh sessions should read [MILESTONES.md](MILESTONES.md) for current progress.

M0–M5 are done. New work is Unreleased bugfixes/polish unless a milestone is opened.

`initial-ai-generated-requirements.md` is a historical first-pass spec, not current behavior. Prefer README, `docs/`, this file, and `core/`.

## Changelog

Changelog bullets are for **product** changes only: features and bugs the operator sees in Blender.

A bullet under `## [Unreleased]` in `CHANGELOG.md` **in the same change** as the code (Keep a Changelog: Added / Changed / Fixed / Removed) when the add-on itself changes: operator, rails, modal keys, overlay, install, keymap, poll, or other in-Blender behavior.

Skip it for README, docs, demos, screenshots, changelog wording, AGENTS/MILESTONES, refactors, tests, comments, and other repo-only edits. Updating “documented behavior” in the README is not a changelog item unless the add-on behavior also changed.

Write one short user-facing line, not a commit subject. Describe the product behavior. Do not name user files or debug-scene geometry. Do not invent a version heading or bump `blender_manifest.toml` — that happens at release.

```markdown
## [Unreleased]

### Added
- Shift+Alt+R starts Slide Tools in Mesh Edit Mode.
```

If `[Unreleased]` has no matching subsection yet, add it. Leave dated `## [x.y.z]` sections untouched.

Do not rewrite a dated changelog bullet. If later work revises that behavior, add a new **Fixed** / **Changed** / **Removed** line. Rewrite an **Unreleased** bullet in place only when it leaked a debug scene.

To ship: `./scripts/release.sh 0.1.0` on a clean `main` with a GitHub `origin` remote. That cuts Unreleased, bumps `blender_manifest.toml` when the version changes, tags `v0.1.0`, and pushes. GitHub Actions builds the zip and creates the GitHub Release.

## Unit and regression tests

Strict, not optional.

- **Every new behavior ships with unit tests in the same change.** Geometry, rail scoring, polar solve, fallback, clamp, axis-lock cycling, mouse-angle wrap, precision, snap, numeric parsing, world↔local, status text, flatten plane fit, curve chains and polynomial/Fourier fits. If a function is worth writing, it is worth a pytest. Keep that logic in `core/` so tests run without Blender.
- **Every new bug gets a regression test that fails before the fix and passes after.** Reproduce with the smallest numeric fixture (points, rails, axis, theta). Do not patch and move on. If a regression is truly impractical (live GPU handler, window event timing), say why in the handoff **and** still extract the logic so the next similar bug can be unit-tested.
- Run `pytest` before calling a milestone done. `scripts/validate_addon.py` covers registration, keymap, poll, execute, and reload — it does not replace unit tests.
- Do not special-case a user `.blend` in tests. Use generic synthetic geometry.

```sh
./scripts/run-unittests.sh
"/Applications/Blender 5.1.app/Contents/MacOS/blender" \
 --factory-startup -b --python scripts/validate_addon.py
```

## Where code lives

| Area | Path |
| --- | --- |
| Vectors / matrices | `core/vec.py` |
| Rail solve, clamp, overlay segments, flatten plane | `core/geometry.py` |
| Loop/path walking, polynomial/Fourier curve fit | `core/curve.py` |
| X/Y/Z lock cycling, view-follow mouse sign | `core/axis.py` |
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

## Modal mouse → theta / scale

Unconstrained rotate: screen `atan2` (CCW around the projected pivot) applied around the **view axis**. `_view_axis` is `view_rotation @ (0,0,1)` — toward the camera — which is why free rotate follows the mouse from any side.

Axis lock (rotate): the same screen angle, applied around world/orientation X/Y/Z. If that axis points **away** from the camera, `_theta_from_mouse` multiplies by `mouse_angle_axis_sign` or the gesture reverses after orbiting to the other side of the model. Native `R` does the same flip. Perspective uses camera minus pivot; ortho uses the view axis.

Unconstrained scale: screen projection of the mouse onto the invoke radial around the pivot (`screen_scale_factor`). Crossing the pivot mirrors (negative factor), like native `S`. Do **not** apply `mouse_angle_axis_sign`. Axis lock scales only along that axis, then projects onto the rail.

Flatten: same screen radial as scale (`screen_scale_factor`). Invoke is factor 1 (fully on the plane, like Loop Tools applying immediately). Drag toward the pivot to ease off; 0 is the start pose. Do **not** apply `mouse_angle_axis_sign`. Typed `1` and Redo Last / `execute` with `factor=1` are full flatten. Rails score against the plane normal (best-fit, or the lock axis through the pivot).

Curve: same screen radial as scale (`screen_scale_factor`), but invoke is factor 0 (start pose). Drag away from the pivot toward 1 to approach the fitted curve. Clamp the factor to ``[0, 1]`` (no overshoot). `[` `]` or mouse wheel changes Order; do **not** steal typed digits. X/Y/Z lock fits the curve in that plane through the pivot. Do **not** apply `mouse_angle_axis_sign`. Typed `1` and Redo Last / `execute` with `factor=1` are full curve. Factor 1 is the closest point on each rail to the fitted curve, not the same-parameter sample. Overlay draws the unconstrained curve. The rail solve is closest-point projection of the lerp.

Do **not** flip typed degrees, typed scale factors, typed flatten factors, typed curve factors, or Redo Last (`execute` applies `self.angle` / `self.factor` around the canonical lock axis / flatten plane / fitted curve).

Rails and the polar/scale solve in `core/geometry.py` are view-independent. “Lock follows the mouse on one side only” is the rotate sign, not the solver. Rails are chosen once at invoke for the then-current axis and mode.

| Symptom | First look |
| --- | --- |
| Unconstrained OK, lock reversed after orbit | `mouse_angle_axis_sign`, `_theta_from_mouse` |
| Scale reversed after orbit | should not happen; check `_factor_from_mouse` |
| Flatten reversed after orbit | should not happen; check `_factor_from_mouse` |
| Curve reversed after orbit | should not happen; check `_factor_from_mouse` |
| Nothing moves | rails / freeze / whole mesh selected; scale on a tangent-only loop |
| Wrong in Top/Front/Right unconstrained | `_view_axis` |
| Keymap / reload / poll | `__init__.py`, `scripts/validate_addon.py` |

## Do not

- Commit, push, tag, or release unless explicitly asked (use `./scripts/release.sh` when asked to release).
- Unregister the add-on from inside an operator execute (use `schedule_reload()`).
- Steal `R`, `S`, `Shift+R`, `Ctrl+R`, `Shift+Ctrl+R`, or `Shift+Alt+S` (To Sphere). Default shortcut is **Shift+Alt+R** on the Mesh keymap, which opens the Slide pie.
