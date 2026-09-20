# Manual checks

- Grid: select a horizontal loop, Shift+Alt+R, pick Rotate (or tap R); vertices travel on vertical rails.
- Scale: select verts with outgoing edges away from the pivot, Shift+Alt+R, tap S; they slide along those radials.
- Flatten: select a wavy loop with outgoing edges, Shift+Alt+R, tap F; verts slide onto the best-fit plane. Drag toward the pivot to ease off. Press Z to flatten onto the pivot's XY plane instead.
- Subdivided face: select the face including interior verts; they follow the same through-rails as the boundary instead of in-face edges.
- Right/Front/Top ortho: free rotation is around the view axis (same as `R`).
- Press `X` / `Y` / `Z` while dragging; header follows View → orientation → Global/Local, and a thick anti-aliased axis line in native-R colors appears through the pivot.
- Axis lock still follows the mouse after orbiting 180° around the model (same as native `R`).
- Active Element pivot: the active vertex stays put.
- `C` clamps to the physical rail; default extend continues past the edge.
- Object with rotation and non-uniform scale still follows world-space rails.
- Esc restores the start pose; Undo after confirm is one step.
- Reload from the sidebar after a Python edit (linked checkout only).
