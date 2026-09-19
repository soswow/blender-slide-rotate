"""Pivot helpers and world/local point conversion."""

from __future__ import annotations

from .vec import Mat4, Vec3, invert_affine_mat4, mul_mat4_point, scale


def median_point(points: list[Vec3]) -> Vec3 | None:
    if not points:
        return None
    total = (0.0, 0.0, 0.0)
    for point in points:
        total = (total[0] + point[0], total[1] + point[1], total[2] + point[2])
    count = float(len(points))
    return (total[0] / count, total[1] / count, total[2] / count)


def bounding_box_center(points: list[Vec3]) -> Vec3 | None:
    if not points:
        return None
    min_corner = list(points[0])
    max_corner = list(points[0])
    for point in points[1:]:
        for index in range(3):
            min_corner[index] = min(min_corner[index], point[index])
            max_corner[index] = max(max_corner[index], point[index])
    return scale(
        (
            min_corner[0] + max_corner[0],
            min_corner[1] + max_corner[1],
            min_corner[2] + max_corner[2],
        ),
        0.5,
    )


def choose_pivot(
    mode: str,
    points: list[Vec3],
    cursor: Vec3 | None,
    active: Vec3 | None,
) -> Vec3 | None:
    """World-space pivot. Individual Origins falls back to median."""
    if mode == "CURSOR":
        return cursor
    if mode == "ACTIVE_ELEMENT":
        return active if active is not None else median_point(points)
    if mode == "BOUNDING_BOX_CENTER":
        return bounding_box_center(points)
    return median_point(points)


def world_from_local(local: Vec3, matrix_world: Mat4) -> Vec3:
    return mul_mat4_point(matrix_world, local)


def local_from_world(world: Vec3, matrix_world: Mat4, inverted: Mat4 | None = None) -> Vec3:
    inverse = inverted if inverted is not None else invert_affine_mat4(matrix_world)
    return mul_mat4_point(inverse, world)
