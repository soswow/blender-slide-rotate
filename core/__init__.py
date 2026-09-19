"""Pure Slide Rotate math. Safe to import without bpy."""

from .axis import lock_label, locked_axis_vector, press_axis_key
from .geometry import (
    apply_vertex_theta,
    build_vertex_state,
    choose_rail,
    clamp_t,
    overlay_segment,
    solve_rail_parameter,
    transformed_world,
)
from .input import (
    apply_precision,
    format_status_text,
    mouse_delta_fallback,
    numeric_handle_key,
    numeric_value_radians,
    screen_angle,
    select_snap_increment,
    snap_angle,
    wrap_angle_delta,
)
from .transforms import bounding_box_center, choose_pivot, local_from_world, median_point, world_from_local
from .types import AxisLockState, NumericInput, Rail, VertexRailState

__all__ = (
    "AxisLockState",
    "NumericInput",
    "Rail",
    "VertexRailState",
    "apply_precision",
    "apply_vertex_theta",
    "bounding_box_center",
    "build_vertex_state",
    "choose_pivot",
    "choose_rail",
    "clamp_t",
    "format_status_text",
    "local_from_world",
    "lock_label",
    "locked_axis_vector",
    "median_point",
    "mouse_delta_fallback",
    "numeric_handle_key",
    "numeric_value_radians",
    "overlay_segment",
    "press_axis_key",
    "screen_angle",
    "select_snap_increment",
    "snap_angle",
    "solve_rail_parameter",
    "transformed_world",
    "world_from_local",
    "wrap_angle_delta",
)
