# Geometry

How Slide Tools chooses rails and moves vertices. Coordinates are solved in world space and written back to BMesh local space so rotated and non-uniformly scaled objects stay correct.

## Shared parameter

One value drives every vertex:

- Rotate: angle `theta`
- Scale: `factor`
- Flatten: `factor` (`0` = start pose, `1` = on the plane)

Each vertex is assigned a rail **once at invoke, and again if you lock X/Y/Z**. Rails are outgoing edges to unselected vertices, scored against the rotational tangent, the scale radial, or the flatten-plane normal. Opposite colinear neighbors are merged into one bidirectional rail so Clamp works in both directions, like a mid-loop slide.

## Interior vertices

Vertices sitting inside a subdivided face often have no 1-ring edge in the rotation direction. If every connected neighbor is a poor match for the rotational tangent, Slide Tools copies rails from the coplanar face island: edges that leave that surface (the through-edges the boundary already has). Those borrowed rails are scored the same way, so interior verts can slide with the face instead of crawling along in-face edges.

## Solvers

**Rotate** intersects the rotated radial line with the rail in the current rotation plane (view axis by default), then applies that parameter on the real 3D rail. If the intersection is parallel, near the pivot, or numerically explosive, it falls back to projecting the unconstrained rotated point onto the rail.

**Scale** projects the unconstrained native-S pose (uniform from the pivot) onto the rail. With X/Y/Z lock, it instead slides each vertex along its rail until the locked coordinate matches native S — so Y-lock at scale 0 lands every vertex on the pivot's Y, even if the rail is slightly tilted.

**Flatten** intersects each rail with the plane that interpolates that vertex's signed distance (factor 1 lands on the plane). Unconstrained Flatten uses the selection's best-fit plane; X/Y/Z lock uses that axis through the transform pivot.

Vertices with no rail, or the active pivot vertex itself (Rotate/Scale only), stay still. Flatten still moves a vertex that sits on the pivot, as long as it has a rail.
