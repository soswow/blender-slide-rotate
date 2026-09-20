import math

from core.curve import (
    VertexChain,
    clamp_curve_order,
    closest_point_on_polyline,
    evaluate_curve,
    fit_chain_curve,
    fit_curve_targets,
    selection_max_curve_order,
    step_curve_order,
    unconstrained_curved_point,
    walk_selected_chains,
)
from core.geometry import (
    apply_vertex_curve,
    build_vertex_state,
    choose_rail,
    closest_point_on_rail_to_polyline,
    transformed_world,
)
from core.types import MODE_CURVE, Rail, VertexRailState
from core.vec import almost_equal


def test_walk_closed_loop() -> None:
    chains = walk_selected_chains([0, 1, 2, 3], [(0, 1), (1, 2), (2, 3), (3, 0)])
    assert len(chains) == 1
    assert chains[0].closed
    assert set(chains[0].indices) == {0, 1, 2, 3}


def test_walk_open_path() -> None:
    chains = walk_selected_chains([0, 1, 2], [(0, 1), (1, 2)])
    assert len(chains) == 1
    assert not chains[0].closed
    assert chains[0].indices in {(0, 1, 2), (2, 1, 0)}


def test_walk_junction_splits() -> None:
    chains = walk_selected_chains([0, 1, 2, 3], [(0, 1), (1, 2), (1, 3)])
    assert len(chains) == 3
    assert all(not chain.closed for chain in chains)
    assert all(len(chain.indices) == 2 for chain in chains)


def test_walk_ignores_isolated() -> None:
    chains = walk_selected_chains([0, 1, 2], [(0, 1)])
    assert len(chains) == 1
    assert not chains[0].closed
    assert set(chains[0].indices) == {0, 1}


def test_open_order_one_is_pinned_chord() -> None:
    points = [(0.0, 0.0, 0.0), (1.0, 0.0, 2.0), (2.0, 0.0, 0.0)]
    fitted = fit_chain_curve(points, False, 1)
    assert fitted is not None
    assert almost_equal(evaluate_curve(fitted, 0.0), points[0])
    assert almost_equal(evaluate_curve(fitted, 1.0), points[2])
    mid = evaluate_curve(fitted, 0.5)
    assert abs(mid[2]) < 1e-6
    assert abs(mid[0] - 1.0) < 1e-6


def test_open_high_order_keeps_more_bump_than_line() -> None:
    chains = [VertexChain(indices=(0, 1, 2, 3), closed=False)]
    worlds = {
        0: (0.0, 0.0, 0.0),
        1: (1.0, 0.0, 2.0),
        2: (2.0, 0.0, 0.0),
        3: (3.0, 0.0, 0.0),
    }
    line = fit_curve_targets(chains, worlds, 1)
    cubic = fit_curve_targets(chains, worlds, 3)
    assert cubic[1][2] > line[1][2] + 0.5


def test_closed_first_harmonic_kills_z_spike() -> None:
    chains = [VertexChain(indices=tuple(range(8)), closed=True)]
    worlds = {}
    for index in range(8):
        angle = 2.0 * math.pi * index / 8.0
        z_value = 2.0 if index == 2 else 0.0
        worlds[index] = (math.cos(angle), math.sin(angle), z_value)
    low = fit_curve_targets(chains, worlds, 1)
    high = fit_curve_targets(chains, worlds, 3)
    assert low[2][2] < 1.7
    assert high[2][2] > low[2][2] + 0.2
    assert worlds[2][2] == 2.0


def test_closed_circle_first_harmonic_stays_on_ring() -> None:
    points = [
        (math.cos(2.0 * math.pi * index / 8.0), math.sin(2.0 * math.pi * index / 8.0), 0.0)
        for index in range(8)
    ]
    fitted = fit_chain_curve(points, True, 1)
    assert fitted is not None
    sample = evaluate_curve(fitted, 0.0)
    radius = (sample[0] ** 2 + sample[1] ** 2) ** 0.5
    assert abs(radius - 1.0) < 1e-4
    assert abs(sample[2]) < 1e-6


def test_axis_lock_projects_fit_to_plane() -> None:
    chains = [VertexChain(indices=(0, 1, 2), closed=False)]
    worlds = {
        0: (0.0, 0.0, 3.0),
        1: (1.0, 0.0, 4.0),
        2: (2.0, 0.0, 3.0),
    }
    targets = fit_curve_targets(
        chains,
        worlds,
        1,
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 1.0),
    )
    assert abs(targets[1][2]) < 1e-6
    assert abs(targets[0][2]) < 1e-6


def test_factor_zero_is_original() -> None:
    original = (1.0, 0.0, 2.0)
    assert almost_equal(unconstrained_curved_point(original, (1.0, 0.0, 0.0), 0.0), original)


