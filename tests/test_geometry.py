import math

from core.geometry import (
    apply_vertex_flatten,
    apply_vertex_scale,
    apply_vertex_theta,
    best_fit_plane,
    build_vertex_state,
    choose_rail,
    clamp_t,
    overlay_axis_segment,
    overlay_segment,
    solve_rail_parameter,
    transformed_world,
    unconstrained_flattened_point,
    unconstrained_scaled_point,
)
from core.types import MODE_FLATTEN, MODE_SCALE, Rail, VertexRailState
from core.vec import almost_equal


def test_grid_loop_vertical_rails_around_center() -> None:
    """Horizontal loop, vertical rails, pivot at the middle vertex.

    Left/right vertices must slide on Y so a shared theta looks like rotation.
    """
    pivot = (1.0, 0.0, 0.0)
    axis = (0.0, 0.0, 1.0)
    left_rail = choose_rail((0.0, 0.0, 0.0), [(0.0, 1.0, 0.0), (0.0, -1.0, 0.0), (1.0, 0.0, 0.0)], pivot, axis)
    right_rail = choose_rail((2.0, 0.0, 0.0), [(2.0, 1.0, 0.0), (2.0, -1.0, 0.0), (1.0, 0.0, 0.0)], pivot, axis)
    assert left_rail is not None and left_rail.merged
    assert right_rail is not None and right_rail.merged
    assert almost_equal(left_rail.direction, (0.0, 1.0, 0.0)) or almost_equal(
        left_rail.direction,
        (0.0, -1.0, 0.0),
    )

    theta = math.radians(20.0)
    left_t, left_fallback = solve_rail_parameter(pivot, axis, theta, (0.0, 0.0, 0.0), left_rail, 0.0)
    right_t, right_fallback = solve_rail_parameter(pivot, axis, theta, (2.0, 0.0, 0.0), right_rail, 0.0)
    assert not left_fallback and not right_fallback
    left = (left_rail.origin[0], left_rail.origin[1] + left_t * left_rail.direction[1], 0.0)
    right = (right_rail.origin[0], right_rail.origin[1] + right_t * right_rail.direction[1], 0.0)
    assert abs(left[0] - 0.0) < 1e-9
    assert abs(right[0] - 2.0) < 1e-9
    assert left[1] * right[1] < 0.0
    expected = math.tan(theta)
    assert abs(abs(left[1]) - expected) < 1e-6
    assert abs(abs(right[1]) - expected) < 1e-6


def test_choose_rail_prefers_unselected_outgoing() -> None:
    pivot = (0.0, 0.0, 0.0)
    axis = (0.0, 0.0, 1.0)
    # Selected structure along X; vertical neighbor is the rail.
    rail = choose_rail((1.0, 0.0, 0.0), [(1.0, 2.0, 0.0)], pivot, axis)
    assert rail is not None
    assert almost_equal(rail.direction, (0.0, 1.0, 0.0))
    assert abs(rail.t_max - 2.0) < 1e-9


def test_no_rail_freezes_vertex() -> None:
    state = build_vertex_state(
        index=0,
        local=(1.0, 0.0, 0.0),
        world=(1.0, 0.0, 0.0),
        neighbor_worlds=[],
        pivot=(0.0, 0.0, 0.0),
        axis=(0.0, 0.0, 1.0),
    )
    assert state.movable is False
    apply_vertex_theta(state, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.5, True)
    assert transformed_world(state) == (1.0, 0.0, 0.0)


def test_pivot_vertex_is_frozen() -> None:
    pivot = (1.0, 0.0, 0.0)
    state = build_vertex_state(
        index=1,
        local=pivot,
        world=pivot,
        neighbor_worlds=[(1.0, 1.0, 0.0)],
        pivot=pivot,
        axis=(0.0, 0.0, 1.0),
    )
    assert state.movable is False


def test_clamp_stops_at_physical_end() -> None:
    rail = Rail(origin=(0.0, 0.0, 0.0), direction=(0.0, 1.0, 0.0), t_min=0.0, t_max=1.0)
    assert clamp_t(2.5, rail, extend_rails=True) == 2.5
    assert clamp_t(2.5, rail, extend_rails=False) == 1.0
    assert clamp_t(-0.3, rail, extend_rails=False) == 0.0


