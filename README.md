# Slide Rotate

Blender 5.1 Edit Mode operator: rotate a vertex/edge/face selection around the current transform pivot while each vertex stays on a connected **guide rail**.

It should feel like native `R`, except vertices can only travel along automatically chosen surrounding edges (like a rotation-driven edge slide).

## Requirements

- Blender 5.1 or newer

## Installation

Download a zip or use this checkout.

**From Disk:** Blender **Edit → Preferences → Get Extensions → Install from Disk**, then enable **Slide Rotate**.

**Development (no zip):**

```sh
./scripts/link-dev.sh
```

That symlinks this repo to `~/Library/Application Support/Blender/5.1/extensions/user_default/slide_rotate`. Enable **Slide Rotate** once. After edits, click **Reload Slide Rotate** at the bottom of the 3D View **Slide Rotate** sidebar (or F3). Watch the system console for `Slide Rotate: reloaded from disk`. Restart Blender after RNA property schema changes.

## Invoke

- Shortcut: **Shift+Alt+R** in Mesh Edit Mode
- Menu: **Vertex → Slide Rotate** or **Edge → Slide Rotate**
- Search: **F3 → Slide Rotate**
- Sidebar: **3D View → Slide Rotate → Slide Rotate**

Native `R` is unchanged.

## Usage

1. Enter Edit Mode and select a loop, vertices, or edges.
2. Set the transform pivot (Median, 3D Cursor, Active Element, or Bounding Box Center).
3. Start Slide Rotate and move the mouse like `R`.
4. Left-click or Enter confirms. Right-click or Esc cancels.

While dragging:

| Key | Action |
| --- | --- |
| Mouse | Change angle around the projected pivot |
| Shift | Precision |
| Ctrl | Angle snap (scene 3D increment; Shift+Ctrl uses the precision increment) |
| C | Toggle Clamp / Extend Rails (extend is the default) |
| X / Y / Z | Axis lock like native `R` (orientation → Global/Local flip → View) |
| 0–9, `.`, `-` | Type an angle in degrees |
| Backspace | Edit typed input |

The header shows the angle, axis, and clamp state. Yellow overlay lines are the cached rails.

## Geometry

One shared angle `theta` drives every vertex. Each vertex is assigned a rail **once at invoke** (outgoing edges to unselected vertices, scored against the rotational tangent). Opposite colinear neighbors are merged into one bidirectional rail so Clamp works in both directions, like a mid-loop slide.

The solver intersects the rotated radial line with the rail in the current rotation plane (view axis by default), then applies that parameter on the real 3D rail. If the intersection is parallel, near the pivot, or numerically explosive, it falls back to projecting the unconstrained rotated point onto the rail. Vertices with no rail, or the active pivot vertex itself, stay still.

Coordinates are solved in world space and written back to BMesh local space so rotated and non-uniformly scaled objects stay correct.

## Limitations

- Individual Origins falls back to median.
- No Trackball (`R R`), geometry snapping, UV correction, proportional editing, or mid-gesture rail cycling.
- Selecting the entire connected mesh leaves no outgoing rails, so nothing moves.
- Simple numeric input only (no units or expressions).
- Custom transform orientations use the orientation matrix when Blender exposes it; Normal uses averaged selected vertex normals.

## Development tests

```sh
python3 -m pytest
"/Applications/Blender 5.1.app/Contents/MacOS/blender" \
  --factory-startup -b --python scripts/validate_addon.py
```

See [AGENTS.md](AGENTS.md) for changelog and unit-test rules, and [MILESTONES.md](MILESTONES.md) for session progress.

## Manual checks

- Grid: select a horizontal loop, Shift+Alt+R, vertices travel on vertical rails.
- Right/Front/Top ortho: free rotation is around the view axis (same as `R`).
- Press `X` / `Y` / `Z` while dragging; header follows View → orientation → Global/Local.
- Active Element pivot: the active vertex stays put.
- `C` clamps to the physical rail; default extend continues past the edge.
- Object with rotation and non-uniform scale still follows world-space rails.
- Esc restores the start pose; Undo after confirm is one step.
- Reload from the sidebar after a Python edit (linked checkout only).

## License

[GPL-3.0-or-later](LICENSE)
