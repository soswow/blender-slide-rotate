from core.axis import lock_label, locked_axis_vector, press_axis_key
from core.types import AxisLockState
from core.vec import almost_equal, identity_mat3, mat3_from_columns


def test_axis_cycle_view_orientation_global_view() -> None:
    state = AxisLockState()
    state = press_axis_key(state, "X")
    assert state == AxisLockState(letter="X", stage=1)
    assert lock_label(state, "GLOBAL") == "Global X"
    state = press_axis_key(state, "X")
    assert state.stage == 2
    assert lock_label(state, "GLOBAL") == "Local X"
    state = press_axis_key(state, "X")
    assert state == AxisLockState(letter=None, stage=0)
    assert lock_label(state, "GLOBAL") == "View"


def test_switching_letter_starts_orientation_lock() -> None:
    state = press_axis_key(AxisLockState(), "X")
    state = press_axis_key(state, "Y")
    assert state == AxisLockState(letter="Y", stage=1)
    assert lock_label(state, "LOCAL") == "Local Y"
    state = press_axis_key(state, "Y")
    assert lock_label(state, "LOCAL") == "Global Y"


def test_locked_axis_vectors_match_stage() -> None:
    view = (0.0, 0.0, 1.0)
    local = mat3_from_columns((0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
    orientation = identity_mat3()
    view_axis = locked_axis_vector(AxisLockState(), view, "GLOBAL", orientation, local)
    assert almost_equal(view_axis, (0.0, 0.0, 1.0))
    x_global = locked_axis_vector(
        AxisLockState(letter="X", stage=1),
        view,
        "GLOBAL",
        orientation,
        local,
    )
    assert almost_equal(x_global, (1.0, 0.0, 0.0))
    x_local = locked_axis_vector(
        AxisLockState(letter="X", stage=2),
        view,
        "GLOBAL",
        orientation,
        local,
    )
    assert almost_equal(x_local, (0.0, 1.0, 0.0))


def test_non_global_stage_two_uses_world_xyz() -> None:
    local = mat3_from_columns((0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
    axis = locked_axis_vector(
        AxisLockState(letter="Y", stage=2),
        (0.0, 0.0, 1.0),
        "NORMAL",
        local,
        local,
    )
    assert almost_equal(axis, (0.0, 1.0, 0.0))


def test_ignore_non_axis_keys() -> None:
    original = AxisLockState(letter="Z", stage=1)
    assert press_axis_key(original, "C") == original
