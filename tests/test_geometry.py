import math

from core.geometry import (
    apply_vertex_theta,
    build_vertex_state,
    choose_rail,
    clamp_t,
    overlay_axis_segment,
    overlay_segment,
    solve_rail_parameter,
    transformed_world,
)
from core.types import Rail, VertexRailState
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
    """Copied volume-through edges become the rail when 1-ring neighbors lie in the face."""
    vertex = (0.0, 0.0, 1.0)
    others = [(1.0, 0.0, 1.0), (-1.0, 0.0, 1.0), (0.0, 0.0, 2.0), (0.0, 0.0, 0.0)]
    borrowed = [(0.0, -2.0, 1.0)]
    pivot = (0.0, 0.0, 0.0)
    axis = (1.0, 0.0, 0.0)
    rail = choose_rail(vertex, others, pivot, axis, borrowed_others=borrowed)
    assert rail is not None
    assert almost_equal(rail.direction, (0.0, -1.0, 0.0)) or almost_equal(
        rail.direction,
        (0.0, 1.0, 0.0),
    )
    assert abs(rail.t_max - 2.0) < 1e-9


def test_borrowed_through_rail_follows_axis() -> None:
    """Physical in-face X wins around Y; borrowed through-Y wins around X."""
    vertex = (0.0, 0.0, 1.0)
    others = [(1.0, 0.0, 1.0)]
    borrowed = [(0.0, -2.0, 1.0)]
    pivot = (0.0, 0.0, 0.0)
    around_x = choose_rail(vertex, others, pivot, (1.0, 0.0, 0.0), borrowed_others=borrowed)
    around_y = choose_rail(vertex, others, pivot, (0.0, 1.0, 0.0), borrowed_others=borrowed)
    assert around_x is not None and around_y is not None
    assert abs(around_x.direction[1]) > 0.9
    assert abs(around_y.direction[0]) > 0.9


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
        neighbor_worlds=[(1.0, 0.0, 1.0), (0.0, 0.0, 0.0)],
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
