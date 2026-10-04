"""Proteus-style drill evidence: coincident-endpoint circles and polygonal pad support (spec 041, US3)."""
import pytest

from mikrocam.bridge.svg_import import import_svg_bytes
from mikrocam.core.svg_drill_circles import COINCIDENT_ENDPOINT_MM
from mikrocam.core.svg_drills import detect_svg_drills

KAPPA = 0.5522847498307936


def four_cubic(cx, cy, r, *, reverse=False, end_dx=0., close=False, turns=1):
    """Proteus writes M x+r,y then four cubic quadrants back to the start, without Z."""
    k = KAPPA * r
    quadrants = [((cx + r, cy + k), (cx + k, cy + r), (cx, cy + r)),
                 ((cx - k, cy + r), (cx - r, cy + k), (cx - r, cy)),
                 ((cx - r, cy - k), (cx - k, cy - r), (cx, cy - r)),
                 ((cx + k, cy - r), (cx + r, cy - k), (cx + r, cy))]
    if reverse:
        quadrants = [((cx + r, cy - k), (cx + k, cy - r), (cx, cy - r)),
                     ((cx - k, cy - r), (cx - r, cy - k), (cx - r, cy)),
                     ((cx - r, cy + k), (cx - k, cy + r), (cx, cy + r)),
                     ((cx + k, cy + r), (cx + r, cy + k), (cx + r, cy))]
    quadrants = quadrants * turns
    *body, (c1, c2, end) = quadrants
    quadrants = [*body, (c1, c2, (end[0] + end_dx, end[1]))]
    text = f'M{cx + r!r},{cy!r} ' + ' '.join(
        'C' + ' '.join(f'{x!r},{y!r}' for x, y in triple) for triple in quadrants)
    return text + (' Z' if close else ' ')


def octagon(cx, cy, w, h, chamfer):
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2
    points = [(x0 + chamfer, y0), (x1 - chamfer, y0), (x1, y0 + chamfer), (x1, y1 - chamfer),
              (x1 - chamfer, y1), (x0 + chamfer, y1), (x0, y1 - chamfer), (x0, y0 + chamfer)]
    return 'M' + ' L'.join(f'{x!r},{y!r}' for x, y in points + points[:1])


def review(body, *, flip=False):
    source = (f'<svg xmlns="http://www.w3.org/2000/svg" width="100mm" height="50mm" viewBox="0 0 100 50">'
              f'{body}</svg>').encode()
    return detect_svg_drills(import_svg_bytes(source, 'proteus-like.svg', flip=flip))


def hole(d, ident='hole', fill='#ffffff'):
    return (f'<g fill="{fill}" stroke="none"><path id="{ident}" vector-effect="non-scaling-stroke" '
            f'fill-rule="evenodd" d="{d}"/></g>')


def pad(d, ident='pad', fill='#000000', extra=''):
    return f'<g fill="{fill}" stroke="none"><path id="{ident}" fill-rule="evenodd" {extra} d="{d}"/></g>'


PROTEUS_PADS = pad(octagon(20, 10, 2.28, 2.80, .38), 'mask') + pad(octagon(20, 10, 2.02, 2.54, .38), 'copper')


def notices(result):
    return [item.code for item in result.notices]


def test_coincident_endpoint_tolerance_is_numerical_noise_only():
    assert COINCIDENT_ENDPOINT_MM == 1e-6


@pytest.mark.parametrize('flip,y', [(False, 10), (True, 40)])
@pytest.mark.parametrize('reverse', [False, True])
def test_unclosed_four_cubic_circle_in_octagonal_pads_is_one_candidate(flip, y, reverse):
    result = review(PROTEUS_PADS + hole(four_cubic(20, 10, .5, reverse=reverse)), flip=flip)
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.center_mm == pytest.approx((20, y), abs=1e-6)
    # A four-cubic circle lies up to 0.027 % of r outside the true circle; the fit reports that.
    assert candidate.diameter_mm == pytest.approx(1, abs=3e-4) and candidate.diameter_mm >= 1
    assert 'hole' in candidate.opening_id and 'copper' in candidate.pad_id  # Smallest supporting pad.