def test_extend_allows_beyond_edge() -> None:
    pivot = (0.0, 0.0, 0.0)
    axis = (0.0, 0.0, 1.0)
    rail = Rail(origin=(1.0, 0.0, 0.0), direction=(0.0, 1.0, 0.0), t_min=0.0, t_max=0.25)
    t_value, _ = solve_rail_parameter(pivot, axis, math.radians(30.0), (1.0, 0.0, 0.0), rail, 0.0)
    assert t_value > 0.25
    assert clamp_t(t_value, rail, True) == t_value
    assert clamp_t(t_value, rail, False) == 0.25


def test_world_x_axis_rotation_uses_yz_plane() -> None:
    pivot = (0.0, 0.0, 0.0)
    axis = (1.0, 0.0, 0.0)
    original = (0.0, 1.0, 0.0)
    rail = Rail(origin=original, direction=(0.0, 0.0, 1.0), t_min=-2.0, t_max=2.0, merged=True)
    t_value, fallback = solve_rail_parameter(pivot, axis, math.radians(45.0), original, rail, 0.0)
    assert not fallback
    point = (rail.origin[0], rail.origin[1] + t_value * rail.direction[1], rail.origin[2] + t_value * rail.direction[2])
    assert abs(point[0]) < 1e-9
    assert abs(point[1] - 1.0) < 1e-9
    assert abs(point[2] - 1.0) < 1e-6


def test_radial_rail_projects_instead_of_snapping_to_pivot() -> None:
    """Rail through the pivot cannot change heading; project unconstrained R onto it.

    Small angles must stay near the start pose (cosine), not jump to the pivot.
    """
    pivot = (0.0, 0.0, 0.0)
    axis = (0.0, 0.0, 1.0)
    original = (0.0, 1.0, 0.4)
    rail = Rail(origin=original, direction=(0.0, 1.0, 0.0), t_min=-5.0, t_max=5.0, merged=True)
    small = math.radians(10.0)
    t_small, fallback_small = solve_rail_parameter(pivot, axis, small, original, rail, 0.0)
    assert fallback_small
    assert abs(t_small - (math.cos(small) - 1.0)) < 1e-9
    point_small = (rail.origin[0], rail.origin[1] + t_small * rail.direction[1], rail.origin[2])
    assert abs(point_small[0]) < 1e-9
    assert abs(point_small[1] - math.cos(small)) < 1e-9
    assert abs(point_small[1] - 1.0) < 0.02
    assert abs(point_small[1]) > 0.9

    t_quarter, fallback_quarter = solve_rail_parameter(pivot, axis, math.pi / 2.0, original, rail, 0.0)
    assert fallback_quarter
    assert abs(t_quarter - (0.0 - 1.0)) < 1e-9


def test_parallel_radial_falls_back_to_projection() -> None:
    pivot = (0.0, 0.0, 0.0)
    axis = (0.0, 0.0, 1.0)
    original = (1.0, 0.0, 0.0)
    # Rail parallel to the rotated radial at 90 degrees (the Y axis through origin
    # never meets x=1). Solver must not return inf/NaN.
    rail = Rail(origin=original, direction=(0.0, 1.0, 0.0), t_min=-10.0, t_max=10.0)
    t_value, fallback = solve_rail_parameter(pivot, axis, math.pi / 2.0, original, rail, 0.0)
    assert fallback
    assert math.isfinite(t_value)


def test_apply_vertex_writes_last_t() -> None:
    rail = Rail(origin=(1.0, 0.0, 0.0), direction=(0.0, 1.0, 0.0), t_min=-2.0, t_max=2.0, merged=True)
    state = VertexRailState(
        index=0,
        original_world=(1.0, 0.0, 0.0),
        original_local=(1.0, 0.0, 0.0),
        rail=rail,
        movable=True,
    )
    apply_vertex_theta(state, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), math.radians(10.0), True)
    world = transformed_world(state)
    assert abs(world[0] - 1.0) < 1e-9
    assert world[1] != 0.0


def test_overlay_extends_past_physical_when_uncamped() -> None:
    rail = Rail(origin=(0.0, 0.0, 0.0), direction=(1.0, 0.0, 0.0), t_min=0.0, t_max=1.0)
    start, end = overlay_segment(rail, extend_rails=True, pad=2.0)
    assert start[0] <= -2.0
    assert end[0] >= 2.0
    clamped_start, clamped_end = overlay_segment(rail, extend_rails=False)
    assert almost_equal(clamped_start, (0.0, 0.0, 0.0))
    assert almost_equal(clamped_end, (1.0, 0.0, 0.0))


