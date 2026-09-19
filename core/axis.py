"""Axis-lock cycling that matches Blender's native Rotate (R) hotkeys."""

from __future__ import annotations

import math

from .types import AxisLockState
from .vec import Mat3, Vec3, column, dot, identity_mat3, normalize, sub

_AXIS_INDEX = {"X": 0, "Y": 1, "Z": 2}
# Factory Theme User Interface Axis X/Y/Z (TH_AXIS_*), used when bpy is absent.
_FACTORY_AXIS_RGB = {
    "X": (1.0, 0.2, 0.3215686274509804),
    "Y": (0.5450980392156862, 0.8627450980392157, 0.0),
    "Z": (0.1568627450980392, 0.5647058823529412, 1.0),
}
# Native R active constraint uses DRAWLIGHT, then UI_make_axis_color.
_DRAWLIGHT_RGB = (220.0 / 255.0, 220.0 / 255.0, 220.0 / 255.0)
_AXIS_COLOR_BLEND = 0.5
_AXIS_COLOR_SHADE = -10


def press_axis_key(state: AxisLockState, key: str) -> AxisLockState:
    """Advance lock state for an X/Y/Z key press during the modal."""
    letter = key.upper()
    if letter not in _AXIS_INDEX:
        return state
    if state.letter != letter:
        return AxisLockState(letter=letter, stage=1)
    if state.stage == 1:
        return AxisLockState(letter=letter, stage=2)
    return AxisLockState(letter=None, stage=0)


def lock_axis_overlay_letter(state: AxisLockState) -> str | None:
    """X/Y/Z letter to draw like native R; None while unconstrained (View)."""
    if state.stage == 0 or state.letter is None:
        return None
    return state.letter


def blend_shade_rgb(
    first: Vec3,
    second: Vec3,
    factor: float,
    shade: int,
) -> Vec3:
    """Match ``get_color_blend_shade_3ubv``: lerp in bytes, then add ``shade``."""
    factor = max(0.0, min(1.0, factor))
    mixed: list[float] = []
    for channel_a, channel_b in zip(first, second, strict=True):
        byte_a = max(0, min(255, int(round(channel_a * 255.0))))
        byte_b = max(0, min(255, int(round(channel_b * 255.0))))
        value = int(math.floor((1.0 - factor) * byte_a + factor * byte_b)) + shade
        mixed.append(max(0, min(255, value)) / 255.0)
    return (mixed[0], mixed[1], mixed[2])


def axis_overlay_color(
    letter: str | None,
    axis_rgb: tuple[float, float, float] | None = None,
) -> tuple[float, float, float, float] | None:
    """Native R constraint color: mix Axis X/Y/Z with DRAWLIGHT, then shade."""
    if letter is None:
        return None
    raw = axis_rgb if axis_rgb is not None else _FACTORY_AXIS_RGB.get(letter.upper())
    if raw is None:
        return None
    mixed = blend_shade_rgb(_DRAWLIGHT_RGB, raw, _AXIS_COLOR_BLEND, _AXIS_COLOR_SHADE)
    return (mixed[0], mixed[1], mixed[2], 1.0)


def lock_label(state: AxisLockState, orientation_name: str) -> str:
    """Short header label such as ``View`` or ``Global X``."""
    if state.stage == 0 or state.letter is None:
        return "View"
    title = _orientation_title(orientation_name)
    if state.stage == 1:
        return f"{title} {state.letter}"
    if orientation_name.upper() == "GLOBAL":
        return f"Local {state.letter}"
    return f"Global {state.letter}"


def locked_axis_vector(
    state: AxisLockState,
    view_axis: Vec3,
    orientation_name: str,
    orientation_matrix: Mat3,
    local_matrix: Mat3,
) -> Vec3:
    """World-space rotation axis for the current lock stage."""
    if state.stage == 0 or state.letter is None:
        axis = normalize(view_axis)
        return axis if axis is not None else (0.0, 0.0, 1.0)

    index = _AXIS_INDEX[state.letter]
    if state.stage == 1:
        matrix = orientation_matrix
    elif orientation_name.upper() == "GLOBAL":
        matrix = local_matrix
    else:
        matrix = identity_mat3()
    axis = normalize(column(matrix, index))
    return axis if axis is not None else (0.0, 0.0, 1.0)


def view_toward_camera(
    view_axis: Vec3,
    pivot: Vec3,
    camera_location: Vec3 | None,
    perspective: bool,
) -> Vec3:
    """Unit vector from the pivot toward the camera (out of the screen)."""
    fallback = normalize(view_axis)
    if fallback is None:
        fallback = (0.0, 0.0, 1.0)
    if perspective and camera_location is not None:
        toward = normalize(sub(camera_location, pivot))
        if toward is not None:
            return toward
    return fallback


def mouse_angle_axis_sign(axis: Vec3, view_toward: Vec3) -> float:
    """Map screen-space CCW onto a lock axis so the mouse still follows.

    Unconstrained rotation uses the view axis (toward the camera), so +atan2 is
    CCW on screen. When the lock axis points the other way, the same gesture
    would run backwards unless the mouse angle is flipped — same idea as native
    R axis constraint.
    """
    unit_axis = normalize(axis)
    unit_view = normalize(view_toward)
    if unit_axis is None or unit_view is None:
        return 1.0
    if dot(unit_axis, unit_view) < 0.0:
        return -1.0
    return 1.0


def _orientation_title(orientation_name: str) -> str:
    mapping = {
        "GLOBAL": "Global",
        "LOCAL": "Local",
        "NORMAL": "Normal",
        "GIMBAL": "Gimbal",
        "VIEW": "View",
        "CURSOR": "Cursor",
    }
    key = orientation_name.upper()
    return mapping.get(key, orientation_name.title() or "Global")
