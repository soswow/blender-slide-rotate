"""Modal-only GPU overlay of cached guide rails and the lock axis."""

from __future__ import annotations

import gpu
from gpu_extras.batch import batch_for_shader

import bpy

from ..core.axis import axis_overlay_color
from ..core.geometry import overlay_axis_segment, overlay_segment
from ..core.types import VertexRailState
from ..core.vec import Vec3

_draw_handle = None
_states: list[VertexRailState] = []
_extend_rails = True
_lock_pivot: Vec3 | None = None
_lock_axis: Vec3 | None = None
_lock_letter: str | None = None
_RAIL_COLOR = (0.95, 0.75, 0.15, 0.9)


def set_rails(states: list[VertexRailState], extend_rails: bool) -> None:
    global _states, _extend_rails
    _states = states
    _extend_rails = extend_rails


def set_lock_axis(pivot: Vec3 | None, axis: Vec3 | None, letter: str | None) -> None:
    global _lock_pivot, _lock_axis, _lock_letter
    _lock_pivot = pivot
    _lock_axis = axis
    _lock_letter = letter


def clear_rails() -> None:
    global _states, _lock_pivot, _lock_axis, _lock_letter
    _states = []
    _lock_pivot = None
    _lock_axis = None
    _lock_letter = None


def _draw_lines(coords: list[tuple[float, float, float]], color: tuple[float, float, float, float], width: float) -> None:
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.line_width_set(width)
    gpu.state.blend_set("ALPHA")
    batch = batch_for_shader(shader, "LINES", {"pos": coords})
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)
    gpu.state.blend_set("NONE")


def _draw_polyline(coords: list[tuple[float, float, float]], color: tuple[float, float, float, float], width: float) -> None:
    # POLYLINE_* is Blender's anti-aliased wide-line shader (same as native R).
    shader = gpu.shader.from_builtin("POLYLINE_UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")
    shader.bind()
    shader.uniform_float("viewportSize", gpu.state.viewport_get()[2:])
    shader.uniform_float("lineWidth", width)
    shader.uniform_float("color", color)
    batch = batch_for_shader(shader, "LINES", {"pos": coords})
    batch.draw(shader)
    gpu.state.blend_set("NONE")


def _theme_axis_color(letter: str) -> tuple[float, float, float, float]:
    fallback = axis_overlay_color(letter)
    color = fallback if fallback is not None else (1.0, 1.0, 1.0, 1.0)
    try:
        theme = bpy.context.preferences.themes[0].user_interface
        rgb = getattr(theme, f"axis_{letter.lower()}")
        mixed = axis_overlay_color(letter, (float(rgb[0]), float(rgb[1]), float(rgb[2])))
        return mixed if mixed is not None else color
    except (AttributeError, IndexError, TypeError, KeyError):
        return color


def _axis_line_width() -> float:
    # Native R uses pixelsize * 2; a bit thicker so the lock axis reads clearly.
    system = getattr(getattr(bpy.context, "preferences", None), "system", None)
    pixel_size = float(getattr(system, "pixel_size", 1.0) or 1.0)
    return max(3.0, pixel_size * 3.0)


def _axis_half_length(pivot: Vec3) -> float:
    space = getattr(bpy.context, "space_data", None)
    clip_end = float(getattr(space, "clip_end", 1000.0) or 1000.0)
    rv3d = getattr(bpy.context, "region_data", None)
    distance = float(getattr(rv3d, "view_distance", 0.0) or 0.0)
    extent = max(abs(pivot[0]), abs(pivot[1]), abs(pivot[2]), 1.0)
    return max(clip_end, distance, extent) * 10.0


def _draw() -> None:
    coords: list[tuple[float, float, float]] = []
    for state in _states:
        if state.rail is None:
            continue
        start, end = overlay_segment(state.rail, _extend_rails)
        coords.append(start)
        coords.append(end)
    if coords:
        _draw_lines(coords, _RAIL_COLOR, 1.5)

    if _lock_letter is None or _lock_pivot is None or _lock_axis is None:
        return
    segment = overlay_axis_segment(_lock_pivot, _lock_axis, _axis_half_length(_lock_pivot))
    if segment is None:
        return
    gpu.state.depth_test_set("NONE")
    _draw_polyline([segment[0], segment[1]], _theme_axis_color(_lock_letter), _axis_line_width())
    gpu.state.depth_test_set("LESS_EQUAL")


def ensure_draw_handler() -> None:
    global _draw_handle
    if _draw_handle is not None:
        return
    _draw_handle = bpy.types.SpaceView3D.draw_handler_add(_draw, (), "WINDOW", "POST_VIEW")


def remove_draw_handler() -> None:
    global _draw_handle
    if _draw_handle is None:
        return
    try:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, "WINDOW")
    except ValueError:
        pass
    _draw_handle = None
    clear_rails()