def test_overlay_axis_segment_runs_through_pivot() -> None:
    pivot = (1.0, 2.0, 3.0)
    segment = overlay_axis_segment(pivot, (0.0, 0.0, 2.0), 10.0)
    assert segment is not None
    start, end = segment
    assert almost_equal(start, (1.0, 2.0, -7.0))
    assert almost_equal(end, (1.0, 2.0, 13.0))
    midpoint = (
        0.5 * (start[0] + end[0]),
        0.5 * (start[1] + end[1]),
        0.5 * (start[2] + end[2]),
    )
    assert almost_equal(midpoint, pivot)
    assert overlay_axis_segment(pivot, (0.0, 0.0, 0.0), 10.0) is None
    assert overlay_axis_segment(pivot, (0.0, 1.0, 0.0), 0.0) is None


def test_face_interior_inplane_neighbors_miss_through_rotation() -> None:
    """In-face X/Z edges score 0 against an X-axis hinge; they are the wrong rails."""
    vertex = (0.0, 0.0, 1.0)
    others = [(1.0, 0.0, 1.0), (-1.0, 0.0, 1.0), (0.0, 0.0, 2.0), (0.0, 0.0, 0.0)]
    pivot = (0.0, 0.0, 0.0)
    axis = (1.0, 0.0, 0.0)
    rail = choose_rail(vertex, others, pivot, axis)
    assert rail is not None
    assert abs(rail.direction[1]) < 0.5


def test_face_interior_borrowed_through_rail_wins() -> None:
    """No unselected 1-ring: copied volume-through edges become the rail."""
    vertex = (0.0, 0.0, 1.0)
    borrowed = [(0.0, -2.0, 1.0)]
    pivot = (0.0, 0.0, 0.0)
    axis = (1.0, 0.0, 0.0)
    rail = choose_rail(vertex, [], pivot, axis, borrowed_others=borrowed)
    assert rail is not None
    assert almost_equal(rail.direction, (0.0, -1.0, 0.0)) or almost_equal(
        rail.direction,
        (0.0, 1.0, 0.0),
    )
    assert abs(rail.t_max - 2.0) < 1e-9


def test_borrowed_through_rail_follows_axis() -> None:
    """Physical in-face X wins around Y; with no 1-ring, borrowed through-Y wins around X."""
    vertex = (0.0, 0.0, 1.0)
    others = [(1.0, 0.0, 1.0)]
    borrowed = [(0.0, -2.0, 1.0)]
    pivot = (0.0, 0.0, 0.0)
    around_x = choose_rail(vertex, [], pivot, (1.0, 0.0, 0.0), borrowed_others=borrowed)
    around_y = choose_rail(vertex, others, pivot, (0.0, 1.0, 0.0), borrowed_others=borrowed)
    assert around_x is not None and around_y is not None
    assert abs(around_x.direction[1]) > 0.9
    assert abs(around_y.direction[0]) > 0.9


def test_loop_vert_keeps_physical_rail_when_tangent_is_orthogonal() -> None:
    """Loop vert sharing the pivot's X: Z-rotation tangent is X, 1-ring is Y.

    Through-X edges copied from the face island must not replace the real Y rails.
    """
    vertex = (0.0, -1.13, 0.77)
    others = [(0.0, -2.0, 0.67), (0.0, 0.13, 0.91)]
    borrowed = [(-1.0, -1.13, 0.77)]
    pivot = (0.0, -0.92, 0.26)
    axis = (0.0, 0.0, 1.0)
    rail = choose_rail(vertex, others, pivot, axis, borrowed_others=borrowed)
    assert rail is not None
    assert abs(rail.direction[1]) > 0.9
    assert abs(rail.direction[0]) < 0.1


