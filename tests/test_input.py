import math

from core.input import (
    DEFAULT_SNAP_RADIANS,
    NumericInput,
    PrecisionAccumulator,
    accumulate_precision,
    apply_precision,
    modal_status_hints,
    mouse_delta_fallback,
    mouse_delta_scale_fallback,
    numeric_handle_key,
    numeric_value_number,
    numeric_value_radians,
    screen_angle,
    screen_scale_factor,
    select_snap_increment,
    snap_angle,
    wrap_angle_delta,
)
from core.types import MODE_FLATTEN, MODE_SCALE


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


def test_precision_after_move_keeps_current_angle() -> None:
    """Regression: Shift must not scale the whole gesture back toward zero."""
    state = PrecisionAccumulator()
    state, theta = accumulate_precision(state, 1.0, False)
    assert abs(theta - 1.0) < 1e-12
    state, theta = accumulate_precision(state, 1.0, True)
    assert abs(theta - 1.0) < 1e-12
    state, theta = accumulate_precision(state, 1.1, True)
    assert abs(theta - 1.01) < 1e-12
    state, theta = accumulate_precision(state, 1.1, False)
    assert abs(theta - 1.01) < 1e-12
    state, theta = accumulate_precision(state, 1.2, False)
    assert abs(theta - 1.11) < 1e-12


def test_precision_from_invoke_still_scales_whole_motion() -> None:
    state = PrecisionAccumulator()
    state, theta = accumulate_precision(state, 2.0, True)
    assert abs(theta - 0.2) < 1e-12


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


def test_modal_status_hints_match_operator_keys() -> None:
    extend = modal_status_hints(True)
    clamp = modal_status_hints(False)
    labels = [label for _icons, label in extend]
    assert labels == [
        "Confirm",
        "Cancel",
        "Precision",
        "Snap",
        "Clamp",
        "X Axis",
        "Y Axis",
        "Z Axis",
    ]
    assert clamp[4][1] == "Extend Rails"
    assert extend[0][0] == ("MOUSE_LMB", "EVENT_RETURN")
    assert extend[1][0] == ("MOUSE_RMB", "EVENT_ESC")
    assert extend[4][0] == ("EVENT_C",)
    assert extend[5][0] == ("EVENT_X",)


def test_screen_scale_factor_ratio_and_mirror() -> None:
    assert screen_scale_factor(20.0, 0.0, 0.0, 0.0, 10.0, 0.0) == 2.0
    assert screen_scale_factor(-10.0, 0.0, 0.0, 0.0, 10.0, 0.0) == -1.0
    assert screen_scale_factor(0.5, 0.0, 0.0, 0.0, 1.0, 0.0) is None


def test_mouse_delta_scale_fallback() -> None:
    assert abs(mouse_delta_scale_fallback(0.0, 200.0, 200.0) - 2.0) < 1e-9


def test_numeric_value_number_is_not_degrees() -> None:
    state = NumericInput()
    _, state = numeric_handle_key(state, "TWO", "")
    assert numeric_value_number(state) == 2.0
    assert numeric_value_radians(state) == math.radians(2.0)


def test_status_text_scale_mode() -> None:
    from core.input import format_status_text

    text = format_status_text(
        0.0,
        "View",
        True,
        0,
        NumericInput(),
        mode=MODE_SCALE,
        factor=1.5,
    )
    assert text == "Slide Scale | Scale: 1.500 | Axis: View | Extend Rails | C: Clamp"
    typed = format_status_text(
        0.0,
        "Global X",
        False,
        0,
        NumericInput(active=True, text="2"),
        mode=MODE_SCALE,
        factor=1.0,
    )
    assert typed == "Slide Scale | Scale: 2 | Axis: Global X | Clamped | C: Extend"


def test_status_text_flatten_mode() -> None:
    from core.input import format_status_text

    text = format_status_text(
        0.0,
        "Best Fit",
        True,
        0,
        NumericInput(),
        mode=MODE_FLATTEN,
        factor=1.0,
    )
    assert text == "Slide Flatten | Flatten: 1.000 | Axis: Best Fit | Extend Rails | C: Clamp"
    typed = format_status_text(
        0.0,
        "Global Z",
        False,
        0,
        NumericInput(active=True, text="0.5"),
        mode=MODE_FLATTEN,
        factor=0.0,
    )
    assert typed == "Slide Flatten | Flatten: 0.5 | Axis: Global Z | Clamped | C: Extend"
