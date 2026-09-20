"""Rail selection and slide solve for rotate, scale, and flatten (no bpy).

Each selected vertex is locked to one cached guide rail. Rotate shares an
angle ``theta`` around a pivot/axis. Scale shares a factor from the pivot.
Flatten shares a factor toward a plane (0 = start pose, 1 = on the plane).
All three write a parameter ``t`` along the same cached rail.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .types import MODE_FLATTEN, MODE_ROTATE, MODE_SCALE, Rail, VertexRailState
from .vec import (
    EPS,
    Mat3,
    Vec3,
    add,
    almost_equal,
    cross,
    dot,
    length,
    length_squared,
    lerp,
    normalize,
    plane_basis,
    project_to_plane,
    rotate_around_axis,
    scale,
    sub,
)

# Cross-product magnitude below this uses closest-point projection instead of
# the polar-angle intersection (near-parallel rotated radial vs rail).
PARALLEL_EPS = 1e-5
# Vertices this close to the pivot have no well-defined tangent; freeze them.
NEAR_PIVOT_EPS = 1e-8
# Reject zero-length candidate edges.
MIN_EDGE_LENGTH = 1e-8
# Treat two outgoing rails as one bidirectional line when aligned this closely.
COLINEAR_DOT = 0.999
# Extreme intersections are treated as unstable and fall back to projection.
MAX_ABS_T = 1.0e6


@dataclass(frozen=True)
class CandidateEdge:
    """One unselected-end edge leaving a selected vertex."""

    other_world: Vec3
    length: float
    direction: Vec3


def clamp_t(value: float, rail: Rail, extend_rails: bool) -> float:
    if extend_rails:
        return value
    return min(max(value, rail.t_min), rail.t_max)


def rotational_tangent(pivot: Vec3, point: Vec3, axis: Vec3) -> Vec3 | None:
    return normalize(cross(axis, sub(point, pivot)))


def rail_score_direction(
    pivot: Vec3,
    point: Vec3,
    axis: Vec3,
    mode: str = MODE_ROTATE,
    axis_locked: bool = False,
) -> Vec3 | None:
    """Direction used to pick a rail for the current Slide mode.

    Rotate scores against the rotational tangent in the plane of ``axis``.
    Scale scores against the 3D radial from the pivot, or against the lock
    axis once X/Y/Z is active (native S then only moves along that axis).
    Flatten scores against the plane normal (``axis`` is that normal).
    """
    if mode == MODE_FLATTEN:
        return normalize(axis)
    if mode == MODE_SCALE:
        if axis_locked:
            return normalize(axis)
        return normalize(sub(point, pivot))
    return rotational_tangent(pivot, point, axis)


def unconstrained_scaled_point(
    original: Vec3,
    pivot: Vec3,
    axis: Vec3,
    factor: float,
    axis_locked: bool,
) -> Vec3:
    """Native-S pose before projecting onto the rail."""
    radial = sub(original, pivot)
    if not axis_locked:
        return add(pivot, scale(radial, factor))
    unit = normalize(axis)
    if unit is None:
        return add(pivot, scale(radial, factor))
    along = dot(radial, unit)
    rest = sub(radial, scale(unit, along))
    return add(pivot, add(scale(unit, along * factor), rest))


def unconstrained_flattened_point(
    original: Vec3,
    plane_origin: Vec3,
    plane_normal: Vec3,
    factor: float,
) -> Vec3:
    """Lerp from the start pose toward the closest point on the flatten plane."""
    return lerp(original, project_to_plane(original, plane_origin, plane_normal), factor)


def _symmetric_eigensystem_3(matrix: Mat3) -> tuple[tuple[float, float, float], tuple[Vec3, Vec3, Vec3]]:
    """Jacobi eigenvalues (ascending) and matching eigenvectors of a 3x3 symmetric matrix."""
    a = [list(row) for row in matrix]
    vectors = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    for _ in range(50):
        off_max = 0.0
        p_index = 0
        q_index = 1
        for i_index, j_index in ((0, 1), (0, 2), (1, 2)):
            value = abs(a[i_index][j_index])
            if value > off_max:
                off_max = value
                p_index, q_index = i_index, j_index
        if off_max <= 1e-12:
            break
        app = a[p_index][p_index]
        aqq = a[q_index][q_index]
        apq = a[p_index][q_index]
        diff = aqq - app
        if abs(apq) <= abs(diff) * 1e-12:
            tangent = apq / diff if abs(diff) > EPS else 0.0
        else:
            phi = 0.5 * diff / apq
            tangent = 1.0 / (abs(phi) + math.sqrt(phi * phi + 1.0))
            if phi < 0.0:
                tangent = -tangent
        cosine = 1.0 / math.sqrt(tangent * tangent + 1.0)
        sine = tangent * cosine
        for k_index in range(3):
            if k_index in {p_index, q_index}:
                continue
            aik = a[k_index][p_index]
            aiq = a[k_index][q_index]
            a[k_index][p_index] = a[p_index][k_index] = cosine * aik - sine * aiq
            a[k_index][q_index] = a[q_index][k_index] = sine * aik + cosine * aiq
        a[p_index][p_index] = cosine * cosine * app - 2.0 * sine * cosine * apq + sine * sine * aqq
        a[q_index][q_index] = sine * sine * app + 2.0 * sine * cosine * apq + cosine * cosine * aqq
        a[p_index][q_index] = a[q_index][p_index] = 0.0
        for k_index in range(3):
            vip = vectors[k_index][p_index]
            viq = vectors[k_index][q_index]
            vectors[k_index][p_index] = cosine * vip - sine * viq
            vectors[k_index][q_index] = sine * vip + cosine * viq
    ranked = sorted(((a[index][index], index) for index in range(3)), key=lambda item: item[0])
    values = (ranked[0][0], ranked[1][0], ranked[2][0])
    axes = tuple(
        (vectors[0][column], vectors[1][column], vectors[2][column]) for _value, column in ranked
    )
    return values, axes


def best_fit_plane(points: list[Vec3]) -> tuple[Vec3, Vec3] | None:
    """Least-squares plane ``(centroid, unit_normal)``, or None if coincident/collinear.

    The normal is the covariance eigenvector of smallest eigenvalue, the same
    fit Loop Tools Flatten uses before projecting vertices.
    """
    if len(points) < 3:
        return None
    count = float(len(points))
    origin = (
        sum(point[0] for point in points) / count,
        sum(point[1] for point in points) / count,
        sum(point[2] for point in points) / count,
    )
    xx = xy = xz = yy = yz = zz = 0.0
    for point in points:
        dx, dy, dz = sub(point, origin)
        xx += dx * dx
        xy += dx * dy
        xz += dx * dz
        yy += dy * dy
        yz += dy * dz
        zz += dz * dz
    values, axes = _symmetric_eigensystem_3(
        (
            (xx, xy, xz),
            (xy, yy, yz),
            (xz, yz, zz),
        )
    )
    if values[2] <= EPS:
        return None
    if values[1] <= values[2] * 1e-8 + EPS:
        return None
    normal = normalize(axes[0])
    if normal is None:
        return None
    return origin, normal


def polar_angle(point: Vec3, pivot: Vec3, axis: Vec3) -> float | None:
    basis = plane_basis(axis)
    if basis is None:
        return None
    first, second = basis
    projected = project_to_plane(point, pivot, axis)
    delta = sub(projected, pivot)
    x_coord = dot(delta, first)
    y_coord = dot(delta, second)
    if x_coord * x_coord + y_coord * y_coord <= NEAR_PIVOT_EPS:
        return None
    return math.atan2(y_coord, x_coord)


def project_t_on_rail(point: Vec3, rail: Rail) -> float:
    """Closest-point parameter of ``point`` on the infinite rail line."""
    return dot(sub(point, rail.origin), rail.direction)


def solve_rail_parameter(
    pivot: Vec3,
    axis: Vec3,
    theta: float,
    original: Vec3,
    rail: Rail,
    last_t: float,
) -> tuple[float, bool]:
    """Return ``(t, used_fallback)`` for one vertex at angle ``theta``.

    Preferred: intersect the rotated radial line with the rail in the rotation
    plane, then apply that ``t`` on the real 3D rail. Fallback: project the
    unconstrained rotated point onto the rail when the intersection is unstable.
    """
    fallback_point = rotate_around_axis(original, pivot, axis, theta)
    fallback_t = project_t_on_rail(fallback_point, rail)

    basis = plane_basis(axis)
    if basis is None:
        return last_t, True
    first, second = basis

    original_angle = polar_angle(original, pivot, axis)
    if original_angle is None:
        return last_t, True
    target_angle = original_angle + theta
    target_2d = (math.cos(target_angle), math.sin(target_angle))

    origin_projected = project_to_plane(rail.origin, pivot, axis)
    direction_projected = sub(
        project_to_plane(add(rail.origin, rail.direction), pivot, axis),
        origin_projected,
    )
    point_2d = (
        dot(sub(origin_projected, pivot), first),
        dot(sub(origin_projected, pivot), second),
    )
    direction_2d = (
        dot(direction_projected, first),
        dot(direction_projected, second),
    )
    dir_len_sq = direction_2d[0] * direction_2d[0] + direction_2d[1] * direction_2d[1]
    if dir_len_sq <= PARALLEL_EPS * PARALLEL_EPS:
        return fallback_t, True
    # Radial rail: the line goes through the pivot, so every polar hit is the
    # pivot. Project unconstrained R onto the rail instead of snapping.
    cross_origin = point_2d[0] * direction_2d[1] - point_2d[1] * direction_2d[0]
    if cross_origin * cross_origin <= NEAR_PIVOT_EPS * dir_len_sq:
        return fallback_t, True
    cross_target = direction_2d[0] * target_2d[1] - direction_2d[1] * target_2d[0]
    if abs(cross_target) < PARALLEL_EPS:
        return fallback_t, True
    # s * target = point_2d + t * direction_2d  →  t = -(point × target) / (dir × target)
    t_value = -(point_2d[0] * target_2d[1] - point_2d[1] * target_2d[0]) / cross_target
    if not math.isfinite(t_value) or abs(t_value) > MAX_ABS_T:
        return fallback_t, True
    return t_value, False


def point_on_rail(rail: Rail, t_value: float) -> Vec3:
    return add(rail.origin, scale(rail.direction, t_value))


def apply_vertex_theta(
    state: VertexRailState,
    pivot: Vec3,
    axis: Vec3,
    theta: float,
    extend_rails: bool,
) -> VertexRailState:
    """Recompute one vertex from its original pose plus the shared angle."""
    if not state.movable or state.rail is None:
        state.last_t = 0.0
        state.used_fallback = False
        return state
    t_value, used_fallback = solve_rail_parameter(
        pivot,
        axis,
        theta,
        state.original_world,
        state.rail,
        state.last_t,
    )
    t_value = clamp_t(t_value, state.rail, extend_rails)
    state.last_t = t_value
    state.used_fallback = used_fallback
    return state


def solve_scale_rail_parameter(
    pivot: Vec3,
    axis: Vec3,
    factor: float,
    original: Vec3,
    rail: Rail,
    axis_locked: bool,
) -> tuple[float, bool]:
    """Return ``(t, used_fallback)`` for one vertex at scale ``factor``.

    Unconstrained: closest-point projection of the native-S pose onto the rail.
    Axis lock: intersect the rail with the plane whose lock-axis coordinate
    matches that pose (so Y-lock factor 0 puts every vertex on the pivot Y,
    even when the rail is slightly tilted). Fallback to projection if the
    rail is parallel to the plane.
    """
    target = unconstrained_scaled_point(original, pivot, axis, factor, axis_locked)
    fallback_t = project_t_on_rail(target, rail)
    if not axis_locked:
        return fallback_t, False
    unit = normalize(axis)
    if unit is None:
        return fallback_t, True
    denom = dot(rail.direction, unit)
    if abs(denom) < PARALLEL_EPS:
        return fallback_t, True
    t_value = (dot(target, unit) - dot(rail.origin, unit)) / denom
    if not math.isfinite(t_value) or abs(t_value) > MAX_ABS_T:
        return fallback_t, True
    return t_value, False


def apply_vertex_scale(
    state: VertexRailState,
    pivot: Vec3,
    axis: Vec3,
    factor: float,
    extend_rails: bool,
    axis_locked: bool,
) -> VertexRailState:
    """Recompute one vertex from its original pose plus the shared scale factor."""
    if not state.movable or state.rail is None:
        state.last_t = 0.0
        state.used_fallback = False
        return state
    t_value, used_fallback = solve_scale_rail_parameter(
        pivot,
        axis,
        factor,
        state.original_world,
        state.rail,
        axis_locked,
    )
    t_value = clamp_t(t_value, state.rail, extend_rails)
    state.last_t = t_value
    state.used_fallback = used_fallback
    return state


def solve_flatten_rail_parameter(
    plane_origin: Vec3,
    plane_normal: Vec3,
    factor: float,
    original: Vec3,
    rail: Rail,
) -> tuple[float, bool]:
    """Return ``(t, used_fallback)`` for one vertex at flatten ``factor``.

    Preferred: intersect the rail with the plane that interpolates the vertex's
    signed distance (factor 1 lands on the flatten plane). Fallback: closest
    point of the unconstrained lerp when the rail is parallel to the plane.
    """
    target = unconstrained_flattened_point(original, plane_origin, plane_normal, factor)
    fallback_t = project_t_on_rail(target, rail)
    unit = normalize(plane_normal)
    if unit is None:
        return fallback_t, True
    denom = dot(rail.direction, unit)
    if abs(denom) < PARALLEL_EPS:
        return fallback_t, True
    original_distance = dot(sub(original, plane_origin), unit)
    target_distance = original_distance * (1.0 - factor)
    t_value = (target_distance - dot(sub(rail.origin, plane_origin), unit)) / denom
    if not math.isfinite(t_value) or abs(t_value) > MAX_ABS_T:
        return fallback_t, True
    return t_value, False


def apply_vertex_flatten(
    state: VertexRailState,
    plane_origin: Vec3,
    plane_normal: Vec3,
    factor: float,
    extend_rails: bool,
) -> VertexRailState:
    """Recompute one vertex from its original pose plus the shared flatten factor."""
    if not state.movable or state.rail is None:
        state.last_t = 0.0
        state.used_fallback = False
        return state
    t_value, used_fallback = solve_flatten_rail_parameter(
        plane_origin,
        plane_normal,
        factor,
        state.original_world,
        state.rail,
    )
    t_value = clamp_t(t_value, state.rail, extend_rails)
    state.last_t = t_value
    state.used_fallback = used_fallback
    return state


def apply_vertex_slide(
    state: VertexRailState,
    pivot: Vec3,
    axis: Vec3,
    value: float,
    extend_rails: bool,
    mode: str,
    axis_locked: bool,
    plane_origin: Vec3 | None = None,
) -> VertexRailState:
    if mode == MODE_FLATTEN:
        origin = plane_origin if plane_origin is not None else pivot
        return apply_vertex_flatten(state, origin, axis, value, extend_rails)
    if mode == MODE_SCALE:
        return apply_vertex_scale(state, pivot, axis, value, extend_rails, axis_locked)
    return apply_vertex_theta(state, pivot, axis, value, extend_rails)


def transformed_world(state: VertexRailState) -> Vec3:
    if not state.movable or state.rail is None:
        return state.original_world
    return point_on_rail(state.rail, state.last_t)


def score_rail(direction: Vec3, tangent: Vec3 | None) -> float:
    if tangent is None:
        return 0.0
    unit = normalize(direction)
    if unit is None:
        return 0.0
    return abs(dot(unit, tangent))


def _candidate_from_other(vertex_world: Vec3, other_world: Vec3) -> CandidateEdge | None:
    offset = sub(other_world, vertex_world)
    edge_length = length(offset)
    if edge_length < MIN_EDGE_LENGTH:
        return None
    direction = scale(offset, 1.0 / edge_length)
    return CandidateEdge(other_world=other_world, length=edge_length, direction=direction)


def _try_merge_colinear(vertex_world: Vec3, first: CandidateEdge, second: CandidateEdge) -> Rail | None:
    alignment = dot(first.direction, second.direction)
    if abs(abs(alignment) - 1.0) > (1.0 - COLINEAR_DOT):
        return None
    if alignment > 0.0:
        # Same direction: keep the longer physical segment only.
        chosen = first if first.length >= second.length else second
        return Rail(
            origin=vertex_world,
            direction=chosen.direction,
            t_min=0.0,
            t_max=chosen.length,
            merged=False,
        )
    return Rail(
        origin=vertex_world,
        direction=first.direction,
        t_min=-second.length,
        t_max=first.length,
        merged=True,
    )


def _rails_from_others(vertex_world: Vec3, others: list[Vec3]) -> list[Rail]:
    candidates: list[CandidateEdge] = []
    for other in others:
        candidate = _candidate_from_other(vertex_world, other)
        if candidate is not None:
            candidates.append(candidate)
    if not candidates:
        return []

    rails: list[Rail] = []
    used: set[int] = set()
    for index, first in enumerate(candidates):
        if index in used:
            continue
        merged = None
        partner = None
        for other_index in range(index + 1, len(candidates)):
            if other_index in used:
                continue
            merged = _try_merge_colinear(vertex_world, first, candidates[other_index])
            if merged is not None and merged.merged:
                partner = other_index
                break
            merged = None
        if merged is not None and partner is not None:
            used.add(index)
            used.add(partner)
            rails.append(merged)
        else:
            used.add(index)
            rails.append(
                Rail(
                    origin=vertex_world,
                    direction=first.direction,
                    t_min=0.0,
                    t_max=first.length,
                    merged=False,
                )
            )
    return rails


def _best_rail(rails: list[Rail], tangent: Vec3 | None) -> tuple[Rail | None, float]:
    best: Rail | None = None
    best_score = -1.0
    for rail in rails:
        score = score_rail(rail.direction, tangent)
        # Prefer a merged bidirectional rail when scores tie.
        if score > best_score + 1e-9 or (
            abs(score - best_score) <= 1e-9 and rail.merged and (best is None or not best.merged)
        ):
            best = rail
            best_score = score
    return best, best_score if best is not None else 0.0


def choose_rail(
    vertex_world: Vec3,
    others: list[Vec3],
    pivot: Vec3,
    axis: Vec3,
    borrowed_others: list[Vec3] | None = None,
    mode: str = MODE_ROTATE,
    axis_locked: bool = False,
) -> Rail | None:
    """Pick one bidirectional rail from unselected-end neighbors.

    Opposite colinear neighbors (typical mid-loop) become one clamp interval
    spanning both segments. Rails are scored against the mode's guide
    direction and cached by the caller — they must not change while the
    mouse moves.

    ``borrowed_others`` are extra endpoints copied from coplanar face-island
    edges that leave the surface. They are used only when the vertex has no
    unselected 1-ring neighbor (typical face-interior: every linked vert is
    also selected). Existing outgoing edges always win, even if they score
    poorly against the rotational tangent — otherwise a loop vertex that
    happens to sit on the pivot's lock-axis plane would slide on a phantom
    through-rail instead of its real edges.
    """
    guide = rail_score_direction(pivot, vertex_world, axis, mode, axis_locked)
    rail, _score = _best_rail(_rails_from_others(vertex_world, others), guide)
    if rail is not None:
        return rail
    if borrowed_others:
        borrowed_rail, _borrowed_score = _best_rail(
            _rails_from_others(vertex_world, borrowed_others),
            guide,
        )
        if borrowed_rail is not None:
            return borrowed_rail
    return rail


def is_near_pivot(point: Vec3, pivot: Vec3) -> bool:
    return length_squared(sub(point, pivot)) <= NEAR_PIVOT_EPS


def build_vertex_state(
    index: int,
    local: Vec3,
    world: Vec3,
    neighbor_worlds: list[Vec3],
    pivot: Vec3,
    axis: Vec3,
    borrowed_worlds: list[Vec3] | None = None,
    mode: str = MODE_ROTATE,
    axis_locked: bool = False,
) -> VertexRailState:
    if mode != MODE_FLATTEN and is_near_pivot(world, pivot):
        return VertexRailState(
            index=index,
            original_world=world,
            original_local=local,
            rail=None,
            movable=False,
        )
    rail = choose_rail(
        world,
        neighbor_worlds,
        pivot,
        axis,
        borrowed_worlds,
        mode=mode,
        axis_locked=axis_locked,
    )
    return VertexRailState(
        index=index,
        original_world=world,
        original_local=local,
        rail=rail,
        movable=rail is not None,
    )


def overlay_axis_segment(
    pivot: Vec3,
    axis: Vec3,
    half_length: float,
) -> tuple[Vec3, Vec3] | None:
    """World-space endpoints of a line through ``pivot`` along ``axis``.

    ``half_length`` is large enough in the overlay that the GPU clip planes
    make it look infinite, like native R axis lock.
    """
    unit = normalize(axis)
    if unit is None or half_length <= 0.0:
        return None
    offset = scale(unit, half_length)
    return sub(pivot, offset), add(pivot, offset)


def overlay_segment(rail: Rail, extend_rails: bool, pad: float = 2.0) -> tuple[Vec3, Vec3]:
    """World-space endpoints for the modal rail overlay."""
    if extend_rails:
        start_t = min(rail.t_min, -pad)
        end_t = max(rail.t_max, pad)
    else:
        start_t = rail.t_min
        end_t = rail.t_max
    return point_on_rail(rail, start_t), point_on_rail(rail, end_t)


def almost_colinear(first: Vec3, second: Vec3) -> bool:
    unit_a = normalize(first)
    unit_b = normalize(second)
    if unit_a is None or unit_b is None:
        return False
    return abs(abs(dot(unit_a, unit_b)) - 1.0) <= (1.0 - COLINEAR_DOT)


def rails_equal(left: Rail, right: Rail, tolerance: float = 1e-6) -> bool:
    same_dir = almost_equal(left.direction, right.direction, tolerance) or almost_equal(
        left.direction,
        scale(right.direction, -1.0),
        tolerance,
    )
    return (
        almost_equal(left.origin, right.origin, tolerance)
        and same_dir
        and abs(left.t_min - right.t_min) <= tolerance
        and abs(left.t_max - right.t_max) <= tolerance
    )
