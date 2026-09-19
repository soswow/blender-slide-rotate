"""Dataclasses for rails, vertex cache, and axis-lock state."""

from __future__ import annotations

from dataclasses import dataclass

from .vec import Vec3

MODE_ROTATE = "ROTATE"
MODE_SCALE = "SCALE"
MODE_FLATTEN = "FLATTEN"


@dataclass(frozen=True)
class Rail:
    """Parametric line ``origin + t * direction`` with a physical clamp interval."""

    origin: Vec3
    direction: Vec3
    t_min: float
    t_max: float
    merged: bool = False


@dataclass
class VertexRailState:
    """Cached per-vertex data captured once when a Slide mode starts."""

    index: int
    original_world: Vec3
    original_local: Vec3
    rail: Rail | None
    movable: bool
    last_t: float = 0.0
    used_fallback: bool = False


@dataclass(frozen=True)
class AxisLockState:
    """Native-R style X/Y/Z cycling: view → orientation → global/local flip → view."""

    letter: str | None = None
    stage: int = 0


@dataclass
class NumericInput:
    """Simple typed-degree buffer (no units or expressions)."""

    active: bool = False
    text: str = ""