def test_inface_1ring_not_replaced_by_better_borrowed() -> None:
    """An unselected in-face neighbor is still a real edge; do not steal a through-rail."""
    vertex = (0.0, 0.0, 1.0)
    others = [(1.0, 0.0, 1.0), (-1.0, 0.0, 1.0), (0.0, 0.0, 2.0), (0.0, 0.0, 0.0)]
    borrowed = [(0.0, -2.0, 1.0)]
    pivot = (0.0, 0.0, 0.0)
    axis = (1.0, 0.0, 0.0)
    rail = choose_rail(vertex, others, pivot, axis, borrowed_others=borrowed)
    assert rail is not None
    assert abs(rail.direction[1]) < 0.5


def test_strong_physical_rail_ignores_borrowed() -> None:
    """A good 1-ring rail is kept even if the face island also offers another direction."""
    pivot = (1.0, 0.0, 0.0)
    axis = (0.0, 0.0, 1.0)
    rail = choose_rail(
        (0.0, 0.0, 0.0),
        [(0.0, 1.0, 0.0), (0.0, -1.0, 0.0), (1.0, 0.0, 0.0)],
        pivot,
        axis,
        borrowed_others=[(2.0, 0.0, 0.0)],
    )
    assert rail is not None and rail.merged
    assert almost_equal(rail.direction, (0.0, 1.0, 0.0)) or almost_equal(
        rail.direction,
        (0.0, -1.0, 0.0),
    )


def test_face_interior_with_no_unselected_neighbors_uses_borrowed() -> None:
    """All in-face neighbors selected: borrowed through-edge is the only rail."""
    vertex = (0.0, 0.0, 1.0)
    pivot = (0.0, 0.0, 0.0)
    axis = (1.0, 0.0, 0.0)
    rail = choose_rail(vertex, [], pivot, axis, borrowed_others=[(0.0, -2.0, 1.0)])
    assert rail is not None
    assert almost_equal(rail.direction, (0.0, -1.0, 0.0)) or almost_equal(
        rail.direction,
        (0.0, 1.0, 0.0),
    )


def test_face_interior_borrowed_state_slides_with_theta() -> None:
    """Interior vert on a borrowed Y rail tracks X-axis rotation like a boundary vert."""
    original = (0.0, 0.0, 1.0)
    pivot = (0.0, 0.0, 0.0)
    axis = (1.0, 0.0, 0.0)
    state = build_vertex_state(
        index=0,
        local=original,
        world=original,
        neighbor_worlds=[],
        pivot=pivot,
        axis=axis,
        borrowed_worlds=[(0.0, -2.0, 1.0)],
    )
    assert state.movable
    apply_vertex_theta(state, pivot, axis, math.radians(30.0), True)
    world = transformed_world(state)
    assert abs(world[0] - 0.0) < 1e-9
    assert abs(world[2] - 1.0) < 1e-9
    assert world[1] < -0.1


def test_recompute_from_original_avoids_drift() -> None:
    rail = Rail(origin=(1.0, 0.0, 0.0), direction=(0.0, 1.0, 0.0), t_min=-5.0, t_max=5.0, merged=True)
    state = VertexRailState(
        index=0,
        original_world=(1.0, 0.0, 0.0),
        original_local=(1.0, 0.0, 0.0),
        rail=rail,
        movable=True,
    )
    pivot = (0.0, 0.0, 0.0)
    axis = (0.0, 0.0, 1.0)
    apply_vertex_theta(state, pivot, axis, 0.3, True)
    first = transformed_world(state)
    apply_vertex_theta(state, pivot, axis, 0.3, True)
    second = transformed_world(state)
    assert almost_equal(first, second)
    apply_vertex_theta(state, pivot, axis, 0.0, True)
    assert almost_equal(transformed_world(state), (1.0, 0.0, 0.0))


def test_scale_prefers_radial_rail_over_tangent() -> None:
    """Rotate wants the Y rail; scale wants the X rail from the same neighbors."""
    vertex = (1.0, 0.0, 0.0)
    others = [(1.0, 1.0, 0.0), (2.0, 0.0, 0.0)]
    pivot = (0.0, 0.0, 0.0)
    axis = (0.0, 0.0, 1.0)
    rotate_rail = choose_rail(vertex, others, pivot, axis)
    scale_rail = choose_rail(vertex, others, pivot, axis, mode=MODE_SCALE)
    assert rotate_rail is not None and scale_rail is not None
    assert abs(rotate_rail.direction[1]) > 0.9
    assert abs(scale_rail.direction[0]) > 0.9


