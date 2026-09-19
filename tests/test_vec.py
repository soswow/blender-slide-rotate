from core.vec import (
    add,
    almost_equal,
    invert_affine_mat4,
    mul_mat4_point,
    rotate_around_axis,
    scale,
    vec3,
)


def test_vec3_roundtrip() -> None:
    assert vec3((1, 2, 3)) == (1.0, 2.0, 3.0)


def test_rotate_around_z_90_degrees() -> None:
    point = rotate_around_axis((1.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 3.141592653589793 / 2.0)
    assert almost_equal(point, (0.0, 1.0, 0.0), 1e-8)


def test_invert_affine_with_nonuniform_scale() -> None:
    matrix = (
        (2.0, 0.0, 0.0, 10.0),
        (0.0, 0.5, 0.0, -3.0),
        (0.0, 0.0, 4.0, 1.0),
        (0.0, 0.0, 0.0, 1.0),
    )
    inverse = invert_affine_mat4(matrix)
    local = (1.5, -2.0, 0.25)
    world = mul_mat4_point(matrix, local)
    restored = mul_mat4_point(inverse, world)
    assert almost_equal(restored, local, 1e-9)


def test_add_scale() -> None:
    assert add((1.0, 0.0, 0.0), scale((0.0, 1.0, 0.0), 2.0)) == (1.0, 2.0, 0.0)
