"""Small 3D vector helpers used by the geometry kernel.

Keep this independent of mathutils so pytest can run outside Blender.
"""

from __future__ import annotations

import math
from typing import Sequence

Vec3 = tuple[float, float, float]
Mat3 = tuple[Vec3, Vec3, Vec3]
Mat4 = tuple[tuple[float, float, float, float], ...]

EPS = 1e-10


def vec3(values: Sequence[float]) -> Vec3:
    return (float(values[0]), float(values[1]), float(values[2]))


def add(left: Vec3, right: Vec3) -> Vec3:
    return (left[0] + right[0], left[1] + right[1], left[2] + right[2])


def sub(left: Vec3, right: Vec3) -> Vec3:
    return (left[0] - right[0], left[1] - right[1], left[2] - right[2])


def scale(vector: Vec3, factor: float) -> Vec3:
    return (vector[0] * factor, vector[1] * factor, vector[2] * factor)


def negate(vector: Vec3) -> Vec3:
    return (-vector[0], -vector[1], -vector[2])


def dot(left: Vec3, right: Vec3) -> float:
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2]


def cross(left: Vec3, right: Vec3) -> Vec3:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def length_squared(vector: Vec3) -> float:
    return dot(vector, vector)


def length(vector: Vec3) -> float:
    return math.sqrt(length_squared(vector))


def normalize(vector: Vec3) -> Vec3 | None:
    magnitude = length(vector)
    if magnitude <= EPS:
        return None
    return scale(vector, 1.0 / magnitude)


def lerp(left: Vec3, right: Vec3, factor: float) -> Vec3:
    return add(left, scale(sub(right, left), factor))


def almost_equal(left: Vec3, right: Vec3, tolerance: float = 1e-6) -> bool:
    return length_squared(sub(left, right)) <= tolerance * tolerance


def identity_mat3() -> Mat3:
    return ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def column(matrix: Mat3, index: int) -> Vec3:
    return (matrix[0][index], matrix[1][index], matrix[2][index])


def mat3_from_columns(x_axis: Vec3, y_axis: Vec3, z_axis: Vec3) -> Mat3:
    return (
        (x_axis[0], y_axis[0], z_axis[0]),
        (x_axis[1], y_axis[1], z_axis[1]),
        (x_axis[2], y_axis[2], z_axis[2]),
    )


def mul_mat3_vec(matrix: Mat3, vector: Vec3) -> Vec3:
    return (
        matrix[0][0] * vector[0] + matrix[0][1] * vector[1] + matrix[0][2] * vector[2],
        matrix[1][0] * vector[0] + matrix[1][1] * vector[1] + matrix[1][2] * vector[2],
        matrix[2][0] * vector[0] + matrix[2][1] * vector[1] + matrix[2][2] * vector[2],
    )


def mul_mat4_point(matrix: Mat4, point: Vec3) -> Vec3:
    x, y, z = point
    rows = matrix
    rx = rows[0][0] * x + rows[0][1] * y + rows[0][2] * z + rows[0][3]
    ry = rows[1][0] * x + rows[1][1] * y + rows[1][2] * z + rows[1][3]
    rz = rows[2][0] * x + rows[2][1] * y + rows[2][2] * z + rows[2][3]
    rw = rows[3][0] * x + rows[3][1] * y + rows[3][2] * z + rows[3][3]
    if abs(rw - 1.0) > 1e-8 and abs(rw) > EPS:
        return (rx / rw, ry / rw, rz / rw)
    return (rx, ry, rz)


def invert_affine_mat4(matrix: Mat4) -> Mat4:
    """Invert a 4x4 affine transform (linear 3x3 plus translation)."""
    a, b, c = matrix[0][0], matrix[0][1], matrix[0][2]
    d, e, f = matrix[1][0], matrix[1][1], matrix[1][2]
    g, h, i = matrix[2][0], matrix[2][1], matrix[2][2]
    tx, ty, tz = matrix[0][3], matrix[1][3], matrix[2][3]

    det = (
        a * (e * i - f * h)
        - b * (d * i - f * g)
        + c * (d * h - e * g)
    )
    if abs(det) <= EPS:
        raise ValueError("matrix is not invertible")
    inv_det = 1.0 / det
    r00 = (e * i - f * h) * inv_det
    r01 = (c * h - b * i) * inv_det
    r02 = (b * f - c * e) * inv_det
    r10 = (f * g - d * i) * inv_det
    r11 = (a * i - c * g) * inv_det
    r12 = (c * d - a * f) * inv_det
    r20 = (d * h - e * g) * inv_det
    r21 = (b * g - a * h) * inv_det
    r22 = (a * e - b * d) * inv_det
    itx = -(r00 * tx + r01 * ty + r02 * tz)
    ity = -(r10 * tx + r11 * ty + r12 * tz)
    itz = -(r20 * tx + r21 * ty + r22 * tz)
    return (
        (r00, r01, r02, itx),
        (r10, r11, r12, ity),
        (r20, r21, r22, itz),
        (0.0, 0.0, 0.0, 1.0),
    )


def rotate_around_axis(point: Vec3, origin: Vec3, axis: Vec3, theta: float) -> Vec3:
    """Rodrigues rotation of ``point`` around ``origin`` + ``axis`` by ``theta``."""
    unit_axis = normalize(axis)
    if unit_axis is None:
        return point
    offset = sub(point, origin)
    cosine = math.cos(theta)
    sine = math.sin(theta)
    rotated = add(
        add(scale(offset, cosine), scale(cross(unit_axis, offset), sine)),
        scale(unit_axis, dot(unit_axis, offset) * (1.0 - cosine)),
    )
    return add(origin, rotated)


def project_to_plane(point: Vec3, origin: Vec3, axis: Vec3) -> Vec3:
    unit_axis = normalize(axis)
    if unit_axis is None:
        return point
    return sub(point, scale(unit_axis, dot(sub(point, origin), unit_axis)))


def plane_basis(axis: Vec3) -> tuple[Vec3, Vec3] | None:
    unit_axis = normalize(axis)
    if unit_axis is None:
        return None
    helper = (0.0, 0.0, 1.0) if abs(unit_axis[2]) < 0.9 else (0.0, 1.0, 0.0)
    first = normalize(cross(unit_axis, helper))
    if first is None:
        return None
    second = cross(unit_axis, first)
    return first, second