def test_scale_along_radial_rail_doubles_distance() -> None:
    pivot = (0.0, 0.0, 0.0)
    axis = (0.0, 0.0, 1.0)
    original = (1.0, 0.0, 0.0)
    rail = Rail(origin=original, direction=(1.0, 0.0, 0.0), t_min=0.0, t_max=4.0)
    state = VertexRailState(
        index=0,
        original_world=original,
        original_local=original,
        rail=rail,
        movable=True,
    )
    apply_vertex_scale(state, pivot, axis, 2.0, True, axis_locked=False)
    assert almost_equal(transformed_world(state), (2.0, 0.0, 0.0))
    apply_vertex_scale(state, pivot, axis, 1.0, True, axis_locked=False)
    assert almost_equal(transformed_world(state), original)


def test_axis_locked_scale_zero_hits_pivot_plane_on_tilted_rail() -> None:
    """Regression: Y-lock factor 0 must share the pivot Y, even if the rail is not exactly Y.

    Closest-point projection of the unconstrained (x, pivot_y, z) pose onto a
    tilted rail stops short of the plane; intersecting the rail with Y=pivot_y
    is the rotate-style solve.
    """
    pivot = (0.0, 1.0, 0.0)
    axis = (0.0, 1.0, 0.0)
    original = (1.0, 3.0, 0.0)
    length = (0.2 * 0.2 + 1.0) ** 0.5
    direction = (0.2 / length, 1.0 / length, 0.0)
    rail = Rail(origin=original, direction=direction, t_min=-10.0, t_max=10.0, merged=True)
    state = VertexRailState(
        index=0,
        original_world=original,
        original_local=original,
        rail=rail,
        movable=True,
    )
    apply_vertex_scale(state, pivot, axis, 0.0, True, axis_locked=True)
    world = transformed_world(state)
    assert abs(world[1] - pivot[1]) < 1e-9
    # Stayed on the rail line.
    offset = (world[0] - original[0], world[1] - original[1], world[2] - original[2])
    assert abs(offset[0] * direction[1] - offset[1] * direction[0]) < 1e-9


def test_axis_locked_scale_only_moves_along_lock_axis() -> None:
    pivot = (0.0, 0.0, 0.0)
    axis = (1.0, 0.0, 0.0)
    original = (1.0, 1.0, 0.0)
    assert almost_equal(
        unconstrained_scaled_point(original, pivot, axis, 2.0, True),
        (2.0, 1.0, 0.0),
    )
    rail = Rail(origin=original, direction=(1.0, 0.0, 0.0), t_min=-4.0, t_max=4.0)
    state = VertexRailState(
        index=0,
        original_world=original,
        original_local=original,
        rail=rail,
        movable=True,
    )
    apply_vertex_scale(state, pivot, axis, 2.0, True, axis_locked=True)
    world = transformed_world(state)
    assert abs(world[0] - 2.0) < 1e-9
    assert abs(world[1] - 1.0) < 1e-9


def test_scale_clamp_stops_at_physical_end() -> None:
    pivot = (0.0, 0.0, 0.0)
    axis = (0.0, 0.0, 1.0)
    original = (1.0, 0.0, 0.0)
    rail = Rail(origin=original, direction=(1.0, 0.0, 0.0), t_min=0.0, t_max=0.25)
    state = VertexRailState(
        index=0,
        original_world=original,
        original_local=original,
        rail=rail,
        movable=True,
    )
    apply_vertex_scale(state, pivot, axis, 2.0, False, axis_locked=False)
    assert almost_equal(transformed_world(state), (1.25, 0.0, 0.0))


def test_locked_scale_scores_rails_along_axis() -> None:
    vertex = (1.0, 1.0, 0.0)
    others = [(2.0, 1.0, 0.0), (1.0, 2.0, 0.0)]
    pivot = (0.0, 0.0, 0.0)
    unlocked = choose_rail(vertex, others, pivot, (1.0, 0.0, 0.0), mode=MODE_SCALE, axis_locked=False)
    locked = choose_rail(vertex, others, pivot, (1.0, 0.0, 0.0), mode=MODE_SCALE, axis_locked=True)
    assert unlocked is not None and locked is not None
    # Unlocked uniform scale prefers the radial (roughly 1,1); both score, but
    # X-lock should prefer the X rail.
    assert abs(locked.direction[0]) > 0.9


