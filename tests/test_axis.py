from core.axis import (
    axis_overlay_color,
    blend_shade_rgb,
    lock_axis_overlay_letter,
    lock_label,
    locked_axis_vector,
    mouse_angle_axis_sign,
    press_axis_key,
    view_toward_camera,
)
from core.types import AxisLockState
from core.vec import (
    almost_equal,
    cross,
    dot,
    identity_mat3,
    mat3_from_columns,
    normalize,
    rotate_around_axis,
    sub,
)


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


def test_view_axis_mouse_sign_stays_positive() -> None:
    for view in ((0.0, 0.0, 1.0), (0.0, 0.0, -1.0), (1.0, 0.0, 0.0), (0.0, -1.0, 0.0)):
        assert mouse_angle_axis_sign(view, view) == 1.0


def test_axis_lock_mouse_sign_flips_when_view_orbits_180_around_z() -> None:
    """Lock axis pointing away from the camera must invert screen-space theta."""
    axis_y = (0.0, 1.0, 0.0)
    assert mouse_angle_axis_sign(axis_y, (0.0, -1.0, 0.0)) == -1.0
    assert mouse_angle_axis_sign(axis_y, (0.0, 1.0, 0.0)) == 1.0
    axis_z = (0.0, 0.0, 1.0)
    assert mouse_angle_axis_sign(axis_z, (0.0, 0.0, 1.0)) == 1.0
    assert mouse_angle_axis_sign(axis_z, (0.0, 0.0, -1.0)) == -1.0


def test_perpendicular_lock_keeps_axis_handedness() -> None:
    assert mouse_angle_axis_sign((0.0, 0.0, 1.0), (0.0, -1.0, 0.0)) == 1.0


def test_perspective_view_vector_uses_camera_to_pivot() -> None:
    toward = view_toward_camera(
        (0.0, 0.0, 1.0),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, -10.0),
        True,
    )
    assert almost_equal(toward, (0.0, 0.0, -1.0))
    ortho = view_toward_camera(
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, -10.0),
        False,
    )
    assert almost_equal(ortho, (0.0, 1.0, 0.0))


def _screen_spin(pivot, start, rotated, view_toward) -> float:
    """Positive when ``rotated`` is CCW from ``start`` around the projected pivot."""
    look = (-view_toward[0], -view_toward[1], -view_toward[2])
    helper = (0.0, 0.0, 1.0) if abs(view_toward[2]) < 0.9 else (0.0, 1.0, 0.0)
    right = normalize(cross(look, helper))
    assert right is not None
    up = cross(view_toward, right)

    def xy(point):
        delta = sub(point, pivot)
        return (dot(delta, right), dot(delta, up))

    x1, y1 = xy(start)
    x2, y2 = xy(rotated)
    return x1 * y2 - y1 * x2


def test_y_lock_follows_mouse_after_orbit_180_around_z() -> None:
    """Regression: Y lock used to reverse after turning the camera around Z."""
    axis = (0.0, 1.0, 0.0)
    screen_ccw = 0.25
    pivot = (0.0, 0.0, 0.0)
    point = (1.0, 0.0, 0.3)
    for view in ((0.0, -1.0, 0.0), (0.0, 1.0, 0.0)):
        theta = screen_ccw * mouse_angle_axis_sign(axis, view)
        rotated = rotate_around_axis(point, pivot, axis, theta)
        assert _screen_spin(pivot, point, rotated, view) > 0.0


def test_lock_axis_overlay_only_when_constrained() -> None:
    assert lock_axis_overlay_letter(AxisLockState()) is None
    assert lock_axis_overlay_letter(AxisLockState(letter="X", stage=0)) is None
    assert lock_axis_overlay_letter(AxisLockState(letter="X", stage=1)) == "X"
    assert lock_axis_overlay_letter(AxisLockState(letter="Y", stage=2)) == "Y"


def test_axis_overlay_colors_match_xyz() -> None:
    assert axis_overlay_color(None) is None
    red = axis_overlay_color("X")
    green = axis_overlay_color("Y")
    blue = axis_overlay_color("Z")
    assert red is not None and red[0] > red[1] and red[0] > red[2]
    assert green is not None and green[1] > green[0] and green[1] > green[2]
    assert blue is not None and blue[2] > blue[0] and blue[2] > blue[1]
    assert axis_overlay_color("W") is None


def test_native_r_mix_lightens_axis_x_toward_pink() -> None:
    """DRAWLIGHT + Axis X + shade -10 is the pastel pink native R uses."""
    raw_x = (1.0, 0.2, 0.3215686274509804)
    mixed = blend_shade_rgb((220 / 255.0, 220 / 255.0, 220 / 255.0), raw_x, 0.5, -10)
    assert mixed == (227 / 255.0, 125 / 255.0, 141 / 255.0)
    overlay = axis_overlay_color("X", raw_x)
    assert overlay is not None
    assert overlay[:3] == mixed
    assert overlay[1] > raw_x[1]
    assert overlay[2] > raw_x[2]
