"""Pure mouse-angle, precision, snap, and numeric-input helpers."""

from __future__ import annotations

import math

from dataclasses import dataclass

from .types import MODE_ROTATE, MODE_SCALE, NumericInput

# Status-bar chips during the modal (icon names match bpy UILayout icons).
# Python cannot register a Blender modal keymap, so we draw these ourselves.

PRECISION_FACTOR = 0.1
# Fallback when Blender snap increments are unavailable.
DEFAULT_SNAP_RADIANS = math.radians(5.0)
DEFAULT_PRECISION_SNAP_RADIANS = math.radians(1.0)
DEFAULT_SNAP_SCALE = 0.1
DEFAULT_PRECISION_SNAP_SCALE = 0.01

_DIGIT_KEYS = {
    "ZERO": "0",
    "ONE": "1",
    "TWO": "2",
    "THREE": "3",
    "FOUR": "4",
    "FIVE": "5",
    "SIX": "6",
    "SEVEN": "7",
    "EIGHT": "8",
    "NINE": "9",
    "NUMPAD_0": "0",
    "NUMPAD_1": "1",
    "NUMPAD_2": "2",
    "NUMPAD_3": "3",
    "NUMPAD_4": "4",
    "NUMPAD_5": "5",
    "NUMPAD_6": "6",
    "NUMPAD_7": "7",
    "NUMPAD_8": "8",
    "NUMPAD_9": "9",
}


def wrap_angle_delta(start: float, current: float) -> float:
    """Signed shortest delta from ``start`` to ``current`` in (-pi, pi]."""
    delta = current - start
    while delta > math.pi:
        delta -= 2.0 * math.pi
    while delta <= -math.pi:
        delta += 2.0 * math.pi
    return delta


def screen_angle(mouse_x: float, mouse_y: float, pivot_x: float, pivot_y: float) -> float | None:
    """Atan2 angle of the mouse around a screen-space pivot, or None if too close."""
    dx = mouse_x - pivot_x
    dy = mouse_y - pivot_y
    if dx * dx + dy * dy < 4.0:
        return None
    return math.atan2(dy, dx)


def apply_precision(delta: float, precision: bool, factor: float = PRECISION_FACTOR) -> float:
    return delta * factor if precision else delta


@dataclass
class PrecisionAccumulator:
    """Rebase mouse deltas when Shift is pressed or released.

    Native R keeps the current angle and only scales further motion. Scaling
    the whole gesture from invoke would jump back toward the start pose.
    """

    base: float = 0.0
    anchor: float = 0.0
    precision: bool = False
    primed: bool = False


def accumulate_precision(
    state: PrecisionAccumulator,
    raw: float,
    precision: bool,
    factor: float = PRECISION_FACTOR,
) -> tuple[PrecisionAccumulator, float]:
    """Return updated state and theta = committed + scaled motion since last Shift change."""
    if not state.primed:
        state = PrecisionAccumulator(base=0.0, anchor=0.0, precision=precision, primed=True)
    elif precision != state.precision:
        committed = state.base + apply_precision(raw - state.anchor, state.precision, factor)
        state = PrecisionAccumulator(base=committed, anchor=raw, precision=precision, primed=True)
    theta = state.base + apply_precision(raw - state.anchor, state.precision, factor)
    return state, theta


def snap_angle(theta: float, increment: float) -> float:
    if increment <= 0.0:
        return theta
    return round(theta / increment) * increment


def select_snap_increment(
    snap: bool,
    precision: bool,
    increment: float,
    precision_increment: float,
) -> float | None:
    """Return the angle step while Ctrl is held, else None."""
    if not snap:
        return None
    if precision:
        return precision_increment if precision_increment > 0.0 else DEFAULT_PRECISION_SNAP_RADIANS
    return increment if increment > 0.0 else DEFAULT_SNAP_RADIANS


def screen_scale_factor(
    mouse_x: float,
    mouse_y: float,
    pivot_x: float,
    pivot_y: float,
    start_x: float,
    start_y: float,
) -> float | None:
    """Signed scale factor from mouse vs invoke position around a screen pivot.

    Projection onto the starting mouse radial, so crossing the pivot mirrors
    (negative factor) like native S. None when the start point is too close
    to the pivot to define a ratio.
    """
    start_dx = start_x - pivot_x
    start_dy = start_y - pivot_y
    denom = start_dx * start_dx + start_dy * start_dy
    if denom < 4.0:
        return None
    current_dx = mouse_x - pivot_x
    current_dy = mouse_y - pivot_y
    return (current_dx * start_dx + current_dy * start_dy) / denom