def test_best_fit_plane_xy_square_is_z() -> None:
    origin, normal = best_fit_plane(
        [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, 2.0, 0.0), (0.0, 2.0, 0.0)]
    )
    assert almost_equal(origin, (1.0, 1.0, 0.0))
    assert abs(abs(normal[2]) - 1.0) < 1e-6
    assert abs(normal[0]) < 1e-6 and abs(normal[1]) < 1e-6


def test_best_fit_plane_rejects_collinear() -> None:
    assert best_fit_plane([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (2.0, 0.0, 0.0)]) is None


def test_flatten_prefers_normal_rail() -> None:
    """A bump with a Z rail and an in-plane X rail should slide on Z."""
    vertex = (1.0, 0.0, 2.0)
    others = [(2.0, 0.0, 2.0), (1.0, 0.0, 0.0)]
    rail = choose_rail(vertex, others, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), mode=MODE_FLATTEN)
    assert rail is not None
    assert abs(rail.direction[2]) > 0.9


def test_flatten_factor_one_hits_plane_on_tilted_rail() -> None:
    plane_origin = (0.0, 0.0, 0.0)
    plane_normal = (0.0, 0.0, 1.0)
    original = (1.0, 0.0, 2.0)
    length = (0.2 * 0.2 + 1.0) ** 0.5
    direction = (0.2 / length, 0.0, -1.0 / length)
    rail = Rail(origin=original, direction=direction, t_min=-10.0, t_max=10.0, merged=True)
    state = VertexRailState(
        index=0,
        original_world=original,
        original_local=original,
        rail=rail,
        movable=True,
    )
    apply_vertex_flatten(state, plane_origin, plane_normal, 1.0, True)
    world = transformed_world(state)
    assert abs(world[2]) < 1e-9
    apply_vertex_flatten(state, plane_origin, plane_normal, 0.0, True)
    assert almost_equal(transformed_world(state), original)
    apply_vertex_flatten(state, plane_origin, plane_normal, 0.5, True)
    assert abs(transformed_world(state)[2] - 1.0) < 1e-9


def test_flatten_unconstrained_lerp_matches_projection() -> None:
    original = (0.0, 0.0, 4.0)
    assert almost_equal(
        unconstrained_flattened_point(original, (0.0, 0.0, 1.0), (0.0, 0.0, 1.0), 1.0),
        (0.0, 0.0, 1.0),
    )
    assert almost_equal(
        unconstrained_flattened_point(original, (0.0, 0.0, 1.0), (0.0, 0.0, 1.0), 0.25),
        (0.0, 0.0, 3.25),
    )


def test_flatten_parallel_rail_stays_put() -> None:
    original = (1.0, 0.0, 2.0)
    rail = Rail(origin=original, direction=(1.0, 0.0, 0.0), t_min=-4.0, t_max=4.0)
    state = VertexRailState(
        index=0,
        original_world=original,
        original_local=original,
        rail=rail,
        movable=True,
    )
    apply_vertex_flatten(state, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 1.0, True)
    assert almost_equal(transformed_world(state), original)
    assert state.used_fallback


def test_flatten_clamp_stops_at_physical_end() -> None:
    original = (0.0, 0.0, 2.0)
    rail = Rail(origin=original, direction=(0.0, 0.0, -1.0), t_min=0.0, t_max=0.5)
    state = VertexRailState(
        index=0,
        original_world=original,
        original_local=original,
        rail=rail,
        movable=True,
    )
    apply_vertex_flatten(state, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 1.0, False)
    assert almost_equal(transformed_world(state), (0.0, 0.0, 1.5))


def test_flatten_does_not_freeze_pivot_vertex() -> None:
    """Rotate freezes the pivot vertex; flatten must still slide it onto the plane."""
    pivot = (0.0, 0.0, 0.0)
    original = pivot
    state = build_vertex_state(
        0,
        original,
        original,
        [(0.0, 0.0, -2.0)],
        pivot,
        (0.0, 0.0, 1.0),
        mode=MODE_FLATTEN,
    )
    assert state.movable and state.rail is not None
    apply_vertex_flatten(state, (0.0, 0.0, 1.0), (0.0, 0.0, 1.0), 1.0, True)
    assert abs(transformed_world(state)[2] - 1.0) < 1e-9
