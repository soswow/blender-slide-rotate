"""Rail selection and angle-preserving slide solve (no bpy).

Each selected vertex is locked to one cached guide rail. A shared rotation
angle ``theta`` around a pivot/axis moves every vertex along its own rail.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .types import Rail, VertexRailState
from .vec import (
    EPS,
    Vec3,
    add,
    almost_equal,
    cross,
    dot,
    length,
    length_squared,
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


def choose_rail(
    vertex_world: Vec3,
    others: list[Vec3],
    pivot: Vec3,
    axis: Vec3,
) -> Rail | None:
    """Pick one bidirectional rail from unselected-end neighbors.

    Opposite colinear neighbors (typical mid-loop) become one clamp interval
    spanning both segments. Rails are scored against the rotation-plane tangent
    and cached by the caller — they must not change while the mouse moves.
    """
    candidates: list[CandidateEdge] = []
    for other in others:
        candidate = _candidate_from_other(vertex_world, other)
        if candidate is not None:
            candidates.append(candidate)
    if not candidates:
        return None

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

    tangent = rotational_tangent(pivot, vertex_world, axis)
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
    return best


def is_near_pivot(point: Vec3, pivot: Vec3) -> bool:
    return length_squared(sub(point, pivot)) <= NEAR_PIVOT_EPS


def build_vertex_state(
    index: int,
    local: Vec3,
    world: Vec3,
    neighbor_worlds: list[Vec3],
    pivot: Vec3,
    axis: Vec3,
) -> VertexRailState:
    if is_near_pivot(world, pivot):
        return VertexRailState(
            index=index,
            original_world=world,
            original_local=local,
            rail=None,
            movable=False,
        )
    rail = choose_rail(world, neighbor_worlds, pivot, axis)
    return VertexRailState(
        index=index,
        original_world=world,
        original_local=local,
        rail=rail,
        movable=rail is not None,
    )


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