def mouse_delta_scale_fallback(
    start_x: float,
    mouse_x: float,
    pixels_per_unit: float = 200.0,
) -> float:
    """Horizontal-drag fallback: 200px right is scale 2.0."""
    if pixels_per_unit <= 0.0:
        return 1.0
    return 1.0 + (mouse_x - start_x) / pixels_per_unit


def mouse_delta_fallback(start_x: float, mouse_x: float, pixels_per_radian: float = 200.0) -> float:
    """Horizontal-drag fallback when the pivot is off-screen or behind the camera."""
    if pixels_per_radian <= 0.0:
        return 0.0
    return (mouse_x - start_x) / pixels_per_radian


def numeric_handle_key(state: NumericInput, event_type: str, unicode_char: str) -> tuple[bool, NumericInput]:
    """Feed one key into simple numeric entry. Returns (handled, next_state)."""
    if event_type in {"BACK_SPACE", "BACKSPACE"}:
        if not state.active:
            return False, state
        if state.text:
            return True, NumericInput(active=True, text=state.text[:-1])
        return True, NumericInput(active=False, text="")

    digit = _DIGIT_KEYS.get(event_type)
    if digit is None and unicode_char and unicode_char in "0123456789":
        digit = unicode_char
    if digit is not None:
        return True, NumericInput(active=True, text=state.text + digit)

    if event_type in {"PERIOD", "NUMPAD_PERIOD"} or unicode_char == ".":
        if "." in state.text:
            return True, state
        prefix = state.text if state.active else ""
        return True, NumericInput(active=True, text=prefix + ".")

    if event_type in {"MINUS", "NUMPAD_MINUS"} or unicode_char == "-":
        if not state.active or state.text == "":
            return True, NumericInput(active=True, text="-")
        if state.text.startswith("-"):
            return True, NumericInput(active=True, text=state.text[1:])
        return True, NumericInput(active=True, text="-" + state.text)

    return False, state


def modal_status_hints(extend_rails: bool) -> tuple[tuple[tuple[str, ...], str], ...]:
    """Key chips for the workspace status bar, same idea as native R."""
    clamp_label = "Clamp" if extend_rails else "Extend Rails"
    return (
        (("MOUSE_LMB", "EVENT_RETURN"), "Confirm"),
        (("MOUSE_RMB", "EVENT_ESC"), "Cancel"),
        (("EVENT_SHIFT",), "Precision"),
        (("EVENT_CTRL",), "Snap"),
        (("EVENT_C",), clamp_label),
        (("EVENT_X",), "X Axis"),
        (("EVENT_Y",), "Y Axis"),
        (("EVENT_Z",), "Z Axis"),
    )


def format_status_text(
    angle: float,
    axis_name: str,
    extend_rails: bool,
    frozen: int,
    numeric: NumericInput,
    mode: str = MODE_ROTATE,
    factor: float = 1.0,
) -> str:
    """Viewport header line during the modal."""
    if mode == MODE_SCALE:
        title = "Slide Scale"
        if numeric.active:
            shown = numeric.text if numeric.text else "1"
            value_part = f"Scale: {shown}"
        else:
            value_part = f"Scale: {factor:.3f}"
    else:
        title = "Slide Rotate"
        degrees = math.degrees(angle)
        if numeric.active:
            shown = numeric.text if numeric.text else "0"
            value_part = f"Angle: {shown}°"
        else:
            value_part = f"Angle: {degrees:.1f}°"
    clamp_part = "Extend Rails | C: Clamp" if extend_rails else "Clamped | C: Extend"
    frozen_part = f" | Frozen: {frozen}" if frozen else ""
    return f"{title} | {value_part} | Axis: {axis_name} | {clamp_part}{frozen_part}"


def numeric_value_radians(state: NumericInput) -> float | None:
    """Parse typed degrees into radians, or None while the buffer is incomplete."""
    parsed = numeric_value_number(state)
    if parsed is None:
        return None
    return math.radians(parsed)


def numeric_value_number(state: NumericInput) -> float | None:
    """Parse typed numeric input as a raw float, or None while incomplete."""
    if not state.active:
        return None
    text = state.text.strip()
    if text in {"", "-", ".", "-."}:
        return None
    try:
        return float(text)
    except ValueError:
        return None
