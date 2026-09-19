"""Modal-only GPU overlay of cached guide rails."""

from __future__ import annotations

import gpu
from gpu_extras.batch import batch_for_shader

import bpy

from ..core.geometry import overlay_segment
from ..core.types import VertexRailState

_draw_handle = None
_states: list[VertexRailState] = []
_extend_rails = True
_RAIL_COLOR = (0.95, 0.75, 0.15, 0.9)


def set_rails(states: list[VertexRailState], extend_rails: bool) -> None:
    global _states, _extend_rails
    _states = states
    _extend_rails = extend_rails


def clear_rails() -> None:
    global _states
    _states = []


def _draw() -> None:
    coords: list[tuple[float, float, float]] = []
    for state in _states:
        if state.rail is None:
            continue
        start, end = overlay_segment(state.rail, _extend_rails)
        coords.append(start)
        coords.append(end)
    if not coords:
        return
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.line_width_set(1.5)
    gpu.state.blend_set("ALPHA")
    batch = batch_for_shader(shader, "LINES", {"pos": coords})
    shader.bind()
    shader.uniform_float("color", _RAIL_COLOR)
    batch.draw(shader)
    gpu.state.blend_set("NONE")


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
