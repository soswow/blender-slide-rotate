# Manual checks

- Grid: select a horizontal loop, Shift+Alt+R, pick Rotate (or tap R); vertices travel on vertical rails.
- Scale: select verts with outgoing edges away from the pivot, Shift+Alt+R, tap S; they slide along those radials.
- Flatten: select a wavy loop with outgoing edges, Shift+Alt+R, tap F; verts slide onto the best-fit plane. Drag toward the pivot to ease off. Press Z to flatten onto the pivot's XY plane instead.
- Curve: select a wavy loop (not a filled face) with outgoing edges, Shift+Alt+R, tap C; verts stay put at factor 0. Drag away from the pivot (or type `1`) to slide toward the fitted line. `[` / `]` changes Order; the light-blue overlay is the imaginary curve.
- Subdivided face: select the face including interior verts; they follow the same through-rails as the boundary instead of in-face edges.
- Loop with Active Element: verts that sit in the lock-axis plane of the active vert still slide on their own outgoing edges, not through the face.
- Right/Front/Top ortho: free rotation is around the view axis (same as `R`).
- Press `X` / `Y` / `Z` while dragging; header follows View → orientation → Global/Local, and a thick anti-aliased axis line in native-R colors appears through the pivot.
- Axis lock still follows the mouse after orbiting 180° around the model (same as native `R`).
- Active Element pivot: the active vertex stays put.
- `C` clamps to the physical rail; default extend continues past the edge.
- Object with rotation and non-uniform scale still follows world-space rails.
- Esc restores the start pose; Undo after confirm is one step.
- Reload from the sidebar after a Python edit (linked checkout only).