def test_unclosed_circle_matches_the_explicitly_closed_circle():
    opened = review(pad(octagon(20, 10, 2, 2, .3)) + hole(four_cubic(20, 10, .5))).candidates
    closed = review(pad(octagon(20, 10, 2, 2, .3)) + hole(four_cubic(20, 10, .5, close=True))).candidates
    assert [(c.center_mm, c.diameter_mm) for c in opened] == [(c.center_mm, c.diameter_mm) for c in closed]


def test_two_half_arcs_back_to_the_start_are_a_full_circle_in_a_round_pad():
    d = 'M30.75,20 A0.75,0.75 0 0 1 29.25,20 A0.75,0.75 0 0 1 30.75,20'
    result = review('<circle id="pad" cx="30" cy="20" r="1.5" fill="black"/>' + hole(d))
    assert len(result.candidates) == 1
    assert result.candidates[0].diameter_mm == pytest.approx(1.5, abs=1e-6)
    assert 'pad' in result.candidates[0].pad_id


def test_rectangular_pad_supports_and_round_pad_keeps_priority():
    rect = '<rect id="rect" x="38" y="8" width="4" height="4" fill="black"/>'
    round_pad = '<circle id="ring" cx="40" cy="10" r="1.6" fill="black"/>'
    assert 'rect' in review(rect + hole(four_cubic(40, 10, .5))).candidates[0].pad_id
    assert 'ring' in review(rect + round_pad + hole(four_cubic(40, 10, .5))).candidates[0].pad_id


@pytest.mark.parametrize('d', [
    'M20.5,10 A0.5,0.5 0 1 1 20,9.5',                              # 270 degree arc.
    four_cubic(20, 10, .5, end_dx=.001),                             # 1 um gap is real geometry.
    four_cubic(20, 10, .5, turns=2),                                  # 720 degrees, endpoints coincide.
    'M20.5,10 A0.5,0.5 0 0 1 19.5,10 M19.5,10 A0.5,0.5 0 0 1 20.5,10',  # Two subpaths.
    octagon(20, 10, 1, 1, .29),                                      # Octagonal opening.
])
def test_partial_multi_turn_split_or_noncircular_openings_are_never_candidates(d):
    result = review(PROTEUS_PADS + hole(d))
    assert result.candidates == ()
    assert 'no-drills' in notices(result)


def test_sub_tolerance_endpoint_noise_is_accepted():
    result = review(PROTEUS_PADS + hole(four_cubic(20, 10, .5, end_dx=1e-7)))
    assert len(result.candidates) == 1


@pytest.mark.parametrize('pads', [
    pad(octagon(20.05, 10, 2.02, 2.54, .38)),                         # Centroid 0.05 mm off.
    pad('M0,0 L60,0 L60,40 L0,40 Z', 'pour'),                          # Copper pour, distant centroid.
    pad(octagon(20, 10, 1.01, 2.54, .2), 'thin'),                     # Edge 0.505 mm < 0.5 + 0.01 mm.
    pad(octagon(20, 10, 2.02, 2.54, .38), 'white', fill='#ffffff'),    # White pad is not copper.
    '<path id="outline" fill="none" stroke="black" stroke-width="2" d="' + octagon(20, 10, 2.02, 2.54, .38) + '"/>',
    '<defs><clipPath id="c"><rect x="0" y="0" width="100" height="50"/></clipPath></defs>'
    + pad(octagon(20, 10, 2.02, 2.54, .38), 'clipped', extra='clip-path="url(#c)"'),
])
def test_unqualified_polygonal_pads_do_not_support_an_opening(pads):
    result = review(pads + hole(four_cubic(20, 10, .5)))
    assert result.candidates == ()
    assert 'unsupported-opening' in notices(result)


def test_octagonal_pad_alone_is_never_a_drill():
    result = review(PROTEUS_PADS)
    assert result.candidates == () and 'no-drills' in notices(result)