def test_rail_target_is_closest_approach_not_same_parameter() -> None:
    """A bow on the imaginary line should pull a Y-rail to that Y, not keep s_i."""
    rail = Rail(origin=(0.0, 0.0, 0.0), direction=(0.0, 1.0, 0.0), t_min=-10.0, t_max=10.0)
    polyline = [(2.0, 0.0, 0.0), (0.1, 4.0, 0.0), (2.0, 8.0, 0.0)]
    target = closest_point_on_rail_to_polyline(rail, polyline)
    assert abs(target[0]) < 1e-9
    assert abs(target[1] - 4.0) < 1e-9
    nearest = closest_point_on_polyline((0.0, 0.0, 0.0), polyline)
    assert nearest[0] > 1.0


def test_curve_slides_along_rail_toward_target() -> None:
    original = (1.0, 0.0, 2.0)
    target = (1.0, 0.0, 0.0)
    rail = Rail(origin=original, direction=(0.0, 0.0, -1.0), t_min=0.0, t_max=4.0)
    state = VertexRailState(
        index=0,
        original_world=original,
        original_local=original,
        rail=rail,
        movable=True,
    )
    apply_vertex_curve(state, target, 1.0, True)
    assert almost_equal(transformed_world(state), target)
    apply_vertex_curve(state, target, 0.5, True)
    assert abs(transformed_world(state)[2] - 1.0) < 1e-9


def test_curve_clamp_stops_at_physical_end() -> None:
    original = (0.0, 0.0, 2.0)
    target = (0.0, 0.0, 0.0)
    rail = Rail(origin=original, direction=(0.0, 0.0, -1.0), t_min=0.0, t_max=0.5)
    state = VertexRailState(
        index=0,
        original_world=original,
        original_local=original,
        rail=rail,
        movable=True,
    )
    apply_vertex_curve(state, target, 1.0, False)
    assert almost_equal(transformed_world(state), (0.0, 0.0, 1.5))


def test_curve_oblique_rail_small_factor_stays_near_start() -> None:
    """Regression: plane-hit along a mostly-perpendicular target slams to t_max."""
    original = (0.0, 0.0, 0.0)
    target = (1.0, 0.0, 0.0)
    length = (0.001 * 0.001 + 1.0) ** 0.5
    direction = (0.001 / length, 1.0 / length, 0.0)
    rail = Rail(origin=original, direction=direction, t_min=0.0, t_max=2.0)
    state = VertexRailState(
        index=0,
        original_world=original,
        original_local=original,
        rail=rail,
        movable=True,
    )
    apply_vertex_curve(state, target, 0.01, True)
    world = transformed_world(state)
    assert (world[0] ** 2 + world[1] ** 2 + world[2] ** 2) ** 0.5 < 0.05
    apply_vertex_curve(state, target, 0.0, True)
    assert almost_equal(transformed_world(state), original)


def test_curve_parallel_rail_projects_in_place() -> None:
    original = (0.0, 0.0, 2.0)
    target = (0.0, 0.0, 0.0)
    rail = Rail(origin=original, direction=(1.0, 0.0, 0.0), t_min=-4.0, t_max=4.0)
    state = VertexRailState(
        index=0,
        original_world=original,
        original_local=original,
        rail=rail,
        movable=True,
    )
    apply_vertex_curve(state, target, 1.0, True)
    assert almost_equal(transformed_world(state), original)


def test_curve_prefers_rail_toward_target() -> None:
    vertex = (1.0, 0.0, 2.0)
    others = [(2.0, 0.0, 2.0), (1.0, 0.0, 0.0)]
    rail = choose_rail(
        vertex,
        others,
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 1.0),
        mode=MODE_CURVE,
        guide_override=(0.0, 0.0, -1.0),
    )
    assert rail is not None
    assert abs(rail.direction[2]) > 0.9


def test_curve_does_not_freeze_pivot_vertex() -> None:
    pivot = (0.0, 0.0, 0.0)
    state = build_vertex_state(
        0,
        pivot,
        pivot,
        [(0.0, 0.0, -2.0)],
        pivot,
        (0.0, 0.0, 1.0),
        mode=MODE_CURVE,
        guide_override=(0.0, 0.0, -1.0),
    )
    assert state.movable and state.rail is not None


def test_order_clamps_and_steps() -> None:
    assert clamp_curve_order(9, 4, False) == 3
    assert clamp_curve_order(9, 8, True) == 3
    assert step_curve_order(3, 1, 3) == 3
    assert step_curve_order(3, -1, 8) == 2
    assert selection_max_curve_order([VertexChain(indices=(0, 1), closed=False)]) == 1
