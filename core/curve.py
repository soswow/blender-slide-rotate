"""Loop/path walking and low-order curve fits for Slide Curve (no bpy).

Open chains get a pinned polynomial (ends stay). Closed chains get a
trigonometric polynomial (Fourier harmonics). Order is how much shape the
imaginary line may keep.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .vec import EPS, Vec3, add, dot, length, length_squared, lerp, normalize, project_to_plane, scale, sub

MAX_CURVE_ORDER = 8
DEFAULT_CURVE_ORDER = 3
OVERLAY_SAMPLES = 32


@dataclass(frozen=True)
class VertexChain:
    """Ordered selected vertices that form one path or loop."""

    indices: tuple[int, ...]
    closed: bool


@dataclass(frozen=True)
class FittedCurve:
    """Evaluatable curve on parameter ``s`` in [0, 1] (closed: period 1)."""

    closed: bool
    order: int
    kind: str
    coeffs: tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]


def max_order_for_chain(count: int, closed: bool) -> int:
    if count < 2:
        return 1
    if closed:
        return max(1, min(MAX_CURVE_ORDER, (count - 1) // 2))
    return max(1, min(MAX_CURVE_ORDER, count - 1))


def clamp_curve_order(order: int, count: int, closed: bool) -> int:
    return min(max(1, int(order)), max_order_for_chain(count, closed))


def selection_max_curve_order(chains: list[VertexChain]) -> int:
    if not chains:
        return 1
    return max(max_order_for_chain(len(chain.indices), chain.closed) for chain in chains)


def step_curve_order(order: int, delta: int, maximum: int) -> int:
    return min(max(1, int(order) + int(delta)), max(1, int(maximum)))


def walk_selected_chains(
    selected: list[int],
    edges: list[tuple[int, int]],
) -> list[VertexChain]:
    """Walk the selected-selected edge graph into open paths and closed loops."""
    selected_set = set(selected)
    adjacency: dict[int, list[int]] = {index: [] for index in selected}
    for start, end in edges:
        if start not in selected_set or end not in selected_set or start == end:
            continue
        if end not in adjacency[start]:
            adjacency[start].append(end)
        if start not in adjacency[end]:
            adjacency[end].append(start)

    used: set[tuple[int, int]] = set()
    chains: list[VertexChain] = []

    def edge_key(left: int, right: int) -> tuple[int, int]:
        return (left, right) if left < right else (right, left)

    def unused_neighbors(index: int) -> list[int]:
        return [other for other in adjacency[index] if edge_key(index, other) not in used]

    def trace_open(start: int, first: int) -> list[int]:
        path = [start]
        previous, current = start, first
        used.add(edge_key(previous, current))
        while True:
            path.append(current)
            if len(adjacency[current]) != 2:
                break
            nxts = unused_neighbors(current)
            if not nxts:
                break
            nxt = nxts[0]
            used.add(edge_key(current, nxt))
            previous, current = current, nxt
        return path

    endpoints = [
        index
        for index in selected
        if len(adjacency[index]) == 1 or len(adjacency[index]) >= 3
    ]
    for start in endpoints:
        for first in list(adjacency[start]):
            if edge_key(start, first) in used:
                continue
            path = trace_open(start, first)
            if len(path) >= 2:
                chains.append(VertexChain(indices=tuple(path), closed=False))

    for start in selected:
        leftovers = unused_neighbors(start)
        if not leftovers:
            continue
        first = leftovers[0]
        path = [start]
        previous, current = start, first
        used.add(edge_key(previous, current))
        closed = False
        while True:
            if current == start:
                closed = True
                break
            path.append(current)
            nxts = unused_neighbors(current)
            if not nxts:
                break
            nxt = nxts[0]
            used.add(edge_key(current, nxt))
            previous, current = current, nxt
        if closed and len(path) >= 3:
            chains.append(VertexChain(indices=tuple(path), closed=True))
        elif len(path) >= 2:
            chains.append(VertexChain(indices=tuple(path), closed=False))
    return chains


def chord_parameters(points: list[Vec3], closed: bool) -> list[float]:
    """Chord-length ``s`` in [0, 1] (closed: last vertex strictly below 1)."""
    count = len(points)
    if count == 0:
        return []
    if count == 1:
        return [0.0]
    segments: list[float] = []
    span = count if closed else count - 1
    for index in range(span):
        nxt = (index + 1) % count
        segments.append(length(sub(points[nxt], points[index])))
    total = sum(segments)
    if total <= EPS:
        denom = float(count - 1) if not closed else float(count)
        return [index / denom for index in range(count)]
    parameters = [0.0]
    accumulated = 0.0
    for index in range(count - 1):
        accumulated += segments[index]
        parameters.append(accumulated / total)
    return parameters


def _solve_linear_system(matrix: list[list[float]], rhs: list[float]) -> list[float] | None:
    """Gaussian elimination with partial pivoting."""
    size = len(rhs)
    if size == 0 or any(len(row) != size for row in matrix):
        return None
    work = [row[:] + [value] for row, value in zip(matrix, rhs)]
    for column in range(size):
        pivot_row = max(range(column, size), key=lambda row: abs(work[row][column]))
        if abs(work[pivot_row][column]) <= 1e-12:
            return None
        work[column], work[pivot_row] = work[pivot_row], work[column]
        pivot = work[column][column]
        for col in range(column, size + 1):
            work[column][col] /= pivot
        for row in range(size):
            if row == column:
                continue
            factor = work[row][column]
            if abs(factor) <= EPS:
                continue
            for col in range(column, size + 1):
                work[row][col] -= factor * work[column][col]
    return [work[index][size] for index in range(size)]


def _least_squares(design: list[list[float]], values: list[float]) -> list[float] | None:
    if not design or not values or len(design) != len(values):
        return None
    width = len(design[0])
    if width == 0 or any(len(row) != width for row in design):
        return None
    ata = [[0.0] * width for _ in range(width)]
    atb = [0.0] * width
    for row, value in zip(design, values):
        for i_index in range(width):
            atb[i_index] += row[i_index] * value
            for j_index in range(width):
                ata[i_index][j_index] += row[i_index] * row[j_index]
    return _solve_linear_system(ata, atb)


def _fit_poly_axis(parameters: list[float], values: list[float], degree: int) -> tuple[float, ...] | None:
    start = values[0]
    end = values[-1]
    if degree <= 1:
        return (start, end - start)
    design: list[list[float]] = []
    rhs: list[float] = []
    for parameter, value in zip(parameters, values):
        if parameter <= 1e-12 or parameter >= 1.0 - 1e-12:
            continue
        power_end = parameter**degree
        design.append([parameter**power - power_end for power in range(1, degree)])
        rhs.append(value - start * (1.0 - power_end) - end * power_end)
    if not design:
        return (start, end - start)
    free = _least_squares(design, rhs)
    if free is None:
        return (start, end - start)
    last = end - start - sum(free)
    return (start, *free, last)


def _fit_fourier_axis(parameters: list[float], values: list[float], order: int) -> tuple[float, ...] | None:
    design: list[list[float]] = []
    for parameter in parameters:
        row = [1.0]
        for harmonic in range(1, order + 1):
            angle = 2.0 * math.pi * harmonic * parameter
            row.append(math.cos(angle))
            row.append(math.sin(angle))
        design.append(row)
    solved = _least_squares(design, values)
    if solved is None:
        return None
    return tuple(solved)


def _eval_poly(coeffs: tuple[float, ...], parameter: float) -> float:
    acc = 0.0
    for coeff in reversed(coeffs):
        acc = acc * parameter + coeff
    return acc


def _eval_fourier(coeffs: tuple[float, ...], parameter: float) -> float:
    acc = coeffs[0]
    harmonic = 1
    index = 1
    while index + 1 < len(coeffs):
        angle = 2.0 * math.pi * harmonic * parameter
        acc += coeffs[index] * math.cos(angle) + coeffs[index + 1] * math.sin(angle)
        index += 2
        harmonic += 1
    return acc


def evaluate_curve(curve: FittedCurve, parameter: float) -> Vec3:
    if curve.kind == "fourier":
        return (
            _eval_fourier(curve.coeffs[0], parameter),
            _eval_fourier(curve.coeffs[1], parameter),
            _eval_fourier(curve.coeffs[2], parameter),
        )
    return (
        _eval_poly(curve.coeffs[0], parameter),
        _eval_poly(curve.coeffs[1], parameter),
        _eval_poly(curve.coeffs[2], parameter),
    )


def fit_chain_curve(points: list[Vec3], closed: bool, order: int) -> FittedCurve | None:
    """Least-squares curve through ``points``, or None if they collapse."""
    count = len(points)
    if count < 2:
        return None
    used_order = clamp_curve_order(order, count, closed)
    parameters = chord_parameters(points, closed)
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    zs = [point[2] for point in points]
    if closed:
        if count < 3:
            return None
        cx = _fit_fourier_axis(parameters, xs, used_order)
        cy = _fit_fourier_axis(parameters, ys, used_order)
        cz = _fit_fourier_axis(parameters, zs, used_order)
        if cx is None or cy is None or cz is None:
            return None
        return FittedCurve(closed=True, order=used_order, kind="fourier", coeffs=(cx, cy, cz))
    px = _fit_poly_axis(parameters, xs, used_order)
    py = _fit_poly_axis(parameters, ys, used_order)
    pz = _fit_poly_axis(parameters, zs, used_order)
    if px is None or py is None or pz is None:
        return None
    return FittedCurve(closed=False, order=used_order, kind="poly", coeffs=(px, py, pz))


def chain_points(
    chain: VertexChain,
    worlds: dict[int, Vec3],
    plane_origin: Vec3 | None = None,
    plane_normal: Vec3 | None = None,
) -> list[Vec3]:
    points = [worlds[index] for index in chain.indices]
    if plane_origin is None or plane_normal is None:
        return points
    unit = normalize(plane_normal)
    if unit is None:
        return points
    return [project_to_plane(point, plane_origin, plane_normal) for point in points]


def fit_curve_targets(
    chains: list[VertexChain],
    worlds: dict[int, Vec3],
    order: int,
    plane_origin: Vec3 | None = None,
    plane_normal: Vec3 | None = None,
) -> dict[int, Vec3]:
    """Map each chained vertex to its factor-1 curve sample."""
    targets: dict[int, Vec3] = {}
    for chain in chains:
        points = chain_points(chain, worlds, plane_origin, plane_normal)
        fitted = fit_chain_curve(points, chain.closed, order)
        if fitted is None:
            continue
        parameters = chord_parameters(points, chain.closed)
        for index, parameter in zip(chain.indices, parameters):
            targets[index] = evaluate_curve(fitted, parameter)
    return targets


def sample_curve_polyline(
    chain: VertexChain,
    worlds: dict[int, Vec3],
    order: int,
    plane_origin: Vec3 | None = None,
    plane_normal: Vec3 | None = None,
    samples: int = OVERLAY_SAMPLES,
) -> list[Vec3]:
    points = chain_points(chain, worlds, plane_origin, plane_normal)
    fitted = fit_chain_curve(points, chain.closed, order)
    if fitted is None:
        return []
    count = max(2, int(samples))
    if chain.closed:
        parameters = [index / count for index in range(count + 1)]
    else:
        parameters = [index / (count - 1) for index in range(count)]
    return [evaluate_curve(fitted, parameter) for parameter in parameters]


def unconstrained_curved_point(original: Vec3, target: Vec3, factor: float) -> Vec3:
    """Lerp from the start pose toward the fitted curve sample."""
    return lerp(original, target, factor)


def closest_point_on_polyline(point: Vec3, polyline: list[Vec3]) -> Vec3:
    """Closest point on a polyline (including segment interiors) to ``point``."""
    if not polyline:
        return point
    best = polyline[0]
    best_dist = length_squared(sub(point, best))
    for index in range(len(polyline) - 1):
        start = polyline[index]
        end = polyline[index + 1]
        span = sub(end, start)
        denom = length_squared(span)
        if denom <= EPS:
            candidate = start
        else:
            parameter = max(0.0, min(1.0, dot(sub(point, start), span) / denom))
            candidate = add(start, scale(span, parameter))
        dist = length_squared(sub(point, candidate))
        if dist < best_dist:
            best_dist = dist
            best = candidate
    return best


def curve_score_direction(original: Vec3, target: Vec3, fallback: Vec3) -> Vec3:
    motion = sub(target, original)
    unit = normalize(motion)
    if unit is not None:
        return unit
    fallback_unit = normalize(fallback)
    return fallback_unit if fallback_unit is not None else (0.0, 0.0, 1.0)
