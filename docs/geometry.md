# Geometry

How Slide Tools chooses rails and moves vertices. Coordinates are solved in world space and written back to BMesh local space so rotated and non-uniformly scaled objects stay correct.

## Shared parameter

One value drives every vertex:

- Rotate: angle `theta`
- Scale: `factor`
- Flatten: `factor` (`0` = start pose, `1` = on the plane)
- Curve: `factor` (`0` = start pose, `1` = on the fitted curve)

Each vertex is assigned a rail **once at invoke, and again if you lock X/Y/Z** (or change Curve order). Rails are outgoing edges to unselected vertices, scored against the rotational tangent, the scale radial, the flatten-plane normal, or the vector toward that vertex's curve sample. Opposite colinear neighbors are merged into one bidirectional rail so Clamp works in both directions, like a mid-loop slide.

## Interior vertices

Vertices sitting inside a fully selected subdivided face have no unselected 1-ring edge. Slide Tools then copies rails from the coplanar face island: edges that leave that surface (the through-edges the boundary already has). Those borrowed rails are scored the same way, so interior verts can slide with the face.

If a vertex still has an outgoing edge to an unselected neighbor, that edge is the rail — even when it is a poor match for the rotational tangent. That keeps a loop sliding on existing edges when some verts sit in the pivot's lock-axis plane (the tangent is then perpendicular to the loop rails).

## Solvers

**Rotate** intersects the rotated radial line with the rail in the current rotation plane (view axis by default), then applies that parameter on the real 3D rail. If the intersection is parallel, the rail runs through the pivot in that plane (polar would snap onto the pivot), or the hit is numerically explosive, it falls back to projecting the unconstrained rotated point onto the rail. That fallback eases along the edge (`cos` of the angle) instead of jumping.

**Scale** projects the unconstrained native-S pose (uniform from the pivot) onto the rail. With X/Y/Z lock, it instead slides each vertex along its rail until the locked coordinate matches native S — so Y-lock at scale 0 lands every vertex on the pivot's Y, even if the rail is slightly tilted.

**Flatten** intersects each rail with the plane that interpolates that vertex's signed distance (factor 1 lands on the plane). Unconstrained Flatten uses the selection's best-fit plane; X/Y/Z lock uses that axis through the transform pivot.

**Curve** walks selected-selected edges into open paths and closed loops. Open paths get a polynomial that is pinned at the ends. Closed loops get a trigonometric polynomial (Fourier harmonics). Order is how much shape that imaginary line may keep. Each vertex lerps toward the point on its rail that comes closest to the fitted curve (not the same-parameter sample on that curve — those often sit off the rail, so verts would barely move). The blue overlay is still the unconstrained imaginary line. X/Y/Z lock fits the curve in that plane through the pivot. Invoke is factor 0.

Vertices with no rail, or the active pivot vertex itself (Rotate/Scale only), stay still. Flatten and Curve still move a vertex that sits on the pivot, as long as it has a rail.
