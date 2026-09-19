"""Axis-lock cycling that matches Blender's native Rotate (R) hotkeys."""

from __future__ import annotations

from .types import AxisLockState
from .vec import Mat3, Vec3, column, identity_mat3, normalize

_AXIS_INDEX = {"X": 0, "Y": 1, "Z": 2}


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
