import math

from core.input import (
    DEFAULT_SNAP_RADIANS,
    NumericInput,
    apply_precision,
    mouse_delta_fallback,
    numeric_handle_key,
    numeric_value_radians,
    screen_angle,
    select_snap_increment,
    snap_angle,
    wrap_angle_delta,
)


def test_wrap_angle_delta_crosses_pi() -> None:
    start = math.pi - 0.1
    current = -math.pi + 0.1
    delta = wrap_angle_delta(start, current)
    assert abs(delta - 0.2) < 1e-9


def test_wrap_angle_delta_negative_cross() -> None:
    start = -math.pi + 0.1
    current = math.pi - 0.1
    delta = wrap_angle_delta(start, current)
    assert abs(delta + 0.2) < 1e-9


def test_screen_angle_and_close_pivot() -> None:
    angle = screen_angle(10.0, 10.0, 0.0, 0.0)
    assert angle is not None
    assert abs(angle - math.pi / 4.0) < 1e-9
    assert screen_angle(0.5, 0.5, 0.0, 0.0) is None


def test_precision_scales_delta() -> None:
    assert apply_precision(2.0, False) == 2.0
    assert apply_precision(2.0, True) == 0.2


def test_snap_angle_five_degrees() -> None:
    increment = math.radians(5.0)
    snapped = snap_angle(math.radians(13.0), increment)
    assert abs(snapped - math.radians(15.0)) < 1e-9
    assert snap_angle(0.4, 0.0) == 0.4


def test_select_snap_increment() -> None:
    assert select_snap_increment(False, False, 0.1, 0.02) is None
    assert select_snap_increment(True, False, 0.1, 0.02) == 0.1
    assert select_snap_increment(True, True, 0.1, 0.02) == 0.02
    assert select_snap_increment(True, False, 0.0, 0.0) == DEFAULT_SNAP_RADIANS


def test_mouse_delta_fallback() -> None:
    assert abs(mouse_delta_fallback(0.0, 200.0, 200.0) - 1.0) < 1e-9


def test_numeric_input_degrees() -> None:
    state = NumericInput()
    handled, state = numeric_handle_key(state, "FOUR", "")
    assert handled
    handled, state = numeric_handle_key(state, "FIVE", "")
    assert handled
    handled, state = numeric_handle_key(state, "PERIOD", "")
    handled, state = numeric_handle_key(state, "FIVE", "")
    assert numeric_value_radians(state) == math.radians(45.5)


def test_numeric_minus_and_backspace() -> None:
    state = NumericInput()
    _, state = numeric_handle_key(state, "MINUS", "")
    _, state = numeric_handle_key(state, "THREE", "")
    _, state = numeric_handle_key(state, "ZERO", "")
    assert numeric_value_radians(state) == math.radians(-30.0)
    _, state = numeric_handle_key(state, "MINUS", "")
    assert numeric_value_radians(state) == math.radians(30.0)
    _, state = numeric_handle_key(state, "BACK_SPACE", "")
    _, state = numeric_handle_key(state, "BACK_SPACE", "")
    assert numeric_value_radians(state) is None
    _, state = numeric_handle_key(state, "BACK_SPACE", "")
    assert state.active is False


def test_numeric_empty_unicode_is_not_a_digit() -> None:
    """Regression: ``"" in "0123456789"`` is True in Python; ignore empty unicode."""
    handled, state = numeric_handle_key(NumericInput(), "PERIOD", "")
    assert handled
    assert state.text == "."
    handled, state = numeric_handle_key(NumericInput(), "C", "")
    assert handled is False



def test_status_text_extend_and_frozen() -> None:
    from core.input import format_status_text

    text = format_status_text(math.radians(17.4), "View", True, 2, NumericInput())
    assert "Angle: 17.4°" in text
    assert "Axis: View" in text
    assert "Extend Rails | C: Clamp" in text
    assert "Frozen: 2" in text
    typed = format_status_text(0.0, "Global X", False, 0, NumericInput(active=True, text="45"))
    assert typed == "Slide Rotate | Angle: 45° | Axis: Global X | Clamped | C: Extend"
