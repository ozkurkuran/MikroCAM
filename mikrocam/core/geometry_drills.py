"""Bounded review of current planar geometry, preserving source identity and roles."""
from dataclasses import replace
import hashlib
import json
import math

from shapely import get_coordinate_dimension, get_num_coordinates
from shapely.geometry.base import BaseGeometry

from .circle_fit import fit_closed_circle
from .drill_groups import DrillHole, DrillTool, group_drill_holes
from .geometry_drill_models import GeometryDrillCandidate, GeometryDrillReview


def _text(value: str, label: str) -> None:
    try:
        valid = type(value) is str and bool(value.strip()) and len(value.encode('utf-8')) <= 256
    except UnicodeError:
        valid = False
    if not valid:
        raise ValueError(f'{label} requires nonempty bounded UTF8 text')


class _Review:
    def __init__(self, name: str, units: str) -> None:
        self.digest = hashlib.sha256()
        self.factor = 1.0 if units == 'MM' else 25.4
        self.nodes = self.coordinates = self.ordinal = self.omitted = 0
        self.candidates: list[GeometryDrillCandidate] = []
        self.notices: list[str] = []
        self.feed(json.dumps((name, units), ensure_ascii=True).encode())

    def feed(self, data: bytes) -> None:
        self.digest.update(len(data).to_bytes(8, 'big'))
        self.digest.update(data)

    def notice(self, message: str) -> None:
        if len(self.notices) < 199:
            self.notices.append(message)
        else:
            self.omitted += 1

    def contour(self, ring: object, label: str, role: str, index: int) -> None:
        if len(ring.coords) > 100000:
            raise ValueError('Geometry contour exceeds 100000 points')
        points = tuple((float(p[0]) * self.factor, float(p[1]) * self.factor) for p in ring.coords)
        fitted = fit_closed_circle(points)
        if fitted is None:
            self.notice(f'Component {self.ordinal} {role}: open or not a resolved circle')
            return
        center, radius = fitted
        if radius * 2 > 1e9:
            raise ValueError('Circle diameter exceeds supported physical magnitude')
        for i, prior in enumerate(self.candidates):
            if math.dist(prior.center_mm, center) <= .02 and abs(prior.diameter_mm - radius*2) <= .01:
                self.candidates[i] = replace(prior, duplicate_count=prior.duplicate_count + 1)
                self.notice(f'Component {self.ordinal} {role}: duplicate circle collapsed')
                return
        if len(self.candidates) >= 1000:
            raise ValueError('Geometry review exceeds 1000 candidates')
        short = label.encode('utf-8')[:160].decode('utf-8', errors='ignore')
        identity = hashlib.sha256(label.encode('utf-8')).hexdigest()[:12]
        source_id = f'{short}:{identity}:{self.ordinal}:{role}:{index}'
        self.candidates.append(GeometryDrillCandidate(center, radius*2, source_id, role))

    def primitive(self, geometry: BaseGeometry, label: str) -> None:
        count = int(get_num_coordinates(geometry))
        self.coordinates += count
        if self.coordinates > 500000:
            raise ValueError('Geometry coordinate budget exceeded')
        kind = geometry.geom_type
        if kind == 'Polygon':
            contours = (geometry.exterior, *geometry.interiors)
        else:
            contours = (geometry,)
        for ring in contours:
            if len(ring.coords) > 100000:
                raise ValueError('Geometry contour exceeds 100000 points')
            for p in ring.coords:
                if len(p) != 2 or any(not math.isfinite(v) or abs(v*self.factor) > 1e9 for v in p):
                    raise ValueError('Geometry requires finite planar bounded physical coordinates')
        if not geometry.is_valid:
            raise ValueError('Invalid geometry cannot be reviewed')
        self.feed(kind.encode())
        self.feed(geometry.wkb)
        self.ordinal += 1
        if geometry.is_empty:
            self.notice(f'Component {self.ordinal}: empty geometry excluded')
        elif kind == 'Point':
            self.notice(f'Component {self.ordinal}: point has no circle diameter')
        elif kind == 'Polygon':
            self.contour(geometry.exterior, label, 'exterior', 0)
            for i, ring in enumerate(geometry.interiors):
                self.contour(ring, label, 'interior', i)
        else:
            self.contour(geometry, label, 'closed-line', 0)

    def walk(self, tree: object, label: str) -> None:
        stack = [(tree, 0)]
        multipart = []
        while stack:
            value, depth = stack.pop()
            self.nodes += 1
            if self.nodes > 10000 or depth > 64:
                raise ValueError('Geometry node/depth budget exceeded')
            if type(value) in (list, tuple):
                kind, children = type(value).__name__, value
            elif isinstance(value, BaseGeometry):
                if get_coordinate_dimension(value) != 2:
                    raise ValueError('Only planar XY geometry is supported')
                kind = value.geom_type
                if kind in ('MultiPolygon', 'MultiLineString', 'GeometryCollection', 'MultiPoint'):
                    children = value.geoms
                    multipart.append(value)
                elif kind in ('Polygon', 'LineString', 'LinearRing', 'Point'):
                    self.primitive(value, label)
                    continue
                else:
                    raise ValueError('Unsupported geometry type')
            else:
                raise ValueError('Geometry tree contains an unsupported object')
            if self.nodes + len(stack) + len(children) > 10000:
                raise ValueError('Geometry node budget exceeded')
            self.feed(f'{kind}:{len(children)}'.encode())
            if not children:
                self.notice('Empty geometry container excluded')
            stack.extend((child, depth+1) for child in reversed(children))
        # Check parent topology only after all children have passed resource/coordinate bounds.
        if any(not geometry.is_valid for geometry in multipart):
            raise ValueError('Invalid multipart geometry cannot be reviewed')


def review_geometry_sources(sources: tuple[tuple[str, object], ...], source_name: str,
                            units: str) -> GeometryDrillReview:
    """Review authoritative current source trees without mutation or source-file I/O."""
    _text(source_name, 'Source name')
    if type(units) is not str or units not in ('MM', 'IN'):
        raise ValueError('Geometry source units must be explicit MM or IN')
    if type(sources) is not tuple or not 1 <= len(sources) <= 10000:
        raise ValueError('Geometry sources require 1..10000 immutable source pairs')
    state = _Review(source_name, units)
    labels = set()
    for pair in sources:
        if type(pair) is not tuple or len(pair) != 2:
            raise ValueError('Geometry sources require immutable label/tree pairs')
        label, tree = pair
        _text(label, 'Source label')
        if label in labels:
            raise ValueError('Geometry source labels must be unique')
        labels.add(label)
        state.feed(label.encode('utf-8'))
        state.walk(tree, label)
    if state.omitted:
        state.notices.append(f'{state.omitted} additional notices omitted')
    return GeometryDrillReview(source_name, units, state.digest.hexdigest(),
                               tuple(state.candidates), tuple(state.notices))


def group_geometry_selection(review: GeometryDrillReview,
                             indices: tuple[int, ...]) -> tuple[DrillTool, ...]:
    """Group only explicitly selected candidates, rejecting overlapping footprints."""
    if type(review) is not GeometryDrillReview or type(indices) is not tuple or not 1 <= len(indices) <= 1000:
        raise ValueError('Select 1..1000 reviewed circle indices')
    if any(type(i) is not int or not 0 <= i < len(review.candidates) for i in indices) or len(set(indices)) != len(indices):
        raise ValueError('Selected indices must be unique in-range integers')
    return group_drill_holes(tuple(DrillHole(review.candidates[i].center_mm,
                                            review.candidates[i].diameter_mm) for i in indices))
