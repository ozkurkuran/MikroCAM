"""Bounded, immutable review of Proteus-style circular white-opening evidence."""
from dataclasses import dataclass
import math
import re

from .svg_drill_circles import circle_evidence
from .svg_models import SvgImportResult, SvgNotice, _number, _point

MAX_DRILL_CANDIDATES = 1000
CENTER_TOLERANCE_MM = .02
DIAMETER_TOLERANCE_MM = .01


def _text(value: str, limit: int, label: str) -> None:
    if type(value) is not str or not 1 <= len(value) <= limit:
        raise ValueError(f'{label} must be nonempty text within {limit} characters')
    try:
        value.encode('utf-8')
    except UnicodeEncodeError as error:
        raise ValueError(f'{label} requires strict UTF-8') from error


@dataclass(frozen=True)
class DrillCandidate:
    center_mm: tuple[float, float]
    diameter_mm: float
    opening_id: str
    pad_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, 'center_mm', _point(self.center_mm))
        diameter = _number(self.diameter_mm, 1e9, 'Drill diameter')
        if diameter <= 0:
            raise ValueError('Drill diameter must be positive')
        object.__setattr__(self, 'diameter_mm', diameter)
        _text(self.opening_id, 256, 'Opening ID')
        _text(self.pad_id, 256, 'Pad ID')


@dataclass(frozen=True)
class DrillReview:
    source_name: str
    source_sha256: str
    flipped: bool
    candidates: tuple[DrillCandidate, ...]
    notices: tuple[SvgNotice, ...]

    def __post_init__(self) -> None:
        _text(self.source_name, 256, 'Source name')
        if type(self.source_sha256) is not str or re.fullmatch('[0-9a-f]{64}', self.source_sha256) is None:
            raise ValueError('Source requires lowercase SHA256')
        if type(self.flipped) is not bool:
            raise ValueError('Flip must be boolean')
        if type(self.candidates) is not tuple or len(self.candidates) > MAX_DRILL_CANDIDATES or any(
                type(value) is not DrillCandidate for value in self.candidates):
            raise ValueError('Review requires at most 1000 immutable candidates')
        if type(self.notices) is not tuple or len(self.notices) > 200 or any(
                type(value) is not SvgNotice for value in self.notices):
            raise ValueError('Review notices must be a bounded immutable tuple')


class _Notices:
    def __init__(self) -> None:
        self.items: list[SvgNotice] = []
        self.omitted = 0

    def add(self, code: str, message: str, identifier: str = '') -> None:
        if len(self.items) < 199:
            self.items.append(SvgNotice(code, message, identifier))
        else:
            self.omitted += 1

    def finish(self) -> tuple[SvgNotice, ...]:
        if self.omitted:
            self.items.append(SvgNotice('notices-truncated', f'{self.omitted} further notices omitted.'))
        return tuple(self.items)


def _circles(result: SvgImportResult, notices: _Notices) -> tuple[list, list]:
    holes, pads = [], []
    for element, rendered in zip(result.document.elements, result.rendered):
        if element.clips:
            notices.add('clipped-drill-evidence', 'Clipped artwork is excluded from full-circle drill inference.',
                        element.element_id)
            continue
        circle = circle_evidence(element, rendered)
        if circle is None:
            if element.fill_is_white is True and element.paint.fill:
                notices.add('noncircular-opening', 'White artwork is not a sufficiently resolved single circle.',
                            element.element_id)
            continue
        if len(holes) + len(pads) >= MAX_DRILL_CANDIDATES:
            raise ValueError('Circular evidence exceeds the 1000 item limit')
        center, radius = circle
        item = (center, radius, element.element_id)
        if element.fill_is_white:
            if element.paint.stroke:
                notices.add('stroked-opening', 'White circle has a stroke; drill diameter is ambiguous.',
                            element.element_id)
                continue
            holes.append(item)
        else:
            pads.append(item)
    return holes, pads


def _pair(holes: list, pads: list, notices: _Notices) -> list[DrillCandidate]:
    candidates = []
    for center, radius, identifier in holes:
        supports = []
        for pad_center, pad_radius, pad_id in pads:
            offset = math.dist(center, pad_center)
            if offset <= CENTER_TOLERANCE_MM and pad_radius >= radius + offset + .01:
                supports.append((pad_radius, pad_id))
        if not supports:
            notices.add('unsupported-opening', 'White circle has no larger concentric nonwhite circular pad.', identifier)
            continue
        _, pad_id = min(supports)
        candidates.append(DrillCandidate(center, 2 * radius, identifier, pad_id))
    return candidates


def _unique(candidates: list[DrillCandidate], notices: _Notices) -> tuple[DrillCandidate, ...]:
    ordered = sorted(candidates, key=lambda c: (c.center_mm, c.diameter_mm, c.opening_id, c.pad_id))
    retained = []
    for candidate in ordered:
        duplicate = next((other for other in retained if
                          math.dist(candidate.center_mm, other.center_mm) <= CENTER_TOLERANCE_MM and
                          abs(candidate.diameter_mm - other.diameter_mm) <= DIAMETER_TOLERANCE_MM), None)
        if duplicate is not None:
            notices.add('duplicate-opening', 'Equal circular opening evidence collapsed into one candidate.',
                        candidate.opening_id)
        else:
            retained.append(candidate)
    conflicting = set()
    for index, candidate in enumerate(retained):
        for other_index in range(index + 1, len(retained)):
            other = retained[other_index]
            if math.dist(candidate.center_mm, other.center_mm) < (
                    candidate.diameter_mm + other.diameter_mm) / 2:
                conflicting.update((index, other_index))
    for index in sorted(conflicting):
        notices.add('conflicting-opening', 'Incompatible overlapping holes excluded; correct the source artwork.',
                    retained[index].opening_id)
    return tuple(candidate for index, candidate in enumerate(retained) if index not in conflicting)


def detect_svg_drills(result: SvgImportResult) -> DrillReview:
    """Interpret source circles conservatively; never change material or create host objects."""
    if type(result) is not SvgImportResult:
        raise ValueError('Drill detection requires an immutable SVG import result')
    notices = _Notices()
    notices.add('heuristic', 'White openings inside circular pads are artwork evidence, not proof of drill intent. '
                'Review centres and diameters before selecting holes.')
    for notice in result.notices:
        notices.add(notice.code, notice.message, notice.element_id)
    holes, pads = _circles(result, notices)
    candidates = _unique(_pair(holes, pads, notices), notices)
    if not candidates:
        notices.add('no-drills', 'No unambiguous circular drill candidates found in this source.')
    return DrillReview(result.document.source_name, result.document.source_sha256,
                       result.flipped, candidates, notices.finish())
