from core.transforms import bounding_box_center, choose_pivot, local_from_world, median_point, world_from_local
from core.vec import almost_equal


def test_median_and_bounding_box() -> None:
    points = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 4.0, 0.0)]
    assert almost_equal(median_point(points), (2.0 / 3.0, 4.0 / 3.0, 0.0))
    assert almost_equal(bounding_box_center(points), (1.0, 2.0, 0.0))


def test_choose_pivot_modes() -> None:
    points = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0)]
    cursor = (9.0, 8.0, 7.0)
    active = (1.0, 2.0, 3.0)
    assert choose_pivot("CURSOR", points, cursor, active) == cursor
    assert choose_pivot("ACTIVE_ELEMENT", points, cursor, active) == active
    assert almost_equal(choose_pivot("MEDIAN_POINT", points, cursor, active), (1.0, 0.0, 0.0))
    assert almost_equal(choose_pivot("BOUNDING_BOX_CENTER", points, cursor, active), (1.0, 0.0, 0.0))
    assert almost_equal(choose_pivot("INDIVIDUAL_ORIGINS", points, cursor, active), (1.0, 0.0, 0.0))


def test_world_local_nonuniform_scale() -> None:
    matrix = (
        (2.0, 0.0, 0.0, 5.0),
        (0.0, 0.5, 0.0, 1.0),
        (0.0, 0.0, 3.0, -2.0),
        (0.0, 0.0, 0.0, 1.0),
    )
    local = (1.0, 4.0, -1.0)
    world = world_from_local(local, matrix)
    assert almost_equal(world, (7.0, 3.0, -5.0))
    assert almost_equal(local_from_world(world, matrix), local)
