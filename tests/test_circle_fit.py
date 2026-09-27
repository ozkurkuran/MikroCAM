"""Physical complete-circle mathematics shared by current Geometry and SVG."""
import math

import pytest

from mikrocam.core.circle_fit import fit_closed_circle


def circle(x=10, y=-5, r=2, n=128):
    pts = tuple((x + r * math.cos(i * 2 * math.pi / n),
                 y + r * math.sin(i * 2 * math.pi / n)) for i in range(n))
    return pts + (pts[0],)


@pytest.mark.parametrize('x,y,r', [(10, -5, 2), (1e7, -1e7, .5), (0, 0, 1e-5)])
@pytest.mark.parametrize('reverse', [False, True])
def test_normalized_fit_physical_circle(x, y, r, reverse):
    pts = circle(x, y, r)
    center, radius = fit_closed_circle(pts[::-1] if reverse else pts)
    assert center == pytest.approx((x, y), abs=1e-8)
    assert radius == pytest.approx(r, rel=1e-7)


def test_redundant_closing_and_consecutive_points():
    pts = circle()
    assert fit_closed_circle((pts[0],) + pts + (pts[0],)) == fit_closed_circle(pts)


@pytest.mark.parametrize('pts', [circle()[:-1], circle(n=8), circle(n=12),
    tuple((2*x, y) for x, y in circle()), ((0., 0.),)*20,
    ((0., 0.), (1., 1.), (0., 1.), (1., 0.), (0., 0.))])
def test_valid_noncircles_are_not_candidates(pts):
    assert fit_closed_circle(pts) is None


@pytest.mark.parametrize('pts', [[], ((True, 0),), ((math.nan, 0),),
    ((math.inf, 0),), ((1e9+1, 0),), ((0, 0, 0),), ([0, 0],),
    ((0, 0),)*100001, 'circle', ((10**400, 0),)])
def test_invalid_unbounded_records_rejected(pts):
    with pytest.raises(ValueError):
        fit_closed_circle(pts)
